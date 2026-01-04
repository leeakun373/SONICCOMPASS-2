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
        三级仲裁逻辑 (Final Fix): 强规则 -> 显式检查 -> AI 向量
        目标：始终返回 Category Code (e.g. 'WPN') 用于颜色映射
        """
        cat_id = meta_dict.get('category', '').strip()
        rich_text = meta_dict.get('rich_context_text', '') or meta_dict.get('semantic_text', '')
        text_upper = rich_text.upper() if rich_text else ""
        
        # --- Level 0: 强规则层 (The Hard Rule Layer) ---
        # 解决 "Future Weapon" -> "Aircraft" 的问题
        # 只要文件名里有这些词，直接锁定 Code，不给 AI 瞎猜的机会
        STRONG_RULES = {
            'WEAPON': 'WPN', 'GUN': 'WPN', 'FIREARM': 'WPN', 'EXPLOSION': 'WPN', 'BLAST': 'WPN',
            'LASER': 'SCI', 'SCIFI': 'SCI', 'ROBOT': 'SCI', 'FUTURISTIC': 'SCI',
            'MAGIC': 'MAG', 'SPELL': 'MAG', 'SORCERY': 'MAG',
            'WATER': 'WAT', 'LIQUID': 'WAT', 'SPLASH': 'WAT', 'OCEAN': 'WAT',
            'RAIN': 'WEA', 'THUNDER': 'WEA', 'STORM': 'WEA',
            'WIND': 'AMB', 'AMBIENCE': 'AMB', 'ATMOSPHERE': 'AMB',
            'FOOTSTEP': 'FOL', 'WALK': 'FOL', 'CLOTH': 'FOL',
            'UI': 'UI', 'BUTTON': 'UI', 'CLICK': 'UI', 'INTERFACE': 'UI',
            'AIRCRAFT': 'AERO', 'PLANE': 'AERO', 'JET': 'AERO', 'HELICOPTER': 'AERO'
        }
        
        # 使用分词匹配 (Tokenization Check) 防止 "TRAIN" 匹配 "RAIN"
        # 简单的做法是检查单词边界，或者直接检查包含
        for keyword, code in STRONG_RULES.items():
            if keyword in text_upper:
                # 命中强规则！直接返回 Code
                return code, "GENERAL"

        # --- Level 1: 现有 Metadata 显式检查 ---
        # 过滤垃圾分类
        is_weak = False
        if "MISC" in cat_id.upper(): 
            is_weak = True
        if cat_id.upper() in ['GEN', 'GENERAL', 'NONE', 'UNCATEGORIZED', '']: 
            is_weak = True
        
        if not is_weak and cat_id and self.ucs_manager:
            # 尝试解析 CatID (如 "AIRBlow")
            info = self.ucs_manager.get_catid_info(cat_id)
            if info and info.get('category_code'):
                 return info['category_code'], info.get('subcategory_name', '')

        # --- Level 3: AI 向量仲裁 (The Vector Layer) ---
        if not self.category_centroids:
            return "UNCATEGORIZED", ""

        if not rich_text:
            return "UNCATEGORIZED", ""

        try:
            vector = self.vector_engine.encode(rich_text)
        except:
            return "UNCATEGORIZED", ""
            
        best_cat_id = None
        best_score = -1.0
        
        for cid, centroid in self.category_centroids.items():
            score = np.dot(vector, centroid)
            if score > best_score:
                best_score = score
                best_cat_id = cid
                
        # 结果解析
        if best_cat_id and best_score > 0.4:
            if self.ucs_manager:
                # 查表：从 CatID (e.g. 'AIRBlow') 查出 Code ('AIR')
                info = self.ucs_manager.get_catid_info(best_cat_id)
                if info and info.get('category_code'):
                    return info['category_code'], info.get('subcategory_name', '')
            
            # 兜底：如果查不到表，但这看起来像是一个合法的 ID，取前三位大写
            # 这能保证至少返回一个 Code，而不是 Name
            return best_cat_id[:3].upper(), ""
            
        return "UNCATEGORIZED", ""
    
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

