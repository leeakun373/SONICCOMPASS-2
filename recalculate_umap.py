"""
Sonic Compass - 仅重新计算UMAP坐标脚本
用于在已有向量缓存的情况下，仅重新计算UMAP坐标（适用于参数调整）
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
    print("❌ 未检测到 UMAP！请先运行: pip install umap-learn")
    sys.exit(1)

try:
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    print("❌ 未检测到 scikit-learn！请先运行: pip install scikit-learn")
    sys.exit(1)

from data import SoundminerImporter
from core import DataProcessor, VectorEngine


def recalculate_umap():
    """仅重新计算UMAP坐标（使用现有向量缓存）"""
    print("=" * 60)
    print("🔄 Sonic Compass: 重新计算UMAP坐标 (Recalculate UMAP Only)")
    print("=" * 60)
    
    # 1. 配置路径
    DB_PATH = "./test_assets/Sonic.sqlite"
    CACHE_DIR = "./cache"
    
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    # 2. 初始化核心组件
    print("\n📦 初始化引擎...")
    print("   正在初始化 SoundminerImporter...")
    try:
        from core import UCSManager
        ucs_manager = UCSManager()
        ucs_manager.load_all()
        importer = SoundminerImporter(
            db_path=DB_PATH,
            ucs_manager=ucs_manager
        )
    except Exception as e:
        print(f"   [WARNING] UCSManager 初始化失败，使用默认配置: {e}")
        importer = SoundminerImporter(db_path=DB_PATH)
    
    print("   正在加载向量模型（这可能需要几秒钟）...")
    import sys
    sys.stdout.flush()  # 强制刷新输出
    
    try:
        vector_engine = VectorEngine(model_path="./models/bge-m3")
        print("   ✅ 模型加载完成")
    except Exception as e:
        print(f"   ❌ 模型加载失败: {e}")
        sys.exit(1)
    
    print("   正在创建 DataProcessor...")
    processor = DataProcessor(
        importer=importer,
        vector_engine=vector_engine,
        cache_dir=CACHE_DIR
    )
    print("   ✅ 初始化完成")
    
    # 3. 检查缓存是否存在
    if not processor._cache_exists():
        print("❌ 向量缓存不存在！")
        print("   请先运行: python rebuild_atlas.py")
        sys.exit(1)
    
    # 4. 加载现有向量和元数据（不重新计算）
    print("\n📂 加载现有向量缓存...")
    start_time = time.time()
    
    try:
        metadata, embeddings = processor.load_index()
        print(f"✅ 加载完成 ({len(metadata)} 条记录)")
        print(f"   耗时: {time.time() - start_time:.2f} 秒")
    except Exception as e:
        print(f"❌ 加载缓存失败: {e}")
        print("   请先运行: python rebuild_atlas.py")
        sys.exit(1)
    
    # 5. Phase 3.5: 提取仲裁后的 Category 并编码为标签
    print("\n🏷️  提取 Category 标签（使用仲裁后的 Category）...")
    
    categories = []
    for meta in metadata:
        # Phase 3.5: 直接使用仲裁后的 Category（已在 data_processor 中保存）
        category = meta.get('category', 'UNCATEGORIZED')
        if not category or category == '':
            category = "UNCATEGORIZED"
        categories.append(category)
    
    # 使用 LabelEncoder 编码为整数数组
    label_encoder = LabelEncoder()
    targets = label_encoder.fit_transform(categories)
    
    print(f"   发现 {len(label_encoder.classes_)} 个 Category")
    
    # 6. Phase 3.5: 计算 Supervised UMAP 坐标（使用极强监督参数）
    print("\n🗺️  计算 Supervised UMAP 坐标（Phase 3.5 极强监督参数）...")
    print("   参数: target_weight=0.95 (铁腕统治), n_neighbors=50, min_dist=0.001, spread=0.5 (大陆板块)")
    print("   ⏳ 这可能需要几分钟，请耐心等待...")
    import sys
    sys.stdout.flush()  # 强制刷新输出
    
    coord_start = time.time()
    
    try:
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=50,       # 从30提升到50 (吸附更多周围的点)
            min_dist=0.001,       # 从0.01降低到0.001 (允许极度紧密)
            spread=0.5,           # 降低扩散 (默认1.0)，让群岛聚拢
            metric='cosine',
            target_weight=0.95,   # 【关键】提升到 0.95，实施铁腕统治
            target_metric='categorical',
            random_state=42,
            n_jobs=1
        )
        print("   [进度] 正在运行 UMAP fit_transform...")
        sys.stdout.flush()
        coords_2d = reducer.fit_transform(embeddings, y=targets)
    except Exception as e:
        print(f"   ❌ UMAP 计算失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 坐标归一化到 0-3000 范围
    min_coords = coords_2d.min(axis=0)
    max_coords = coords_2d.max(axis=0)
    scale = 3000.0 / (np.max(max_coords - min_coords) + 1e-5)
    coords_2d = (coords_2d - min_coords) * scale
    
    # 保存坐标
    processor.save_coordinates(coords_2d)
    
    print(f"✅ 坐标计算完成")
    print(f"   耗时: {time.time() - coord_start:.2f} 秒")
    print(f"   坐标范围: [{coords_2d.min(axis=0)[0]:.1f}, {coords_2d.min(axis=0)[1]:.1f}] 到 [{coords_2d.max(axis=0)[0]:.1f}, {coords_2d.max(axis=0)[1]:.1f}]")
    
    # 7. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ UMAP坐标重新计算完成！")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    print(f"   坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates.npy')}")
    print("=" * 60)
    print("\n👉 现在可以运行: python main.py")


if __name__ == "__main__":
    recalculate_umap()

