"""
BGE-M3 模型部署脚本
自动下载并部署 BGE-M3 模型到本地
"""

import os
from pathlib import Path
from sentence_transformers import SentenceTransformer


def deploy_bge_m3(model_dir: str = "./models/bge-m3", model_name: str = "BAAI/bge-m3"):
    """
    部署 BGE-M3 模型
    
    Args:
        model_dir: 本地模型保存目录
        model_name: HuggingFace 模型名称
    """
    model_path = Path(model_dir)
    
    # 检查模型是否已存在
    if model_path.exists() and any(model_path.iterdir()):
        print(f"模型已存在于: {model_path}")
        print("正在验证模型完整性...")
        
        try:
            # 尝试加载模型验证
            model = SentenceTransformer(str(model_path))
            print("[OK] 模型验证成功，可以正常使用")
            print(f"  向量维度: {model.get_sentence_embedding_dimension()}")
            return True
        except Exception as e:
            print(f"[ERROR] 模型验证失败: {e}")
            print("  将重新下载模型...")
            # 删除损坏的模型
            import shutil
            shutil.rmtree(model_path)
            model_path.mkdir(parents=True, exist_ok=True)
    
    # 下载模型
    print(f"\n正在从 HuggingFace 下载模型: {model_name}")
    print(f"保存路径: {model_path.absolute()}")
    print("这可能需要一些时间，请耐心等待...\n")
    
    try:
        # 下载并保存模型
        model = SentenceTransformer(model_name)
        model.save(str(model_path))
        
        print(f"\n[OK] 模型下载完成！")
        print(f"  保存位置: {model_path.absolute()}")
        print(f"  向量维度: {model.get_sentence_embedding_dimension()}")
        
        # 测试编码
        print("\n正在测试模型...")
        test_text = "这是一个测试文本"
        embedding = model.encode(test_text)
        print(f"[OK] 测试成功！向量形状: {embedding.shape}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 模型下载失败: {e}")
        print("\n提示:")
        print("1. 检查网络连接")
        print("2. 确保已安装: pip install sentence-transformers")
        print("3. 如果使用代理，请配置 HuggingFace 镜像")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("BGE-M3 模型部署工具")
    print("=" * 60)
    print()
    
    # 部署模型
    success = deploy_bge_m3()
    
    if success:
        print("\n" + "=" * 60)
        print("部署完成！现在可以使用 vector_engine.py 了")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("部署失败，请检查错误信息")
        print("=" * 60)
