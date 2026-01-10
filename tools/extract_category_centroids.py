"""
提取类别质心脚本 - 生成 ucs_coordinates.json 初稿

从现有的 coordinates.npy 和 metadata 中提取82个大类的质心，
生成 ucs_coordinates.json 初稿，便于后续人工微调。

算法优化:
- 使用Median（中位数）而非Mean，避免离群点影响
- 剔除Top 5%和Bottom 5%的离群点
- 计算2%-98%分位数范围作为radius初值
- 自动计算gap_buffer（radius * 0.15）
"""

import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from typing import Tuple, Set

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import UCSManager


def extract_centroids_median(coords: np.ndarray) -> Tuple[float, float]:
    """
    使用Median（中位数）提取质心
    
    Args:
        coords: 坐标数组 (N, 2)
        
    Returns:
        (median_x, median_y)
    """
    if len(coords) == 0:
        return (0.0, 0.0)
    
    median_x = np.median(coords[:, 0])
    median_y = np.median(coords[:, 1])
    
    return (median_x, median_y)


def calculate_radius_robust(coords: np.ndarray, center_x: float, center_y: float) -> float:
    """
    使用Robust方法计算半径（严格剔除离群点）
    
    【重要说明】
    - 此函数只用于计算 radius，不影响实际数据放置
    - 实际数据放置使用 place_local_coords()，会强制限制在 radius 范围内
    - 因此，剔除离群点只是为了让 radius 更合理，不会让数据"逃离"大类范围
    
    Args:
        coords: 坐标数组 (N, 2)
        center_x: 中心X坐标
        center_y: 中心Y坐标
        
    Returns:
        radius: 半径初值（已剔除离群点）
    """
    if len(coords) == 0:
        return 10.0  # 默认半径
    
    # 计算每个点到中心的距离
    distances = np.sqrt((coords[:, 0] - center_x)**2 + (coords[:, 1] - center_y)**2)
    
    # 【优化策略】使用更严格的离群点剔除
    # 对于大数据集，使用更严格的分位数范围
    if len(distances) > 20:
        # 策略1：使用中位数 + IQR（四分位距）方法（最稳健）
        median_dist = np.median(distances)
        q1 = np.percentile(distances, 25)
        q3 = np.percentile(distances, 75)
        iqr = q3 - q1
        
        # 使用 1.5×IQR 规则剔除极端离群点（统计学标准方法）
        # 保留 [Q1 - 1.5×IQR, Q3 + 1.5×IQR] 范围内的点
        lower_bound = max(0, q1 - 1.5 * iqr)
        upper_bound = q3 + 1.5 * iqr
        
        filtered_distances = distances[(distances >= lower_bound) & (distances <= upper_bound)]
        
        if len(filtered_distances) > 10:
            # 使用过滤后的数据计算更紧凑的半径
            # 策略：使用90%分位数（而非98%），避免被极端值影响
            p90 = np.percentile(filtered_distances, 90)
            # 也可以使用中位数 + 1.5×IQR（更保守）
            median_filtered = np.median(filtered_distances)
            q1_filtered = np.percentile(filtered_distances, 25)
            q3_filtered = np.percentile(filtered_distances, 75)
            iqr_filtered = q3_filtered - q1_filtered
            robust_radius = median_filtered + 1.5 * iqr_filtered
            
            # 取两者中较小值（更保守，避免 radius 过大）
            radius = min(p90, robust_radius)
        else:
            # 如果过滤后数据太少，使用原始数据的75%分位数（保守估计）
            radius = np.percentile(distances, 75)
    elif len(distances) > 5:
        # 中等数据集：使用75%分位数（避免被极端值影响）
        radius = np.percentile(distances, 75)
    else:
        # 小数据集：直接使用最大距离
        radius = np.max(distances)
    
    # 【空间优化】根据数据量动态调整 radius 上限
    # 避免单个大类占用过多空间，确保82个大类能在3000×3000范围内合理分布
    # 经验值：单个大类的 radius 不应超过总范围的 10%（即 300）
    max_radius_limit = 300.0
    if radius > max_radius_limit:
        print(f"      [警告] 计算的radius({radius:.2f})超过上限({max_radius_limit})，已限制")
        radius = max_radius_limit
    
    # 确保最小值
    radius = max(radius, 5.0)
    
    return float(radius)


def load_all_main_categories_from_csv(csv_path: Path) -> Set[str]:
    """
    从 ucs_catid_list.csv 读取所有唯一的主类别
    
    Args:
        csv_path: CSV文件路径
        
    Returns:
        主类别集合（全部大写）
    """
    if not csv_path.exists():
        print(f"   ⚠️  CSV文件不存在: {csv_path}")
        return set()
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        if 'Category' not in df.columns:
            print(f"   ⚠️  CSV文件缺少 'Category' 列")
            return set()
        
        # 获取所有唯一的主类别（全部大写），过滤掉NaN值
        categories = df['Category'].dropna().astype(str).str.upper().unique()
        # 过滤掉空字符串
        main_categories = {cat for cat in categories if cat and cat.strip()}
        return main_categories
    except Exception as e:
        print(f"   ⚠️  读取CSV文件失败: {e}")
        import traceback
        traceback.print_exc()
        return set()


def extract_category_centroids():
    """提取类别质心并生成 ucs_coordinates.json"""
    print("=" * 60)
    print("🔍 提取类别质心 (Extract Category Centroids)")
    print("=" * 60)
    
    # 1. 配置路径
    CACHE_DIR = Path("./cache")
    CONFIG_DIR = Path("./data_config")
    CSV_PATH = CONFIG_DIR / "ucs_catid_list.csv"
    # 优先使用 coordinates_ucs.npy，如果没有则使用 coordinates.npy（向后兼容）
    COORDS_PATH_UCS = CACHE_DIR / "coordinates_ucs.npy"
    COORDS_PATH_LEGACY = CACHE_DIR / "coordinates.npy"
    COORDS_PATH = COORDS_PATH_UCS if COORDS_PATH_UCS.exists() else COORDS_PATH_LEGACY
    METADATA_PATH = CACHE_DIR / "metadata.pkl"
    OUTPUT_PATH = CONFIG_DIR / "ucs_coordinates.json"
    
    # 2. 首先从CSV文件读取所有主类别（确保82个都包含）
    print("\n📋 从 ucs_catid_list.csv 读取所有主类别...")
    all_main_categories = load_all_main_categories_from_csv(CSV_PATH)
    
    if len(all_main_categories) == 0:
        print("   ❌ 无法从CSV文件读取主类别")
        print(f"   请检查文件是否存在: {CSV_PATH}")
        sys.exit(1)
    
    print(f"   ✅ 找到 {len(all_main_categories)} 个主类别（来自CSV）")
    
    # 3. 检查坐标文件（如果存在，用于提取质心；如果不存在，使用默认值）
    has_coords = False
    coords = None
    metadata = []
    
    if COORDS_PATH.exists() and METADATA_PATH.exists():
        print("\n📂 加载现有坐标数据（用于提取质心）...")
        try:
            coords = np.load(COORDS_PATH)
            with open(METADATA_PATH, 'rb') as f:
                metadata = pickle.load(f)
            has_coords = True
            print(f"   ✅ 使用坐标文件: {COORDS_PATH.name}")
            print(f"   ✅ 坐标形状: {coords.shape}")
            print(f"   ✅ 元数据数量: {len(metadata)}")
            
            # 验证坐标和元数据长度一致
            if len(coords) != len(metadata):
                print(f"   ⚠️  警告: 坐标数量({len(coords)})与元数据数量({len(metadata)})不一致")
                # 使用较小的长度
                min_len = min(len(coords), len(metadata))
                coords = coords[:min_len]
                metadata = metadata[:min_len]
                print(f"   ✅ 已截断到最小长度: {min_len}")
        except Exception as e:
            print(f"   ⚠️  加载坐标数据失败: {e}")
            import traceback
            traceback.print_exc()
            print("   将继续使用默认坐标")
    else:
        print("\n⚠️  未找到现有坐标数据")
        print(f"   尝试的文件:")
        print(f"     - {COORDS_PATH_UCS.name}: {'存在' if COORDS_PATH_UCS.exists() else '不存在'}")
        print(f"     - {COORDS_PATH_LEGACY.name}: {'存在' if COORDS_PATH_LEGACY.exists() else '不存在'}")
        print(f"   元数据文件: {METADATA_PATH} {'存在' if METADATA_PATH.exists() else '不存在'}")
        print("   将为所有类别使用默认坐标")
        print("\n💡 提示:")
        print("   要生成坐标数据，请先运行:")
        print("     python rebuild_atlas.py --mode ucs")
        print("   或")
        print("     python recalculate_umap.py --mode ucs")
    
    # 4. 初始化UCSManager（用于CatID映射）
    print("\n📦 初始化UCSManager...")
    try:
        ucs_manager = UCSManager(config_dir=str(CONFIG_DIR))
        ucs_manager.load_all()
        print(f"   ✅ 已加载 {len(set(ucs_manager.catid_to_main_category.values()))} 个主类别")
    except Exception as e:
        print(f"   ⚠️  UCSManager初始化失败: {e}")
        print("   将仅使用CSV中的主类别列表")
        ucs_manager = None
    
    # 5. 如果有坐标数据，按主类别分组
    category_groups = defaultdict(list)  # {category_name: [indices]}
    uncategorized_count = 0
    
    if has_coords and ucs_manager:
        print("\n🏷️  按主类别分组数据...")
        for i, meta in enumerate(metadata):
            cat_id = meta.get('category', '') if isinstance(meta, dict) else getattr(meta, 'category', '')
            
            if not cat_id or cat_id == 'UNCATEGORIZED':
                uncategorized_count += 1
                continue
            
            main_category = ucs_manager.get_main_category_by_id(cat_id)
            if main_category and main_category != 'UNCATEGORIZED':
                category_groups[main_category.upper()].append(i)
            else:
                uncategorized_count += 1
        
        print(f"   分组完成: {len(category_groups)} 个类别有数据, {uncategorized_count} 个未分类")
    
    # 6. 为所有主类别生成配置（确保82个都包含）
    print("\n📊 提取质心和半径...")
    coordinates_config = {}
    
    # 统计信息
    categories_with_data = 0
    categories_without_data = 0
    
    # 首先处理有数据的类别
    for category in sorted(all_main_categories):
        if category in category_groups and len(category_groups[category]) > 0:
            # 有数据的类别：从坐标中提取质心
            indices = category_groups[category]
            category_coords = coords[indices]
            
            # 使用Median提取质心
            center_x, center_y = extract_centroids_median(category_coords)
            
            # 使用Robust方法计算半径（已剔除离群点）
            radius = calculate_radius_robust(category_coords, center_x, center_y)
            
            # 【gap_buffer 策略优化】
            # gap_buffer 的作用：防止子类贴边，留出缓冲空间
            # 比例策略（根据 radius 大小自适应）：
            #   - 小 radius (< 50): 15% (更紧凑)
            #   - 中 radius (50-200): 12% (平衡)
            #   - 大 radius (> 200): 10% (避免过度浪费空间)
            if radius < 50:
                gap_buffer_ratio = 0.15
            elif radius < 200:
                gap_buffer_ratio = 0.12
            else:
                gap_buffer_ratio = 0.10  # 大类别降低比例，节省空间
            
            gap_buffer = radius * gap_buffer_ratio
            
            coordinates_config[category] = {
                "x": float(center_x),
                "y": float(center_y),
                "radius": float(radius),
                "gap_buffer": float(gap_buffer),
                "description": f"{category} 大类",
                "count": len(indices),  # 记录数据点数量（便于调试）
                "has_data": True
            }
            
            print(f"   {category:20s} | 中心: ({center_x:7.2f}, {center_y:7.2f}) | "
                  f"半径: {radius:6.2f} | 点数: {len(indices):5d} ✅")
            categories_with_data += 1
        else:
            # 无数据的类别：使用默认坐标（将在后续布局中调整）
            # 默认坐标使用简单的网格排列，后续可手动调整
            coordinates_config[category] = {
                "x": 0.0,  # 默认值，需要手动调整
                "y": 0.0,  # 默认值，需要手动调整
                "radius": 15.0,  # 默认半径
                "gap_buffer": 2.25,  # radius * 0.15
                "description": f"{category} 大类（无数据，需手动调整坐标）",
                "count": 0,
                "has_data": False
            }
            
            print(f"   {category:20s} | 中心: (  0.00,   0.00) | "
                  f"半径:  15.00 | 点数:     0 ⚠️  无数据")
            categories_without_data += 1
    
    print(f"\n   统计: {categories_with_data} 个类别有数据, {categories_without_data} 个类别无数据（使用默认值）")
    
    # 7. 保存JSON文件
    print(f"\n💾 保存配置到: {OUTPUT_PATH}")
    CONFIG_DIR.mkdir(exist_ok=True)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(coordinates_config, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ 已保存 {len(coordinates_config)} 个类别的坐标配置")
    print(f"\n📝 下一步:")
    if categories_without_data > 0:
        print(f"   ⚠️  有 {categories_without_data} 个类别没有数据，使用了默认坐标(0,0)")
        print(f"   1. 检查 {OUTPUT_PATH}，手动调整无数据类别的坐标")
    else:
        print(f"   1. 检查并微调 {OUTPUT_PATH} 中的坐标")
    print(f"   2. 使用 tools/plot_ucs_layout.py 可视化布局")
    print(f"   3. 运行 python rebuild_atlas.py --mode ucs 生成UCS坐标")


if __name__ == "__main__":
    try:
        extract_category_centroids()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
