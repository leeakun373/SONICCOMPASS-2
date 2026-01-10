"""
UMAP 参数配置 - 统一参数管理

本模块为所有脚本（recalculate_umap.py, rebuild_atlas.py, tools/verify_subset.py, ui/main_window.py）
提供统一的 UMAP 参数配置。

优势：
- 单一数据源：所有 UMAP 参数集中在一个地方
- 易于调优：无需修改多个文件，只需修改此文件
- 避免不一致：防止遗漏更新和参数错误
- 文档清晰：参数选择有明确说明
"""

# ============================================================================
# 超级锚点策略参数
# ============================================================================

# 类别向量注入权重
AUDIO_WEIGHT = 1.0          # 音频特征权重（保持内部结构）
CATEGORY_WEIGHT = 150      # 类别锚点权重（引力强度）- 建议从75.0开始测试
                            # 值越大，按类别聚类的强制力越强
                            # 推荐范围：15.0-150.0
                            # 当前值：75.0（从50.0进一步提升，测试更强的大类聚合）
                            # 测试建议：
                            #   - 50.0: 仍有子类离开大类范围
                            #   - 75.0: 当前测试值（逐步提升）
                            #   - 100.0: 如果75.0不够，可继续提升
                            #   - 150.0: 极端值（可能导致过度紧密，失去内部结构）

# 小数据集自适应权重（用于验证/测试）
CATEGORY_WEIGHT_SMALL = 150.0  # 用于数据集 < 500 条样本（从30.0提升到50.0）
CATEGORY_WEIGHT_LARGE = 150.0  # 用于数据集 >= 500 条样本（从50.0提升到75.0，与默认值相同）

# 自适应阈值（区分小数据集和大数据集）
ADAPTIVE_THRESHOLD = 500      # 数据量阈值：< 500 为小数据集，>= 500 为大数据集

# 测试脚本特殊参数（小数据集或非监督场景）
MIN_DIST_SMALL = 0.1          # 小数据集或非监督场景的最小距离（更紧密）

# ============================================================================
# UMAP 拓扑参数
# ============================================================================

# 低维空间中点之间的最小距离
MIN_DIST = 0.1              # 范围：0.0-1.0
                            # 较小值：紧密聚类（0.0-0.1）
                            # 中等值：平衡（0.1-0.5）
                            # 较大值：更分散（0.5-1.0）
                            # 当前值：0.05（配合category_weight=75.0，防止过度重叠）
                            # 注意：category_weight越高，点越紧密，可能需要适当增大min_dist
                            # 如果发现点过度重叠，可以调整到0.1-0.2

# 扩散参数（点之间的平均距离）
SPREAD = 1.0                # 范围：0.1-3.0（通常 < 3.0）
                            # 较小值：紧凑聚类（0.3-1.0）
                            # 中等值：平衡（1.0-2.0）
                            # 较大值：更分散（2.0-3.0）
                            # 当前值：1.0（从0.5增加，以获得更好的分布）

# 邻居数量（局部结构保留）
N_NEIGHBORS = 30            # 范围：2 到 min(200, 数据量-1)
                            # 较小值：更多局部细节，更多"小岛"（5-50）
                            # 较大值：更多全局结构，更大的"大陆"（15-100）
                            # 当前值：80（保持全局结构）

# ============================================================================
# UMAP 监督学习参数
# ============================================================================

# 目标权重（监督强度）
TARGET_WEIGHT = 1         # 范围：0.0-1.0
                            # 0.0：无监督（忽略标签）
                            # 0.5：平衡（当前值，因为向量注入是主要约束）
                            # 1.0：完全监督（强制按标签聚类）
                            # 当前值：0.5（从0.95降低，因为向量注入提供主要约束）

TARGET_METRIC = 'categorical'  # 标签类型：'categorical'（离散）或 'continuous'（连续数值）

# ============================================================================
# UMAP 其他参数
# ============================================================================

N_COMPONENTS = 2            # 输出维度（2D用于可视化）
METRIC = 'cosine'           # 距离度量（'cosine'用于高维向量）
RANDOM_STATE = 42          # 随机种子（用于可复现性）
N_JOBS = 1                 # 并行任务数（1避免内存问题）
VERBOSE = True             # 显示进度信息

# ============================================================================
# UCS/Gravity 模式专用参数
# ============================================================================

# UCS模式局部UMAP参数（用于每个大类内部的局部计算）
UCS_LOCAL_N_NEIGHBORS_SMALL = 5     # 小类别（5-50个样本）
UCS_LOCAL_N_NEIGHBORS_LARGE = 30    # 大类别（>=1000个样本）
UCS_LOCAL_MIN_DIST = 0.05           # 局部UMAP参数（紧密聚类）

# Gravity模式参数（纯无监督全局UMAP）
GRAVITY_N_NEIGHBORS = 15            # Gravity模式邻居数量（更关注局部结构）

# ============================================================================
# 自适应配置辅助函数
# ============================================================================

def get_category_weight(data_size: int, use_adaptive: bool = False) -> float:
    """
    根据数据量获取类别权重（用于自适应场景）
    
    参数:
        data_size: 数据集中的样本数量（可选）
        use_adaptive: 是否使用自适应权重（小数据集 vs 大数据集）
    
    返回:
        要使用的类别权重
    """
    if use_adaptive and data_size is not None:
        return CATEGORY_WEIGHT_SMALL if data_size < ADAPTIVE_THRESHOLD else CATEGORY_WEIGHT_LARGE
    else:
        return CATEGORY_WEIGHT


def get_umap_params(data_size: int = None, use_adaptive: bool = False, is_supervised: bool = True) -> dict:
    """
    获取完整的 UMAP 参数字典
    
    参数:
        data_size: 可选的数据量（用于自适应参数）
        use_adaptive: 是否使用自适应类别权重
        is_supervised: 是否为监督学习（False时移除监督参数）
    
    返回:
        可直接传递给 umap.UMAP() 的参数字典
    """
    # 根据场景选择 min_dist
    if use_adaptive and data_size is not None and (not is_supervised or data_size <= 50):
        min_dist = MIN_DIST_SMALL  # 小数据集或非监督场景使用更小的 min_dist
    else:
        min_dist = MIN_DIST  # 默认值
    
    params = {
        'n_components': N_COMPONENTS,
        'n_neighbors': N_NEIGHBORS,
        'min_dist': min_dist,
        'spread': SPREAD,
        'metric': METRIC,
        'random_state': RANDOM_STATE,
        'n_jobs': N_JOBS,
        'verbose': VERBOSE
    }
    
    # 只有在监督学习时才添加监督参数
    if is_supervised:
        params['target_weight'] = TARGET_WEIGHT
        params['target_metric'] = TARGET_METRIC
    else:
        params['target_weight'] = None
        params['target_metric'] = None
    
    return params


def get_injection_params(data_size: int = None, use_adaptive: bool = False) -> dict:
    """
    获取向量注入参数
    
    参数:
        data_size: 可选的数据量（用于自适应参数）
        use_adaptive: 是否使用自适应类别权重
    
    返回:
        包含 audio_weight 和 category_weight 的字典
    """
    return {
        'audio_weight': AUDIO_WEIGHT,
        'category_weight': get_category_weight(data_size, use_adaptive)
    }
