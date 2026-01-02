"""
搜索算法核心
提供极速的向量检索功能
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from .vector_engine import VectorEngine
from .data_processor import DataProcessor


class SearchCoreError(Exception):
    """搜索核心错误"""
    pass


class SearchCore:
    """搜索核心 - 向量检索引擎"""
    
    def __init__(
        self,
        vector_engine: VectorEngine,
        processor: Optional[DataProcessor] = None,
        metadata: Optional[List[Dict]] = None,
        embeddings: Optional[np.ndarray] = None
    ):
        """
        初始化搜索核心
        
        Args:
            vector_engine: VectorEngine 实例
            processor: DataProcessor 实例（用于加载数据）
            metadata: 元数据列表（如果直接提供）
            embeddings: 向量矩阵（如果直接提供）
        """
        self.vector_engine = vector_engine
        
        # 加载数据
        if processor is not None:
            print("[INFO] 从 DataProcessor 加载索引...")
            self.metadata, self.embeddings = processor.load_index()
        elif metadata is not None and embeddings is not None:
            self.metadata = metadata
            self.embeddings = embeddings
        else:
            raise SearchCoreError(
                "必须提供 processor 或 (metadata, embeddings)"
            )
        
        # 确保向量是归一化的（用于余弦相似度计算）
        self.embeddings = self._normalize_vectors(self.embeddings)
        
        print(f"[INFO] 搜索核心初始化完成")
        print(f"      数据量: {len(self.metadata)} 条")
        print(f"      向量维度: {self.embeddings.shape[1]}")
        print(f"      向量已归一化: True")
    
    def search_by_text(
        self,
        query: str,
        top_k: int = 50,
        filter_category: Optional[str] = None
    ) -> List[Tuple[Dict, float]]:
        """
        文本搜索：根据查询文本找到最相似的音频文件
        
        Args:
            query: 查询文本
            top_k: 返回前K个结果
            filter_category: 可选的分类过滤（UCS分类）
            
        Returns:
            List of (metadata, score) 元组，按相似度降序排列
        """
        if not query or not query.strip():
            return []
        
        try:
            # 1. 将查询文本转为向量
            query_vector = self.vector_engine.encode(
                query.strip(),
                normalize_embeddings=True
            )
            query_vector = query_vector.reshape(1, -1)  # (1, dim)
            
            # 2. 计算余弦相似度（使用矩阵运算，避免循环）
            # cosine_similarity = dot(query, embeddings) / (||query|| * ||embeddings||)
            # 由于向量已归一化，||query|| = ||embeddings|| = 1
            # 所以 cosine_similarity = dot(query, embeddings)
            similarities = np.dot(self.embeddings, query_vector.T).flatten()
            
            # 3. 应用分类过滤（如果指定）
            if filter_category:
                mask = np.array([
                    filter_category.lower() in str(meta.get('category', '')).lower()
                    for meta in self.metadata
                ])
                similarities = np.where(mask, similarities, -1.0)
            
            # 4. 获取 Top K
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # 5. 构建结果
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # 只返回相似度大于0的结果
                    results.append((
                        self.metadata[idx],
                        float(similarities[idx])
                    ))
            
            return results
            
        except Exception as e:
            raise SearchCoreError(f"文本搜索失败: {e}") from e
    
    def search_by_id(
        self,
        rec_id: int,
        top_k: int = 50
    ) -> List[Tuple[Dict, float]]:
        """
        音频搜音频：根据文件ID找到语义相似的其他文件
        
        Args:
            rec_id: 音频文件的 recID
            top_k: 返回前K个结果
            
        Returns:
            List of (metadata, score) 元组，按相似度降序排列
        """
        # 1. 找到对应ID的向量
        target_idx = None
        for idx, meta in enumerate(self.metadata):
            if meta.get('recID') == rec_id:
                target_idx = idx
                break
        
        if target_idx is None:
            raise SearchCoreError(f"未找到 recID={rec_id} 的记录")
        
        # 2. 获取目标向量
        target_vector = self.embeddings[target_idx:target_idx+1]  # (1, dim)
        
        # 3. 计算与所有向量的相似度
        similarities = np.dot(self.embeddings, target_vector.T).flatten()
        
        # 4. 排除自身（相似度为1.0）
        similarities[target_idx] = -1.0
        
        # 5. 获取 Top K
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # 6. 构建结果
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append((
                    self.metadata[idx],
                    float(similarities[idx])
                ))
        
        return results
    
    def calculate_gravity_forces(
        self,
        target_pillars: List[str]
    ) -> List[Dict[str, float]]:
        """
        计算引力：为UI的"引力视图"服务
        
        计算库中每一个文件与指定"引力桩"（Pillars）的相似度
        
        Args:
            target_pillars: 引力桩列表，例如 ["Fire", "Ice", "Impact"]
            
        Returns:
            List of Dict，每个Dict包含每个文件到各桩的相似度权重
            格式: [{"Fire": 0.85, "Ice": 0.12, "Impact": 0.03}, ...]
        """
        if not target_pillars:
            return []
        
        try:
            # 1. 将引力桩转为向量
            pillar_vectors = self.vector_engine.encode_batch(
                target_pillars,
                batch_size=len(target_pillars),
                show_progress=False,
                normalize_embeddings=True
            )
            
            # 2. 计算每个文件与所有桩的相似度矩阵
            # embeddings: (n_files, dim)
            # pillar_vectors: (n_pillars, dim)
            # similarity_matrix: (n_files, n_pillars)
            similarity_matrix = np.dot(self.embeddings, pillar_vectors.T)
            
            # 3. 将相似度转换为权重（可选：使用softmax归一化）
            # 这里直接使用相似度值，也可以使用softmax
            # weights = self._softmax(similarity_matrix, axis=1)
            weights = similarity_matrix
            
            # 4. 构建结果
            results = []
            for i in range(len(self.metadata)):
                pillar_weights = {
                    pillar: float(weights[i, j])
                    for j, pillar in enumerate(target_pillars)
                }
                results.append(pillar_weights)
            
            return results
            
        except Exception as e:
            raise SearchCoreError(f"引力计算失败: {e}") from e
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        归一化向量（L2归一化）
        
        Args:
            vectors: 向量矩阵
            
        Returns:
            归一化后的向量矩阵
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)  # 避免除零
        return vectors / norms
    
    def _softmax(self, x: np.ndarray, axis: int = 1) -> np.ndarray:
        """
        Softmax归一化（可选，用于引力权重）
        
        Args:
            x: 输入矩阵
            axis: 归一化轴
            
        Returns:
            Softmax归一化后的矩阵
        """
        exp_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return exp_x / np.sum(exp_x, axis=axis, keepdims=True)
    
    def get_statistics(self) -> Dict:
        """
        获取搜索核心的统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_records': len(self.metadata),
            'embedding_dim': self.embeddings.shape[1],
            'vector_memory_mb': self.embeddings.nbytes / (1024 * 1024)
        }

