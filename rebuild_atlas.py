"""
Sonic Compass - 重建星图脚本
用于初次运行或强制重建数据缓存（向量 + UMAP 坐标）
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

try:
    import umap
    print("✅ 检测到 UMAP 库")
except ImportError:
    print("❌ 未检测到 UMAP！请先运行: pip install umap-learn scikit-learn matplotlib")
    sys.exit(1)

try:
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    print("❌ 未检测到 scikit-learn！请先运行: pip install scikit-learn")
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
    print("   [步骤 1/4] 加载数据并计算 Category 质心...")
    start_time = time.time()
    
    # 构建索引（向量化）
    # 注意：build_index 内部会先计算质心，这个过程可能较慢
    print("   [步骤 2/4] 向量化数据（使用 GPU 加速）...")
    metadata, embeddings = processor.build_index(
        limit=None,  # 处理所有数据
        force_rebuild=True  # 强制重建
    )
    
    print(f"✅ 向量化完成 ({len(metadata)} 条记录)")
    print(f"   耗时: {time.time() - start_time:.2f} 秒")
    
    # 4. 提取 Category 并编码为标签
    print("\n🏷️  提取 Category 标签...")
    try:
        from core.category_color_mapper import CategoryColorMapper
        mapper = CategoryColorMapper()
    except Exception as e:
        print(f"[WARNING] 无法加载 CategoryColorMapper: {e}")
        mapper = None
    
    categories = []
    for meta in metadata:
        cat_id = meta.get('category', '')
        if mapper:
            category = mapper.get_category_from_catid(cat_id)
            if not category:
                category = "UNCATEGORIZED"
        else:
            category = "UNCATEGORIZED"
        categories.append(category)
    
    # 使用 LabelEncoder 编码为整数数组
    label_encoder = LabelEncoder()
    targets = label_encoder.fit_transform(categories)
    
    print(f"   发现 {len(label_encoder.classes_)} 个 Category")
    print(f"   类别: {', '.join(label_encoder.classes_[:10])}{'...' if len(label_encoder.classes_) > 10 else ''}")
    
    # 5. 计算 Supervised UMAP 坐标
    print("\n🗺️  计算 Supervised UMAP 坐标...")
    coord_start = time.time()
    
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,       # 降低内存消耗，防止19GB报错
        min_dist=0.1,         # 内部点分布稍微紧凑
        spread=1.0,           # 限制扩散范围
        metric='cosine',      # 使用余弦相似度（对音频语义更好）
        target_weight=0.7,    # 强制形成大陆板块，允许30%语义漂移
        target_metric='categorical',  # 分类标签
        random_state=42,
        n_jobs=1              # 避免并行计算导致的微小差异
    )
    coords_2d = reducer.fit_transform(embeddings, y=targets)
    
    # 坐标归一化到 0-3000 范围（减少"海洋"空隙）
    min_coords = coords_2d.min(axis=0)
    max_coords = coords_2d.max(axis=0)
    scale = 3000.0 / (np.max(max_coords - min_coords) + 1e-5)
    coords_2d = (coords_2d - min_coords) * scale
    
    # 保存坐标
    processor.save_coordinates(coords_2d)
    
    print(f"✅ 坐标计算完成")
    print(f"   耗时: {time.time() - coord_start:.2f} 秒")
    print(f"   坐标范围: [{coords_2d.min(axis=0)[0]:.1f}, {coords_2d.min(axis=0)[1]:.1f}] 到 [{coords_2d.max(axis=0)[0]:.1f}, {coords_2d.max(axis=0)[1]:.1f}]")
    
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

