"""
AI 向量引擎
使用 BGE-M3 模型将文本转换为向量
"""

import torch
from pathlib import Path
from typing import List, Union, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError(
        "需要安装 sentence_transformers 库。"
        "请运行: pip install sentence-transformers"
    )


class VectorEngineError(Exception):
    """向量引擎错误"""
    pass


class VectorEngine:
    """BGE-M3 向量引擎"""
    
    def __init__(self, model_path: str | Path = "./models/bge-m3"):
        """
        初始化向量引擎
        
        Args:
            model_path: 模型路径（默认: ./models/bge-m3）
                       可以是本地路径或 HuggingFace 模型名称（如 "BAAI/bge-m3"）
        """
        self.model_path_str = str(model_path)
        self.model_path = Path(model_path)
        
        # 检测设备
        self.device = self._detect_device()
        
        # 加载模型
        try:
            print(f"正在加载模型: {self.model_path_str}")
            print(f"使用设备: {self.device}")
            
            # 显式指定设备，确保使用 GPU（如果可用）
            device_str = self.device
            if device_str == 'cuda' and not torch.cuda.is_available():
                print("[WARNING] CUDA 不可用，回退到 CPU")
                device_str = 'cpu'
            elif device_str == 'mps' and (not hasattr(torch.backends, 'mps') or not torch.backends.mps.is_available()):
                print("[WARNING] MPS 不可用，回退到 CPU")
                device_str = 'cpu'
            
            # 如果路径是目录且存在，加载本地模型
            # 否则假设是 HuggingFace 模型名称
            if self.model_path.exists() and self.model_path.is_dir():
                self.model = SentenceTransformer(
                    str(self.model_path),
                    device=device_str  # 显式传递设备
                )
            else:
                # 尝试作为 HuggingFace 模型名称加载
                # 首次运行会自动下载
                self.model = SentenceTransformer(
                    self.model_path_str,
                    device=device_str  # 显式传递设备
                )
            
            # 验证模型实际使用的设备
            if hasattr(self.model, '_modules') and len(self.model._modules) > 0:
                first_module = list(self.model._modules.values())[0]
                if hasattr(first_module, 'device'):
                    actual_device = str(first_module.device)
                    print(f"模型实际运行在: {actual_device}")
            
            print("模型加载完成")
            
        except Exception as e:
            raise VectorEngineError(f"加载模型失败: {e}") from e
    
    def _detect_device(self) -> str:
        """
        自动检测可用的计算设备
        
        Returns:
            设备名称 ('cuda', 'mps', 或 'cpu')
        """
        if torch.cuda.is_available():
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return 'mps'
        else:
            return 'cpu'
    
    def encode_batch(
        self,
        texts: List[str],
        batch_size: int = None,
        show_progress: bool = True,
        normalize_embeddings: bool = True
    ) -> np.ndarray:
        """
        批量编码文本为向量
        
        Args:
            texts: 文本列表
            batch_size: 批处理大小（如果为 None，将根据设备自动选择）
            show_progress: 是否显示进度条
            normalize_embeddings: 是否归一化向量
            
        Returns:
            numpy数组，形状为 (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        try:
            # 如果没有指定 batch_size，根据设备自动选择
            if batch_size is None:
                if self.device == 'cuda':
                    batch_size = 64  # GPU 可以使用更大的 batch size
                elif self.device == 'mps':
                    batch_size = 32  # MPS 使用中等 batch size
                else:
                    batch_size = 16  # CPU 使用较小的 batch size
            
            # 过滤空文本
            valid_texts = [text if text else "" for text in texts]
            
            # 使用模型编码
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=normalize_embeddings,
                convert_to_numpy=True
            )
            
            return embeddings
            
        except Exception as e:
            raise VectorEngineError(f"编码失败: {e}") from e
    
    def encode(
        self,
        text: str,
        normalize_embeddings: bool = True
    ) -> np.ndarray:
        """
        编码单个文本为向量
        
        Args:
            text: 输入文本
            normalize_embeddings: 是否归一化向量
            
        Returns:
            numpy数组，形状为 (embedding_dim,)
        """
        if not text:
            # 返回零向量（维度需要从模型获取）
            # 这里先编码一个空字符串来获取维度
            dummy_embedding = self.model.encode([""], convert_to_numpy=True)
            return np.zeros_like(dummy_embedding[0])
        
        embeddings = self.encode_batch(
            [text],
            batch_size=1,
            show_progress=False,
            normalize_embeddings=normalize_embeddings
        )
        
        return embeddings[0]
    
    def get_embedding_dim(self) -> int:
        """
        获取向量维度
        
        Returns:
            向量维度
        """
        # 编码一个空字符串来获取维度
        dummy_embedding = self.encode("")
        return dummy_embedding.shape[0]


if __name__ == "__main__":
    # 测试代码
    import time
    
    # 测试模型路径（如果本地没有，可以使用 HuggingFace 模型名称）
    # 例如: "BAAI/bge-m3" 或 "./models/bge-m3"
    TEST_MODEL_PATH = "./models/bge-m3"
    
    # 如果本地模型不存在，尝试使用 HuggingFace 模型
    if not Path(TEST_MODEL_PATH).exists():
        print(f"本地模型不存在: {TEST_MODEL_PATH}")
        print("尝试使用 HuggingFace 模型: BAAI/bge-m3")
        TEST_MODEL_PATH = "BAAI/bge-m3"
    
    try:
        print("初始化向量引擎...")
        engine = VectorEngine(model_path=TEST_MODEL_PATH)
        
        print(f"\n向量维度: {engine.get_embedding_dim()}")
        
        # 测试单个文本编码
        test_text = "这是一个测试文本，用于验证向量编码功能。"
        print(f"\n测试单个文本编码:")
        print(f"输入文本: {test_text}")
        
        start_time = time.time()
        embedding = engine.encode(test_text)
        elapsed = time.time() - start_time
        
        print(f"编码耗时: {elapsed:.4f} 秒")
        print(f"向量形状: {embedding.shape}")
        print(f"向量前10个值: {embedding[:10]}")
        
        # 测试批量编码
        test_texts = [
            "这是一个测试文本。",
            "This is a test text.",
            "音频文件：枪声、爆炸声、环境音。",
            "Sound effects: gunshot, explosion, ambience.",
            "魔法咒语，能量爆发，元素攻击。"
        ]
        
        print(f"\n测试批量编码 ({len(test_texts)} 个文本):")
        start_time = time.time()
        embeddings = engine.encode_batch(test_texts, batch_size=2)
        elapsed = time.time() - start_time
        
        print(f"批量编码耗时: {elapsed:.4f} 秒")
        print(f"向量形状: {embeddings.shape}")
        print(f"平均每个文本耗时: {elapsed/len(test_texts):.4f} 秒")
        
        # 测试相似度计算
        print(f"\n测试相似度计算:")
        similarity = np.dot(embeddings[0], embeddings[1])
        print(f"文本1和文本2的余弦相似度: {similarity:.4f}")
        
    except VectorEngineError as e:
        print(f"向量引擎错误: {e}")
        print("\n提示:")
        print("1. 确保已安装 sentence-transformers: pip install sentence-transformers")
        print("2. 如果使用本地模型，请确保模型文件存在于指定路径")
        print("3. 如果使用 HuggingFace 模型，首次运行会自动下载")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

