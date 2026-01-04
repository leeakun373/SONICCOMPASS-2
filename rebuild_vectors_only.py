"""
Sonic Compass - 仅重新向量化脚本
用于在已有UMAP坐标的情况下，仅重新计算向量（通常不需要，除非模型更新）
"""

import sys
import os
import time
from pathlib import Path

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

from data import SoundminerImporter
from core import DataProcessor, VectorEngine


def rebuild_vectors_only():
    """仅重新向量化（保留现有UMAP坐标）"""
    print("=" * 60)
    print("🔄 Sonic Compass: 重新向量化 (Rebuild Vectors Only)")
    print("=" * 60)
    print("⚠️  警告: 重新向量化后，现有UMAP坐标将不再匹配！")
    print("   建议: 向量化完成后，运行 python recalculate_umap.py")
    print("=" * 60)
    
    reply = input("\n是否继续？(y/n): ")
    if reply.lower() != 'y':
        print("已取消")
        return
    
    # 1. 配置路径
    DB_PATH = "./test_assets/Sonic.sqlite"
    CACHE_DIR = "./cache"
    
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    # 2. 初始化核心组件
    print("\n📦 初始化引擎...")
    importer = SoundminerImporter(db_path=DB_PATH)
    vector_engine = VectorEngine(model_path="./models/bge-m3")
    
    processor = DataProcessor(
        importer=importer,
        vector_engine=vector_engine,
        cache_dir=CACHE_DIR
    )
    
    # 3. 重新向量化
    print("\n⚙️  开始向量化（这可能需要几分钟）...")
    start_time = time.time()
    
    metadata, embeddings = processor.build_index(
        limit=None,
        force_rebuild=True  # 强制重建
    )
    
    print(f"✅ 向量化完成 ({len(metadata)} 条记录)")
    print(f"   耗时: {time.time() - start_time:.2f} 秒")
    
    # 4. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ 向量化完成！")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    print("=" * 60)
    print("\n⚠️  注意: 现有UMAP坐标已失效，请运行:")
    print("   python recalculate_umap.py")


if __name__ == "__main__":
    rebuild_vectors_only()

