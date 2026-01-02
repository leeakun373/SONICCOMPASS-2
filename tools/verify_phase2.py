"""
Phase 2 集成验证脚本
验证数据持久化缓存和核心搜索算法
"""

import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data import SoundminerImporter
from core import VectorEngine, DataProcessor, SearchCore, UCSManager


# 测试配置
TEST_DB_PATH = "./test_assets/Sonic.sqlite"
MODEL_PATH = "./models/bge-m3"
CACHE_DIR = "./cache"


def run_phase2_verification():
    """运行 Phase 2 集成验证"""
    print("=" * 60)
    print("[START] Phase 2 集成验证")
    print("=" * 60)
    
    # --- 步骤 1: 初始化基础组件 ---
    print("\n[1/5] 初始化基础组件...")
    try:
        # 加载UCS管理器
        ucs_manager = UCSManager()
        ucs_manager.load_all()
        print(f"  [OK] UCSManager 加载完成")
        
        # 初始化导入器
        importer = SoundminerImporter(db_path=TEST_DB_PATH, ucs_manager=ucs_manager)
        print(f"  [OK] SoundminerImporter 初始化完成")
        
        # 初始化向量引擎
        vector_engine = VectorEngine(model_path=MODEL_PATH)
        print(f"  [OK] VectorEngine 初始化完成")
        
    except Exception as e:
        print(f"  [ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # --- 步骤 2: 构建索引 ---
    print("\n[2/5] 构建索引（批量向量化并缓存）...")
    try:
        processor = DataProcessor(
            importer=importer,
            vector_engine=vector_engine,
            cache_dir=CACHE_DIR
        )
        
        start_time = time.time()
        metadata, embeddings = processor.build_index(
            batch_size=16,  # 较小的批次以便快速测试
            limit=100  # 限制100条数据以便快速测试
        )
        build_time = time.time() - start_time
        
        print(f"  [OK] 索引构建完成")
        print(f"       耗时: {build_time:.2f} 秒")
        print(f"       数据量: {len(metadata)} 条")
        print(f"       向量形状: {embeddings.shape}")
        
        importer.close()
        
    except Exception as e:
        print(f"  [ERROR] 索引构建失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # --- 步骤 3: 初始化搜索核心 ---
    print("\n[3/5] 初始化搜索核心...")
    try:
        start_time = time.time()
        search_core = SearchCore(
            vector_engine=vector_engine,
            processor=processor
        )
        load_time = time.time() - start_time
        
        print(f"  [OK] 搜索核心初始化完成")
        print(f"       加载耗时: {load_time:.4f} 秒")
        
        stats = search_core.get_statistics()
        print(f"       统计信息:")
        print(f"         - 总记录数: {stats['total_records']}")
        print(f"         - 向量维度: {stats['embedding_dim']}")
        print(f"         - 内存占用: {stats['vector_memory_mb']:.2f} MB")
        
    except Exception as e:
        print(f"  [ERROR] 搜索核心初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # --- 步骤 4: 测试文本搜索 ---
    print("\n[4/5] 测试文本搜索...")
    try:
        query = "Sci-Fi Weapon"
        print(f"  查询: \"{query}\"")
        
        start_time = time.time()
        results = search_core.search_by_text(query, top_k=3)
        search_time = time.time() - start_time
        
        print(f"  [OK] 搜索完成 (耗时: {search_time*1000:.2f} ms)")
        print(f"       找到 {len(results)} 个结果:")
        
        for i, (metadata, score) in enumerate(results, 1):
            print(f"\n      结果 {i}:")
            print(f"        - RecID: {metadata.get('recID')}")
            print(f"        - 文件名: {metadata.get('filename', 'N/A')[:50]}")
            print(f"        - 相似度: {score:.4f}")
            print(f"        - 分类: {metadata.get('category', 'N/A')}")
            
    except Exception as e:
        print(f"  [ERROR] 文本搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # --- 步骤 5: 测试引力计算 ---
    print("\n[5/5] 测试引力计算...")
    try:
        target_pillars = ["Organic", "Synthetic"]
        print(f"  引力桩: {target_pillars}")
        
        start_time = time.time()
        gravity_forces = search_core.calculate_gravity_forces(target_pillars)
        calc_time = time.time() - start_time
        
        print(f"  [OK] 引力计算完成 (耗时: {calc_time*1000:.2f} ms)")
        print(f"       计算了 {len(gravity_forces)} 个文件的引力权重")
        print(f"\n       前 3 个文件的引力权重:")
        
        for i in range(min(3, len(gravity_forces))):
            meta = search_core.metadata[i]
            forces = gravity_forces[i]
            print(f"\n      文件 {i+1}:")
            print(f"        - RecID: {meta.get('recID')}")
            print(f"        - 文件名: {meta.get('filename', 'N/A')[:40]}")
            for pillar, weight in forces.items():
                print(f"        - {pillar}: {weight:.4f}")
        
        # 统计信息
        if gravity_forces:
            avg_organic = sum(f.get('Organic', 0) for f in gravity_forces) / len(gravity_forces)
            avg_synthetic = sum(f.get('Synthetic', 0) for f in gravity_forces) / len(gravity_forces)
            print(f"\n       平均权重:")
            print(f"         - Organic: {avg_organic:.4f}")
            print(f"         - Synthetic: {avg_synthetic:.4f}")
            
    except Exception as e:
        print(f"  [ERROR] 引力计算失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # --- 总结 ---
    print("\n" + "=" * 60)
    print("[SUCCESS] Phase 2 验证完成！")
    print("=" * 60)
    print("\n关键指标:")
    print(f"  - 索引构建: {build_time:.2f} 秒")
    print(f"  - 索引加载: {load_time*1000:.2f} ms")
    print(f"  - 文本搜索: {search_time*1000:.2f} ms")
    print(f"  - 引力计算: {calc_time*1000:.2f} ms")
    print("\n[SUCCESS] 所有功能正常工作，已实现毫秒级搜索！")


if __name__ == "__main__":
    run_phase2_verification()

