# 坐标可视化功能设计文档

## 问题解答

### 1. CREATURES 分散的原因

**配置分析：**
- CREATURES: `radius=779.3`, `gap_buffer=116.9` → 实际半径 = 662.4
- ANIMALS: `radius=272.1`, `gap_buffer=40.8` → 实际半径 = 231.3

**原因：**
1. `extract_category_centroids.py` 计算 radius 时包含了离群点，导致 radius 过大
2. CREATURES 数据量大（310条），局部 UMAP 参数 `n_neighbors=30` 可能不合适
3. `gap_buffer` 相对 radius 的比例（15%）可能偏小

**解决方案：**
- 已在 `layout_engine.py` 中修复，现在使用 `UCS_LOCAL_MIN_DIST` 和 `UCS_LOCAL_N_NEIGHBORS_LARGE`
- 建议重新运行 `tools/extract_category_centroids.py` 生成更准确的 radius
- 对于CREATURES这种大数据集，可以考虑手动调整 `radius` 和 `gap_buffer`

### 2. 局部 UMAP 参数位置

**位置：** `core/umap_config.py` (第94-96行)

```python
UCS_LOCAL_N_NEIGHBORS_SMALL = 5     # 小类别（5-50个样本）
UCS_LOCAL_N_NEIGHBORS_LARGE = 30    # 大类别（>=1000个样本）
UCS_LOCAL_MIN_DIST = 0.05           # 局部UMAP参数（紧密聚类）
```

**修复：** 已在 `core/layout_engine.py` 中修复，现在正确使用这些参数。

### 3. 200w+ 数据，3000 坐标范围够用吗？

**分析：**
- 从 CSV 数据看，当前坐标范围在 -500 到 3000 左右（X/Y 轴）
- 理论范围：3000 × 3000 = 900万格子点
- 200万数据：平均每个格子点约 4.5 个数据点

**结论：**
- **基本够用**，但可能会有些重叠
- 建议：
  - 如果数据继续增长，可以考虑扩大范围到 5000×5000
  - 或者使用更精细的六边形网格

### 4. gap_buffer 的作用

**回答：** 是的，`gap_buffer` 控制大类内部的子类间距。

**公式：**
```
有效半径 = radius - gap_buffer
最终坐标 = 中心坐标 + (局部UMAP坐标 × 有效半径)
```

**含义：**
- `radius`: 大类占据的最大范围
- `gap_buffer`: 预留的缓冲间距（防止子类贴边）
- `有效半径`: 实际用于放置数据的半径

**示例：**
- CREATURES: radius=779.3, gap_buffer=116.9 → 有效半径=662.4
- 这意味着 CREATURES 内部的数据最多只能分布在 662.4 的范围内

### 5. XY 轴的具体含义

**回答：** **没有具体语义含义**，只是 UMAP 降维后的二维坐标。

**说明：**
- X/Y 轴是 UMAP 算法生成的数学坐标
- 它们只表示数据点在低维空间中的位置关系
- **类似地图的经纬度**，只是坐标系统，没有"方向"含义
- 例如：X=1000, Y=2000 不代表"向东1000米，向北2000米"，只是表示这个点在坐标空间中的位置

## 新功能需求

### 功能 1: 坐标轴显示（可开关）
- 在画布上显示 X/Y 坐标轴
- 添加开关按钮控制显示/隐藏
- 坐标轴样式：浅色、半透明、带刻度

### 功能 2: 鼠标位置坐标显示
- 实时显示鼠标位置的 X/Y 坐标
- 显示在状态栏或画布角落
- 坐标格式：(X: 1234.5, Y: 5678.9)

### 功能 3: 鼠标位置范围可视化
- 鼠标位置显示一个圆形/矩形范围指示器
- 可以用来评估大类的 radius 范围
- 可配置范围大小（例如：radius 的倍数）

## 实现计划

### 步骤 1: 添加坐标轴层
在 `ui/visualizer/sonic_universe.py` 中添加 `CoordinateAxesLayer` 类

### 步骤 2: 添加鼠标跟踪
在 `ui/components/canvas_view.py` 中添加鼠标移动事件处理

### 步骤 3: 添加范围指示器
在 `ui/visualizer/sonic_universe.py` 中添加 `RangeIndicator` 类

### 步骤 4: 添加 UI 控制
在 `ui/main_window.py` 中添加开关按钮和状态栏显示
