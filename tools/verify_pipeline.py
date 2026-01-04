"""
集成测试脚本 - 验证完整流水线
将 config, ucs, importer, vector 全部串起来测试
"""

import time
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data import SoundminerImporter, ConfigLoader
from core import VectorEngine, UCSManager

# 向后兼容
AudioMetadata = SoundminerImporter.AudioMetadata if hasattr(SoundminerImporter, 'AudioMetadata') else None
ConfigManager = ConfigLoader  # 别名


# 路径配置 (指向你的测试素材)
TEST_DB_PATH = "./test_assets/Sonic.sqlite"
MODEL_PATH = "./models/bge-m3"


def run_verification():
    print("=" * 60)
    print("[START] 开始 Phase 1 集成验证 (Pipeline Check)")
    print("=" * 60)

    # --- 步骤 0: 加载配置和UCS管理器 ---
    print("\n[0/4] 加载配置和UCS管理器...")
    try:
        config_manager = ConfigManager()
        config_manager.load_all()
        print(f"[OK] ConfigManager 加载完成: {len(config_manager.axis_definitions)} 个轴, "
              f"{len(config_manager.presets)} 个预设, {len(config_manager.pillars)} 个支柱")
        
        ucs_manager = UCSManager()
        ucs_manager.load_all()
        print(f"[OK] UCSManager 加载完成: {len(ucs_manager.catid_to_category)} 个分类, "
              f"{len(ucs_manager.alias_to_catid)} 个别名")
    except Exception as e:
        print(f"[ERROR] 配置加载失败: {e}")
        return

    # --- 步骤 1: 实例化 Importer ---
    print(f"\n[1/4] 连接数据库: {TEST_DB_PATH}...")
    try:
        importer = SoundminerImporter(db_path=TEST_DB_PATH, ucs_manager=ucs_manager)
        # 提取前 5 条数据用于测试
        data_batch = importer.import_all(limit=5)
        
        if not data_batch:
            print("[ERROR] 错误: 数据库为空或读取失败！")
            return
        
        print(f"[OK] 成功读取 {len(data_batch)} 条记录。")
        print(f"   第一条样本语义文本: \"{data_batch[0].semantic_text[:100]}...\"")
        print(f"   第一条样本详情:")
        print(f"     - RecID: {data_batch[0].recID}")
        print(f"     - 文件名: {data_batch[0].filename}")
        print(f"     - 分类: {data_batch[0].category}")
        
    except Exception as e:
        print(f"[ERROR] Importer 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        importer.close()

    # --- 步骤 2: 实例化 AI 引擎 ---
    print(f"\n[2/4] 加载 BGE-M3 模型: {MODEL_PATH}...")
    try:
        start_load = time.time()
        engine = VectorEngine(model_path=MODEL_PATH)
        load_time = time.time() - start_load
        print(f"[OK] 模型加载完成 (耗时: {load_time:.2f}s)")
        print(f"   设备: {engine.device}")
        print(f"   向量维度: {engine.get_embedding_dim()}")
    except Exception as e:
        print(f"[ERROR] VectorEngine 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- 步骤 3: 向量化处理 (核心握手) ---
    print("\n[3/4] 执行向量化 (Text -> Vector)...")
    try:
        # 提取 semantic_text 列表
        texts = [item.semantic_text for item in data_batch if item.semantic_text]
        
        if not texts:
            print("[ERROR] 错误: 没有可用的语义文本！")
            return
        
        print(f"   准备编码 {len(texts)} 条文本...")
        start_encode = time.time()
        vectors = engine.encode_batch(texts, batch_size=2, show_progress=True)
        encode_time = time.time() - start_encode
        
        print(f"[OK] 向量化完成 (耗时: {encode_time:.2f}s)")
        print("-" * 60)
        
        # 验证维度
        expected_dim = 1024
        if vectors.shape[1] == expected_dim:
            print(f"[SUCCESS] 验证通过! 输出形状: {vectors.shape} ({vectors.shape[0]}条数据, {expected_dim}维)")
            print("   数据流向: SQLite -> UCS清洗 -> Semantic Text -> BGE-M3 -> Numpy Array")
        else:
            print(f"[WARNING] 警告: 向量维度异常! 期望 {expected_dim}, 实际 {vectors.shape[1]}")
        
        # 显示一些统计信息
        print(f"\n   向量统计:")
        print(f"   - 均值: {np.mean(vectors):.6f}")
        print(f"   - 标准差: {np.std(vectors):.6f}")
        print(f"   - 最小值: {np.min(vectors):.6f}")
        print(f"   - 最大值: {np.max(vectors):.6f}")
        
    except Exception as e:
        print(f"[ERROR] 向量化过程出错: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- 步骤 4: 相似度测试 ---
    print("\n[4/4] 测试向量相似度计算...")
    try:
        if len(vectors) >= 2:
            # 计算第一条和第二条的相似度
            similarity = np.dot(vectors[0], vectors[1])
            print(f"[OK] 相似度计算成功")
            print(f"   文本1 和 文本2 的余弦相似度: {similarity:.4f}")
            
            # 计算所有文本之间的相似度矩阵
            similarity_matrix = np.dot(vectors, vectors.T)
            print(f"   相似度矩阵形状: {similarity_matrix.shape}")
            print(f"   平均相似度: {np.mean(similarity_matrix):.4f}")
        else:
            print("[WARNING] 数据不足，跳过相似度测试")
    except Exception as e:
        print(f"[ERROR] 相似度计算失败: {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] 集成验证完成！所有模块工作正常。")
    print("=" * 60)


if __name__ == "__main__":
    run_verification()

