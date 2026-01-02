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


class DataProcessorError(Exception):
    """数据处理器错误"""
    pass


class DataProcessor:
    """数据处理器 - 索引构建器"""
    
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
        self.importer = importer
        self.vector_engine = vector_engine
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 缓存文件路径
        self.metadata_cache_path = self.cache_dir / "metadata.pkl"
        self.embeddings_cache_path = self.cache_dir / "embeddings.npy"
        self.index_info_path = self.cache_dir / "index_info.pkl"
        self.coordinates_cache_path = self.cache_dir / "coordinates.npy"
    
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
        
        # 1. 从数据库获取数据
        metadata_list = self.importer.import_all(limit=limit)
        
        # 2. 提取语义文本并转换为字典格式
        texts = []
        metadata_dicts = []
        for meta in metadata_list:
            if meta.semantic_text:
                texts.append(meta.semantic_text)
                # 转换为字典格式
                if hasattr(meta, '__dict__'):
                    metadata_dicts.append(asdict(meta) if hasattr(meta, '__dict__') and hasattr(meta, '__dataclass_fields__') else meta.__dict__)
                else:
                    metadata_dicts.append({
                        'recID': getattr(meta, 'recID', None),
                        'filename': getattr(meta, 'filename', ''),
                        'filepath': getattr(meta, 'filepath', ''),
                        'description': getattr(meta, 'description', ''),
                        'keywords': getattr(meta, 'keywords', ''),
                        'category': getattr(meta, 'category', ''),
                        'semantic_text': getattr(meta, 'semantic_text', '')
                    })
        
        if not texts:
            raise DataProcessorError("没有可用的语义文本数据")
        
        # 3. 批量向量化（使用tqdm显示进度）
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
        
        return metadata_dicts, embeddings
    
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

