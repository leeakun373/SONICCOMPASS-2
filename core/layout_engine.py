"""
布局引擎 - 定锚群岛策略 (Fixed Archipelago Strategy)

实施硬规则布局 + 局部UMAP计算，彻底解决UCS模式下的"大陆漂移"问题。

核心功能:
- compute_ucs_layout: UCS模式布局计算（硬规则 + 局部UMAP）
- compute_gravity_layout: Gravity模式布局计算（纯无监督全局UMAP）
- load_ucs_coordinates_config: 加载UCS坐标配置文件
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    print("[WARNING] umap-learn not available, layout_engine will not work")

from . import umap_config


def load_ucs_coordinates_config(config_path: str = "data_config/ucs_coordinates.json") -> Dict[str, Dict[str, Any]]:
    """
    加载UCS坐标配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        字典：{category_name: {x, y, radius, gap_buffer, ...}}
        
    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"UCS坐标配置文件不存在: {config_path}\n"
                              f"请先运行: python tools/extract_category_centroids.py")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 验证必需的字段
    for category, settings in config.items():
        if 'x' not in settings or 'y' not in settings or 'radius' not in settings:
            raise ValueError(f"类别 {category} 缺少必需字段 (x, y, radius)")
        # 如果没有gap_buffer，使用默认值（radius * 0.15）
        if 'gap_buffer' not in settings:
            settings['gap_buffer'] = settings['radius'] * 0.15
    
    return config


def normalize_local_coords(coords: np.ndarray) -> np.ndarray:
    """
    使用Robust Scaler将局部UMAP坐标归一化到 [-1, 1] 范围
    
    算法:
    1. 计算2%和98%分位数作为边界
    2. 归一化到 [-1, 1]
    3. Clip超出范围的点
    
    优势: 防止离群点将99%正常点压缩到中心微小区域
    
    Args:
        coords: 局部UMAP坐标 (N, 2)
        
    Returns:
        归一化后的坐标 (N, 2)，范围在 [-1, 1]
    """
    if len(coords) == 0:
        return coords
    
    coords = np.array(coords, dtype=np.float32)
    
    # 计算2%和98%分位数
    p2_x, p98_x = np.percentile(coords[:, 0], [2, 98])
    p2_y, p98_y = np.percentile(coords[:, 1], [2, 98])
    
    # 归一化每列
    normalized = np.zeros_like(coords)
    
    # X轴归一化
    if p98_x > p2_x:
        normalized[:, 0] = (coords[:, 0] - p2_x) / (p98_x - p2_x) * 2 - 1
    else:
        normalized[:, 0] = 0.0
    
    # Y轴归一化
    if p98_y > p2_y:
        normalized[:, 1] = (coords[:, 1] - p2_y) / (p98_y - p2_y) * 2 - 1
    else:
        normalized[:, 1] = 0.0
    
    # Clip到 [-1, 1]
    normalized = np.clip(normalized, -1, 1)
    
    return normalized


def place_local_coords(local_coords: np.ndarray, center_x: float, center_y: float, 
                       radius: float, gap_buffer: float = 0.0) -> np.ndarray:
    """
    将归一化的局部坐标缩放和平移到预设中心
    
    公式: Final = Global_Center + (Local_UMAP * (radius - gap_buffer))
    
    Args:
        local_coords: 归一化后的局部坐标 (N, 2)，范围 [-1, 1]
        center_x: 预设中心X坐标
        center_y: 预设中心Y坐标
        radius: 半径
        gap_buffer: 缓冲间距（从radius中扣除）
        
    Returns:
        最终的全局坐标 (N, 2)
    """
    # 计算实际使用的半径（减去gap_buffer）
    effective_radius = radius - gap_buffer
    
    # 缩放并平移
    final_coords = np.zeros_like(local_coords)
    final_coords[:, 0] = center_x + local_coords[:, 0] * effective_radius
    final_coords[:, 1] = center_y + local_coords[:, 1] * effective_radius
    
    return final_coords


def _compute_local_umap_small(n_vectors: int, embeddings: np.ndarray) -> Optional[np.ndarray]:
    """
    处理极小样本的局部UMAP计算
    
    Args:
        n_vectors: 向量数量
        embeddings: 嵌入向量 (N, dim)
        
    Returns:
        坐标数组 (N, 2) 或 None（如果无法计算）
    """
    if n_vectors == 1:
        # 单点：使用中心坐标
        return np.array([[0.0, 0.0]], dtype=np.float32)
    elif n_vectors == 2:
        # 两点：微小偏移
        return np.array([[-0.1, 0.0], [0.1, 0.0]], dtype=np.float32)
    elif n_vectors == 3:
        # 三点：正三角形
        angle = 2 * np.pi / 3
        return np.array([
            [0.0, 0.2],
            [0.173, -0.1],
            [-0.173, -0.1]
        ], dtype=np.float32)
    elif n_vectors == 4:
        # 四点：正方形
        return np.array([
            [-0.1, -0.1],
            [0.1, -0.1],
            [0.1, 0.1],
            [-0.1, 0.1]
        ], dtype=np.float32)
    else:
        return None


def compute_ucs_layout(
    metadata: List[Dict],
    embeddings: np.ndarray,
    ucs_manager,
    config_path: str = "data_config/ucs_coordinates.json",
    use_parallel: bool = True
) -> Tuple[np.ndarray, Dict[str, List[int]]]:
    """
    计算UCS模式布局（定锚群岛策略）
    
    关键点:
    - 禁用向量注入（数据已经是纯净的单一类别）
    - 对每个大类单独运行局部UMAP
    - 使用Robust Scaler归一化
    - 平移到预设中心
    
    Args:
        metadata: 元数据列表
        embeddings: 嵌入向量矩阵 (N, dim)
        ucs_manager: UCSManager实例
        config_path: UCS坐标配置文件路径
        use_parallel: 是否使用并行计算（默认True）
        
    Returns:
        (coordinates_ucs, category_indices)
        - coordinates_ucs: 最终坐标 (N, 2)
        - category_indices: {category_name: [indices]}
    """
    if not UMAP_AVAILABLE:
        raise RuntimeError("umap-learn is required for compute_ucs_layout")
    
    # 1. 加载UCS坐标配置
    print("\n📋 加载UCS坐标配置...")
    coordinates_config = load_ucs_coordinates_config(config_path)
    print(f"   已加载 {len(coordinates_config)} 个大类的坐标配置")
    
    # 2. 按主类别分组数据
    print("\n🏷️  按主类别分组数据...")
    category_groups = defaultdict(list)  # {category_name: [indices]}
    uncategorized_indices = []
    
    for i, meta in enumerate(metadata):
        # 获取CatID
        cat_id = meta.get('category', '') if isinstance(meta, dict) else getattr(meta, 'category', '')
        
        if not cat_id or cat_id == 'UNCATEGORIZED':
            uncategorized_indices.append(i)
            continue
        
        # 获取主类别名称
        if ucs_manager:
            main_category = ucs_manager.get_main_category_by_id(cat_id)
            if main_category and main_category != 'UNCATEGORIZED':
                category_groups[main_category.upper()].append(i)
            else:
                uncategorized_indices.append(i)
        else:
            uncategorized_indices.append(i)
    
    print(f"   分组完成: {len(category_groups)} 个类别, {len(uncategorized_indices)} 个未分类")
    
    # 3. 对每个大类单独运行局部UMAP
    print("\n🚀 开始局部UMAP计算...")
    
    # 初始化最终坐标数组
    final_coords = np.zeros((len(metadata), 2), dtype=np.float32)
    
    # 顺序执行（当前实现）
    # 注意：并行化需要序列化embeddings和metadata，开销较大
    # 后续可以优化为真正的并行（使用多进程）
    results = []
    for category, indices in sorted(category_groups.items()):
        if category not in coordinates_config:
            print(f"   [WARNING] 类别 {category} 不在配置文件中，跳过")
            continue
        
        cat_embeddings = embeddings[indices]
        config = coordinates_config[category]
        
        print(f"   计算 {category}: {len(indices)} 个点...", end='', flush=True)
        result = _compute_category_layout(
            category, indices, cat_embeddings, config, ucs_manager
        )
        results.append(result)
        print(" ✅")
    
    # 4. 合并所有类别的坐标
    print("\n🔗 合并坐标...")
    for category, indices, coords in results:
        final_coords[indices] = coords
        print(f"   {category}: {len(indices)} 个点")
    
    # 5. 处理未分类数据（放置到中心或最近类别）
    if len(uncategorized_indices) > 0:
        print(f"\n⚠️  处理 {len(uncategorized_indices)} 个未分类数据点...")
        # 简单处理：放在原点附近
        for idx in uncategorized_indices:
            final_coords[idx] = [0.0, 0.0]
    
    # 6. 碰撞检测
    check_category_overlaps(coordinates_config)
    
    return final_coords, dict(category_groups)


def _compute_category_layout(
    category: str,
    indices: List[int],
    embeddings: np.ndarray,
    config: Dict[str, Any],
    ucs_manager
) -> Tuple[str, List[int], np.ndarray]:
    """
    计算单个类别的局部布局
    
    Args:
        category: 类别名称
        indices: 该类别的索引列表
        embeddings: 该类别的嵌入向量 (N, dim)
        config: 该类别的配置 {x, y, radius, gap_buffer, ...}
        ucs_manager: UCSManager实例（未使用，保留接口一致性）
        
    Returns:
        (category, indices, coords) - 类别名、索引列表、坐标数组
    """
    n_vectors = len(embeddings)
    center_x = config['x']
    center_y = config['y']
    radius = config['radius']
    gap_buffer = config.get('gap_buffer', radius * 0.15)
    
    # 极小样本特殊处理
    if n_vectors < 5:
        local_coords = _compute_local_umap_small(n_vectors, embeddings)
        if local_coords is not None:
            final_coords = place_local_coords(local_coords, center_x, center_y, radius, gap_buffer)
            return (category, indices, final_coords)
    
    # 计算局部UMAP参数（使用UCS专用参数）
    if 5 <= n_vectors < 50:
        n_neighbors = min(n_vectors - 1, umap_config.UCS_LOCAL_N_NEIGHBORS_SMALL)
    elif 50 <= n_vectors < 1000:
        n_neighbors = 15  # 中等类别使用固定值
    else:
        n_neighbors = umap_config.UCS_LOCAL_N_NEIGHBORS_LARGE  # 大类别使用专用参数
    
    # 运行局部UMAP（关键：不使用向量注入，使用UCS专用min_dist）
    if UMAP_AVAILABLE:
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            min_dist=umap_config.UCS_LOCAL_MIN_DIST,  # 使用UCS专用min_dist
            spread=umap_config.SPREAD,
            metric=umap_config.METRIC,
            random_state=umap_config.RANDOM_STATE,
            n_jobs=1,  # 局部UMAP使用单进程
            verbose=False  # 避免输出过多
        )
        
        local_coords = reducer.fit_transform(embeddings)
    else:
        # 如果UMAP不可用，使用PCA降维
        from sklearn.decomposition import PCA
        pca = PCA(n_components=2, random_state=42)
        local_coords = pca.fit_transform(embeddings)
    
    # 归一化（Robust Scaler）
    normalized_coords = normalize_local_coords(local_coords)
    
    # 放置到预设中心
    final_coords = place_local_coords(normalized_coords, center_x, center_y, radius, gap_buffer)
    
    return (category, indices, final_coords)


def compute_gravity_layout(
    metadata: List[Dict],
    embeddings: np.ndarray
) -> np.ndarray:
    """
    计算Gravity模式布局（纯无监督全局UMAP）
    
    关键点:
    - 不使用向量注入
    - 不使用监督学习参数
    - 保持原有的Gravity模式计算逻辑
    
    Args:
        metadata: 元数据列表（未使用，保留接口一致性）
        embeddings: 嵌入向量矩阵 (N, dim)
        
    Returns:
        coordinates_gravity: 全局坐标 (N, 2)
    """
    if not UMAP_AVAILABLE:
        raise RuntimeError("umap-learn is required for compute_gravity_layout")
    
    print("\n🌌 计算Gravity模式布局（纯无监督全局UMAP）...")
    
    # 获取Gravity模式参数
    params = umap_config.get_umap_params(is_supervised=False)
    params['n_neighbors'] = getattr(umap_config, 'GRAVITY_N_NEIGHBORS', 15)
    
    # 运行纯无监督全局UMAP
    reducer = umap.UMAP(**params)
    coords_2d = reducer.fit_transform(embeddings)
    
    # 【归一化】将Gravity模式的坐标归一化到 0-3000 范围（与UCS模式保持一致）
    # 这样可以确保两种模式的坐标范围一致，便于UI切换
    if len(coords_2d) > 0:
        min_coords = np.min(coords_2d, axis=0)
        max_coords = np.max(coords_2d, axis=0)
        coord_range = max_coords - min_coords
        max_range = np.max(coord_range) if np.max(coord_range) > 0 else 1.0
        
        # 归一化到 0-3000 范围
        scale = 3000.0 / max_range
        coords_2d = (coords_2d - min_coords) * scale
        
        print(f"   ✅ Gravity布局计算完成: {coords_2d.shape}")
        print(f"   📊 坐标范围: X=[{coords_2d[:, 0].min():.1f}, {coords_2d[:, 0].max():.1f}], "
              f"Y=[{coords_2d[:, 1].min():.1f}, {coords_2d[:, 1].max():.1f}]")
    else:
        print(f"   ⚠️  警告: 没有数据点，返回空坐标")
    
    return coords_2d


def check_category_overlaps(coordinates_config: Dict[str, Dict[str, Any]]) -> None:
    """
    检查类别是否重叠（碰撞检测）
    
    Args:
        coordinates_config: UCS坐标配置字典
    """
    print("\n🔍 执行碰撞检测...")
    overlaps = []
    
    categories = list(coordinates_config.keys())
    for i, cat1 in enumerate(categories):
        config1 = coordinates_config[cat1]
        for j, cat2 in enumerate(categories):
            if i >= j:  # 避免重复检查
                continue
            
            config2 = coordinates_config[cat2]
            
            # 计算两个圆心的距离
            dist = np.sqrt((config1['x'] - config2['x'])**2 + 
                          (config1['y'] - config2['y'])**2)
            
            # 计算重叠半径（考虑gap_buffer）
            overlap_radius = config1['radius'] + config2['radius'] + \
                           config1.get('gap_buffer', 0) + \
                           config2.get('gap_buffer', 0)
            
            if dist < overlap_radius:
                overlaps.append((cat1, cat2, dist, overlap_radius))
                print(f"   [WARNING] 类别重叠: {cat1} 与 {cat2} "
                      f"(距离={dist:.2f}, 重叠半径={overlap_radius:.2f})")
    
    if not overlaps:
        print("   ✅ 未发现类别重叠")
    else:
        print(f"   ⚠️  发现 {len(overlaps)} 组重叠，请调整坐标配置")
