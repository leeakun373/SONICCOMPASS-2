"""
数据处理器 - 索引构建器
将数据库中的所有数据分批次进行向量化，并保存到本地缓存文件
实现"慢速AI计算"到"极速本地搜索"的转换
"""

import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# 导入 PySide6 Signal 机制
try:
    from PySide6.QtCore import QObject, Signal
    QT_AVAILABLE = True
except ImportError:
    # 如果 PySide6 不可用，创建模拟类
    class QObject:
        pass
    class Signal:
        def __init__(self, *args):
            pass
        def emit(self, *args):
            pass
    QT_AVAILABLE = False


class DataProcessorError(Exception):
    """数据处理器错误"""
    pass


class DataProcessor(QObject):
    """数据处理器 - 索引构建器"""
    
    # 定义进度信号
    if QT_AVAILABLE:
        progress_signal = Signal(int, str)  # 进度(%), 描述
    
    def __init__(
        self,
        importer,
        vector_engine,
        cache_dir: str = "./cache"
    ):
        """
        初始化数据处理器
        
        Args:
            importer: SoundminerImporter 实例
            vector_engine: VectorEngine 实例
            cache_dir: 缓存目录路径
        """
        if QT_AVAILABLE:
            super().__init__()
        
        self.importer = importer
        self.vector_engine = vector_engine
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存文件路径
        self.metadata_cache_path = self.cache_dir / "metadata.pkl"
        self.embeddings_cache_path = self.cache_dir / "embeddings.npy"
        self.index_info_path = self.cache_dir / "index_info.pkl"
        self.coordinates_cache_path = self.cache_dir / "coordinates.npy"
        self.platinum_centroids_path = self.cache_dir / "platinum_centroids_754.pkl"  # 754 CatID 版本
        
        # AI 语义仲裁相关
        self.category_centroids: Dict[str, np.ndarray] = {}  # Category -> 质心向量（从 Platinum Centroids 加载）
        self.ucs_manager = None  # 将在需要时初始化
    
    def _cache_exists(self) -> bool:
        """检查缓存是否存在"""
        return (
            self.metadata_cache_path.exists() and
            self.embeddings_cache_path.exists() and
            self.index_info_path.exists()
        )
    
    def build_index(
        self,
        batch_size: int = 32,
        limit: Optional[int] = None,
        force_rebuild: bool = False
    ) -> Tuple[List[Dict], np.ndarray]:
        """
        构建索引：批量向量化数据并保存到缓存
        
        Args:
            batch_size: 批处理大小
            limit: 限制处理的数据量（用于测试）
            force_rebuild: 是否强制重建索引
            
        Returns:
            (metadata_list, embeddings_matrix) 元数据列表和向量矩阵
        """
        # 检查缓存是否存在
        if not force_rebuild and self._cache_exists():
            return self.load_index()
        
        # 发射进度信号
        if QT_AVAILABLE:
            self.progress_signal.emit(5, "Loading data from database...")
        
        # 1. 从数据库获取数据
        metadata_list = self.importer.import_all(limit=limit)
        
        # 2. 提取语义文本并转换为字典格式，同时进行智能分类
        texts = []
        metadata_dicts = []
        
        # 初始化 UCS Manager（用于关键词匹配）
        try:
            from core.ucs_manager import UCSManager
            if self.ucs_manager is None:
                self.ucs_manager = UCSManager()
                self.ucs_manager.load_all()
        except Exception as e:
            print(f"[WARNING] 无法初始化 UCSManager: {e}")
            self.ucs_manager = None
        
        # 【Platinum Centroids】加载预定义的标准质心（而不是从用户数据计算）
        if QT_AVAILABLE:
            self.progress_signal.emit(10, "Loading platinum centroids...")
        print("[INFO] 正在加载 Platinum Centroids（标准 UCS 定义质心）...")
        import sys
        sys.stdout.flush()  # 强制刷新输出
        self._load_platinum_centroids()
        if self.category_centroids:
            print(f"[INFO] Platinum Centroids 加载完成，共 {len(self.category_centroids)} 个标准质心")
        else:
            print("[WARNING] Platinum Centroids 未找到，AI 仲裁将无法工作")
            print("   请先运行: python tools/generate_platinum_centroids.py")
        sys.stdout.flush()
        
        # Phase 3.5: 处理元数据并应用 Smart Metadata Arbitration
        print(f"[INFO] 处理 {len(metadata_list)} 条记录，应用 Smart Metadata Arbitration...")
        sys.stdout.flush()
        processed_count = 0
        for meta in metadata_list:
            # Phase 3.5: 优先使用 rich_context_text，向后兼容 semantic_text
            context_text = getattr(meta, 'rich_context_text', '') or getattr(meta, 'semantic_text', '')
            if context_text:
                texts.append(context_text)
                # 转换为字典格式
                if hasattr(meta, '__dict__'):
                    meta_dict = asdict(meta) if hasattr(meta, '__dict__') and hasattr(meta, '__dataclass_fields__') else meta.__dict__
                else:
                    meta_dict = {
                        'recID': getattr(meta, 'recID', None),
                        'filename': getattr(meta, 'filename', ''),
                        'filepath': getattr(meta, 'filepath', ''),
                        'description': getattr(meta, 'description', ''),
                        'keywords': getattr(meta, 'keywords', ''),
                        'category': getattr(meta, 'category', ''),
                        'semantic_text': getattr(meta, 'semantic_text', ''),
                        'rich_context_text': getattr(meta, 'rich_context_text', '') or getattr(meta, 'semantic_text', '')
                    }
                
                # Phase 3.5: 使用 Smart Metadata Arbitration 进行智能分类
                result = self._extract_category(meta_dict)
                if result:
                    category, subcategory = result
                    # 保存仲裁后的 Category 和 SubCategory
                    meta_dict['category'] = category
                    meta_dict['subcategory'] = subcategory
                else:
                    # 如果无法确定，标记为 UNCATEGORIZED
                    meta_dict['category'] = "UNCATEGORIZED"
                    meta_dict['subcategory'] = ""
                
                metadata_dicts.append(meta_dict)
                processed_count += 1
                
                # 每处理 1000 条输出一次进度
                if processed_count % 1000 == 0:
                    print(f"   [进度] 已处理 {processed_count}/{len(metadata_list)} 条记录...")
                    import sys
                    sys.stdout.flush()  # 强制刷新输出
        
        print(f"[INFO] AI 语义仲裁完成，处理了 {processed_count} 条记录")
        import sys
        sys.stdout.flush()
        
        if not texts:
            raise DataProcessorError("没有可用的语义文本数据")
        
        # 3. 批量向量化（使用tqdm显示进度）
        if QT_AVAILABLE:
            self.progress_signal.emit(20, "Encoding vectors...")
        
        print(f"[INFO] 开始向量化 {len(texts)} 条文本...")
        import sys
        sys.stdout.flush()
        
        try:
            from tqdm import tqdm
            show_progress = True
        except ImportError:
            show_progress = False
        
        embeddings = self.vector_engine.encode_batch(
            texts,
            batch_size=batch_size,
            show_progress=show_progress,
            normalize_embeddings=True
        )
        
        print(f"[INFO] 向量化完成，向量维度: {embeddings.shape}")
        sys.stdout.flush()
        
        if QT_AVAILABLE:
            self.progress_signal.emit(80, "Saving cache...")
        
        # 4. 保存到缓存
        with open(self.metadata_cache_path, 'wb') as f:
            pickle.dump(metadata_dicts, f)
        
        embeddings_float32 = embeddings.astype(np.float32)
        np.save(self.embeddings_cache_path, embeddings_float32)
        
        # 保存索引信息
        index_info = {
            'count': len(metadata_dicts),
            'dimension': embeddings.shape[1],
            'dtype': 'float32'
        }
        with open(self.index_info_path, 'wb') as f:
            pickle.dump(index_info, f)
        
        if QT_AVAILABLE:
            self.progress_signal.emit(100, "Complete")
        
        return metadata_dicts, embeddings
    
    def _load_platinum_centroids(self):
        """
        加载 Platinum Centroids（从预定义的 JSON 定义生成的质心）
        
        【754 CatID Source of Truth】保持 CatID 格式，不转换为 Category
        格式: {CatID: Vector}，例如 {"AIRBlow": vector, "WPNGun": vector}
        """
        if not self.platinum_centroids_path.exists():
            print(f"[WARNING] Platinum Centroids 文件不存在: {self.platinum_centroids_path}")
            print("   请先运行: python tools/generate_platinum_centroids.py")
            return
        
        try:
            with open(self.platinum_centroids_path, 'rb') as f:
                platinum_centroids = pickle.load(f)
            
            # 【754 CatID Source of Truth】直接使用 CatID 作为 key，不转换
            # 格式: {CatID: Vector}，例如 {"AIRBlow": vector}
            self.category_centroids = platinum_centroids.copy()
            
            print(f"[INFO] 成功加载 {len(self.category_centroids)} 个 CatID 质心（754 CatID Source of Truth）")
            
        except Exception as e:
            print(f"[ERROR] 加载 Platinum Centroids 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _compute_category_centroids(self, metadata_list):
        """
        【已废弃】不再从用户数据计算质心
        
        此方法已被 _load_platinum_centroids 替代。
        现在使用预定义的 Platinum Centroids（从 ucs_definitions.json 生成）。
        
        保留此方法仅用于向后兼容，但不会被调用。
        """
        print("[WARNING] _compute_category_centroids 已被废弃，请使用 Platinum Centroids")
        print("   请运行: python tools/generate_platinum_centroids.py")
        pass
    
    def _extract_category(self, meta_dict: Dict) -> Optional[Tuple[str, str]]:
        """
        Phase 3.5: Smart Metadata Arbitration - 3级仲裁逻辑
        
        Args:
            meta_dict: 元数据字典
            
        Returns:
            (Category, SubCategory) 元组，如果无法确定则返回 None
        """
        try:
            from core.category_color_mapper import CategoryColorMapper
            mapper = CategoryColorMapper()
        except Exception:
            mapper = None
        
        # ========== Level 1: Explicit (检查 Category 字段) ==========
        cat_id = meta_dict.get('category', '').strip()
        if cat_id:
            if mapper:
                category = mapper.get_category_from_catid(cat_id)
                subcategory = mapper.get_subcategory_from_catid(cat_id)
                
                # Dynamic "Misc" Filter: 拒绝通用的 "Misc" 元数据，强制使用 AI 仲裁
                is_weak = False
                
                # Check 1: String contains "MISC" (case-insensitive)
                cat_id_upper = cat_id.upper()
                if "MISC" in cat_id_upper:
                    is_weak = True
                if subcategory and "MISC" in subcategory.upper():
                    is_weak = True
                
                # Check 2: Specific Generic IDs
                weak_ids = ['GEN', 'GENERAL', 'NONE', 'UNCATEGORIZED']
                if cat_id_upper in weak_ids:
                    is_weak = True
                
                # Only return if it passes the "Misc Check" and is valid
                if not is_weak and category and category != "UNCATEGORIZED":
                    return (category, subcategory or "")
                # If is_weak is True, fall through to Level 2/3 for better specificity
        
        # ========== Level 2: Heuristics (使用 ucs_alias.csv 和 Synonyms) ==========
        # 使用 rich_context_text（如果存在）或 semantic_text（向后兼容）
        context_text = meta_dict.get('rich_context_text', '') or meta_dict.get('semantic_text', '')
        if context_text and self.ucs_manager:
            context_lower = context_text.lower()
            
            # 2.1: 使用 ucs_alias.csv 映射
            resolved_catid = self.ucs_manager.resolve_alias(context_lower)
            if resolved_catid:
                if mapper:
                    category = mapper.get_category_from_catid(resolved_catid)
                    subcategory = mapper.get_subcategory_from_catid(resolved_catid)
                    if category and category != "UNCATEGORIZED":
                        return (category, subcategory or "")
            
            # 2.2: 使用 Synonyms 从 ucs_catid_list.csv
            if mapper:
                # 获取所有 CatID 及其 Synonyms
                try:
                    import pandas as pd
                    ucs_csv_path = Path("data_config/ucs_catid_list.csv")
                    if ucs_csv_path.exists():
                        df = pd.read_csv(ucs_csv_path, encoding='utf-8')
                        for _, row in df.iterrows():
                            synonyms_str = str(row.get('Synonyms - Comma Separated', '')).strip()
                            if synonyms_str:
                                synonyms = [s.strip().lower() for s in synonyms_str.split(',')]
                                # 检查 context_text 是否包含任何同义词
                                for synonym in synonyms:
                                    if synonym and synonym in context_lower:
                                        cat_id = str(row.get('CatID', '')).strip()
                                        category = mapper.get_category_from_catid(cat_id)
                                        subcategory = mapper.get_subcategory_from_catid(cat_id)
                                        if category and category != "UNCATEGORIZED":
                                            return (category, subcategory or "")
                except Exception as e:
                    print(f"[WARNING] Synonyms 匹配失败: {e}")
        
        # ========== Level 3: AI Vector Match (向量相似度) - 754 CatID Source of Truth ==========
        if self.category_centroids and context_text:
            try:
                # 计算文件的 Embedding（使用 rich_context_text）
                file_embedding = self.vector_engine.encode_batch(
                    [context_text],
                    batch_size=1,
                    show_progress=False,
                    normalize_embeddings=True
                )[0]
                
                # 【关键修改】计算与所有 754 个 CatID 质心的余弦相似度
                max_similarity = -1.0
                best_catid = None
                
                for catid, centroid in self.category_centroids.items():
                    # 余弦相似度（已归一化，直接点积）
                    similarity = np.dot(file_embedding, centroid)
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_catid = catid
                
                # 如果最大相似度 > 0.6，分配给该 CatID
                if max_similarity > 0.6 and best_catid:
                    # 【CRITICAL STEP】使用 UCSManager 查表获取 Parent Category (CatShort)
                    if self.ucs_manager:
                        final_category = self.ucs_manager.get_category_code(best_catid)  # 返回 CatShort (如 "AIR")
                        final_subcategory = self.ucs_manager.get_subcategory_by_catid(best_catid)  # 返回 SubCategory (如 "BLOW")
                        
                        if final_category:
                            # 保存 CatShort 到 metadata，确保 Color Mapper 能正确工作
                            return (final_category, final_subcategory or "")
                    else:
                        # 如果没有 UCSManager，尝试使用 mapper
                        if mapper:
                            final_category = mapper.get_category_from_catid(best_catid)
                            final_subcategory = mapper.get_subcategory_from_catid(best_catid)
                            if final_category:
                                return (final_category, final_subcategory or "")
            except Exception as e:
                print(f"[WARNING] AI 向量匹配失败: {e}")
        
        # 无法确定，返回 None（将在后续处理中标记为 UNCATEGORIZED）
        return None
    
    def load_index(self) -> Tuple[List[Dict], np.ndarray]:
        """
        从缓存加载索引（毫秒级加载）
        
        Returns:
            (metadata_list, embeddings_matrix) 元数据列表和向量矩阵
        """
        if not self._cache_exists():
            raise DataProcessorError("缓存不存在，请先构建索引")
        
        # 加载元数据
        with open(self.metadata_cache_path, 'rb') as f:
            metadata_dicts = pickle.load(f)
        
        # 加载向量矩阵
        embeddings = np.load(self.embeddings_cache_path)
        
        return metadata_dicts, embeddings
    
    def load_coordinates(self) -> Optional[np.ndarray]:
        """
        加载预计算的 UMAP 坐标
        
        Returns:
            2D 坐标矩阵，如果不存在则返回 None
        """
        if self.coordinates_cache_path.exists():
            return np.load(self.coordinates_cache_path)
        return None
    
    def save_coordinates(self, coordinates: np.ndarray):
        """
        保存 UMAP 坐标到缓存
        
        Args:
            coordinates: 2D 坐标矩阵
        """
        np.save(self.coordinates_cache_path, coordinates.astype(np.float32))
    
    def clear_cache(self):
        """清除缓存文件"""
        if self.metadata_cache_path.exists():
            self.metadata_cache_path.unlink()
        if self.embeddings_cache_path.exists():
            self.embeddings_cache_path.unlink()
        if self.index_info_path.exists():
            self.index_info_path.unlink()
        if self.coordinates_cache_path.exists():
            self.coordinates_cache_path.unlink()

