"""
Sonic Compass - 重建星图脚本
用于初次运行或强制重建数据缓存（向量 + UMAP 坐标）
"""

import sys
import os
import time
from pathlib import Path

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

try:
    import umap
    print("✅ 检测到 UMAP 库")
except ImportError:
    print("❌ 未检测到 UMAP！请先运行: pip install umap-learn scikit-learn matplotlib")
    sys.exit(1)

from data import SoundminerImporter
from core import DataProcessor, VectorEngine


def rebuild():
    """重建星图数据"""
    print("=" * 60)
    print("🚀 Sonic Compass: 正在重绘星系地图 (Rebuilding Atlas)")
    print("=" * 60)
    
    # 1. 配置路径
    DB_PATH = "./test_assets/Sonic.sqlite"
    CACHE_DIR = "./cache"
    
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        print("   请确保数据库文件存在于 test_assets/ 目录")
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
    
    # 3. 强制重建（这会计算向量和 UMAP 坐标）
    print("\n⚙️  开始计算（这可能需要几分钟，请耐心等待）...")
    start_time = time.time()
    
    # 构建索引（向量化）
    metadata, embeddings = processor.build_index(
        limit=None,  # 处理所有数据
        force_rebuild=True  # 强制重建
    )
    
    print(f"✅ 向量化完成 ({len(metadata)} 条记录)")
    print(f"   耗时: {time.time() - start_time:.2f} 秒")
    
    # 4. 计算 UMAP 坐标
    print("\n🗺️  计算 UMAP 坐标...")
    coord_start = time.time()
    
    reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
    coords_2d = reducer.fit_transform(embeddings)
    
    # 保存坐标
    processor.save_coordinates(coords_2d)
    
    print(f"✅ 坐标计算完成")
    print(f"   耗时: {time.time() - coord_start:.2f} 秒")
    
    # 5. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ 星图构建完成！")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    print(f"   坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates.npy')}")
    print("=" * 60)
    print("\n👉 现在可以运行: python main.py")


if __name__ == "__main__":
    rebuild()

