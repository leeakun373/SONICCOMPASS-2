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
        
        # AI 语义仲裁相关
        self.category_centroids: Dict[str, np.ndarray] = {}  # Category -> 质心向量
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
        
        # 先计算有明确标注的数据的质心
        if QT_AVAILABLE:
            self.progress_signal.emit(10, "Computing category centroids...")
        print("[INFO] 正在计算 Category 质心（这可能需要一些时间）...")
        self._compute_category_centroids(metadata_list)
        print(f"[INFO] 质心计算完成，发现 {len(self.category_centroids)} 个 Category")
        
        # 处理元数据并应用 AI 语义仲裁
        print(f"[INFO] 处理 {len(metadata_list)} 条记录，应用 AI 语义仲裁...")
        processed_count = 0
        for meta in metadata_list:
            if meta.semantic_text:
                texts.append(meta.semantic_text)
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
                        'semantic_text': getattr(meta, 'semantic_text', '')
                    }
                
                # 使用 AI 语义仲裁进行智能分类
                category = self._extract_category(meta_dict)
                if category:
                    meta_dict['category'] = category
                else:
                    # 如果无法确定，标记为 UNCATEGORIZED
                    meta_dict['category'] = "UNCATEGORIZED"
                
                metadata_dicts.append(meta_dict)
                processed_count += 1
                
                # 每处理 1000 条输出一次进度
                if processed_count % 1000 == 0:
                    print(f"   [进度] 已处理 {processed_count}/{len(metadata_list)} 条记录...")
        
        print(f"[INFO] AI 语义仲裁完成，处理了 {processed_count} 条记录")
        
        if not texts:
            raise DataProcessorError("没有可用的语义文本数据")
        
        # 3. 批量向量化（使用tqdm显示进度）
        if QT_AVAILABLE:
            self.progress_signal.emit(20, "Encoding vectors...")
        
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
    
    def _compute_category_centroids(self, metadata_list):
        """
        计算每个 UCS Category 的平均向量（质心）
        
        Args:
            metadata_list: 元数据列表
            
        Returns:
            字典：{category: centroid_vector}
        """
        # 先收集有明确 UCS 标注的数据
        category_embeddings = {}  # category -> [embeddings]
        category_texts = {}  # category -> [texts]
        
        try:
            from core.category_color_mapper import CategoryColorMapper
            mapper = CategoryColorMapper()
        except Exception:
            mapper = None
        
        for meta in metadata_list:
            if not meta.semantic_text:
                continue
            
            # 获取 Category
            cat_id = getattr(meta, 'category', '')
            category = None
            
            if mapper:
                category = mapper.get_category_from_catid(cat_id)
            
            # 如果有明确的 Category，收集其文本
            if category and category != "UNCATEGORIZED":
                if category not in category_texts:
                    category_texts[category] = []
                category_texts[category].append(meta.semantic_text)
        
        # 对每个 Category 计算质心
        if category_texts:
            print(f"[INFO] 发现 {len(category_texts)} 个 Category，开始计算质心...")
            # 批量向量化所有文本
            all_texts = []
            text_to_category = []
            for category, texts in category_texts.items():
                all_texts.extend(texts)
                text_to_category.extend([category] * len(texts))
            
            if all_texts:
                print(f"[INFO] 向量化 {len(all_texts)} 条文本用于质心计算...")
                all_embeddings = self.vector_engine.encode_batch(
                    all_texts,
                    batch_size=64,
                    show_progress=True,  # 显示进度
                    normalize_embeddings=True
                )
                
                # 按 Category 分组并计算平均值
                print("[INFO] 计算各 Category 的平均向量...")
                for i, category in enumerate(text_to_category):
                    if category not in category_embeddings:
                        category_embeddings[category] = []
                    category_embeddings[category].append(all_embeddings[i])
                
                # 计算每个 Category 的质心
                for category, emb_list in category_embeddings.items():
                    if emb_list:
                        self.category_centroids[category] = np.mean(emb_list, axis=0)
                print(f"[INFO] 质心计算完成，共 {len(self.category_centroids)} 个 Category 质心")
    
    def _extract_category(self, meta_dict: Dict) -> Optional[str]:
        """
        AI 语义仲裁：三级分类策略
        
        Args:
            meta_dict: 元数据字典
            
        Returns:
            Category 名称，如果无法确定则返回 None
        """
        # Try Metadata: 有有效 UCS Category -> 使用
        cat_id = meta_dict.get('category', '')
        if cat_id:
            try:
                from core.category_color_mapper import CategoryColorMapper
                mapper = CategoryColorMapper()
                category = mapper.get_category_from_catid(cat_id)
                if category and category != "UNCATEGORIZED":
                    return category
            except Exception:
                pass
        
        # Try Keyword: 文件名命中 UCS 关键词 -> 使用
        filename = meta_dict.get('filename', '').lower()
        if filename and self.ucs_manager:
            # 尝试从文件名中提取关键词
            # 简单的关键词匹配：检查文件名是否包含 UCS 关键词
            resolved_catid = self.ucs_manager.resolve_alias(filename)
            if resolved_catid:
                try:
                    from core.category_color_mapper import CategoryColorMapper
                    mapper = CategoryColorMapper()
                    category = mapper.get_category_from_catid(resolved_catid)
                    if category and category != "UNCATEGORIZED":
                        return category
                except Exception:
                    pass
        
        # Try AI: 计算与质心的余弦相似度
        if self.category_centroids:
            semantic_text = meta_dict.get('semantic_text', '')
            if semantic_text:
                try:
                    # 计算文件的 Embedding
                    file_embedding = self.vector_engine.encode_batch(
                        [semantic_text],
                        batch_size=1,
                        show_progress=False,
                        normalize_embeddings=True
                    )[0]
                    
                    # 计算与所有质心的余弦相似度
                    max_similarity = -1.0
                    best_category = None
                    
                    for category, centroid in self.category_centroids.items():
                        # 余弦相似度
                        similarity = np.dot(file_embedding, centroid)
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_category = category
                    
                    # 如果最大相似度 > 0.6，分配给该 Category
                    if max_similarity > 0.6 and best_category:
                        return best_category
                except Exception as e:
                    print(f"[WARNING] AI 分类失败: {e}")
        
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

