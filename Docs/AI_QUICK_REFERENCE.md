# Sonic Compass - AI快速参考文档

**版本**: v3.0  
**最后更新**: 2025-01-10  
**目的**: 为AI助手提供项目快速理解和问题定位指南

---

## 🎯 项目核心概念（30秒理解）

**Sonic Compass**: 音频资产管理工具，类似"Google Earth for Audio"

**核心理念**: 从宏观语义宇宙（UCS分类地图）到微观资产管理（文件预览）的无缝流转

**关键特征**:
- 支持200万+音频资产索引
- 4种模式：UCS模式、Gravity模式、Preset模式、Library模式
- 基于UMAP降维的可视化地图
- **定锚群岛策略（Fixed Archipelago Strategy）**: UCS模式使用固定坐标+局部UMAP，彻底解决"大陆漂移"问题

---

## 📁 关键文件位置速查

### 配置文件（参数调优）
- **`core/umap_config.py`** ⭐ - **UMAP参数统一配置**（所有参数在这里！）
  - `UCS_LOCAL_N_NEIGHBORS_SMALL`: UCS模式小类别邻居数（当前5）
  - `UCS_LOCAL_N_NEIGHBORS_LARGE`: UCS模式大类别邻居数（当前30）
  - `UCS_LOCAL_MIN_DIST`: UCS模式局部UMAP最小距离（当前0.05）
  - `GRAVITY_N_NEIGHBORS`: Gravity模式邻居数量（当前15）
  - **修改此文件即可调整所有脚本的参数**

### 核心模块
- **`core/layout_engine.py`** ⭐ - **布局引擎**（定锚群岛策略实现）
  - `compute_ucs_layout()`: UCS模式布局计算（固定坐标+局部UMAP）
  - `compute_gravity_layout()`: Gravity模式布局计算（全局无监督UMAP）
- **`core/data_processor.py`** - 数据处理、缓存、分类逻辑
- **`core/vector_engine.py`** - BGE-M3向量化引擎
- **`core/ucs_manager.py`** - UCS分类系统管理
- **`core/search_core.py`** - 搜索核心逻辑
- **`core/category_color_mapper.py`** - 类别颜色映射

### 主要脚本
- **`recalculate_umap.py`** - 重新计算UMAP坐标（支持 `--mode ucs/gravity/both`）
- **`rebuild_atlas.py`** - 完整重建地图（向量化+UMAP）
- **`tools/extract_category_centroids.py`** ⭐ - **生成UCS坐标配置**（从现有数据提取82个大类坐标）
- **`tools/verify_subset.py`** - 验证工具（生成可视化图和CSV，支持 `--mode ucs/gravity`）

### 配置文件
- **`data_config/ucs_coordinates.json`** ⭐ - **UCS坐标配置**（82个大类的固定坐标、半径、gap_buffer）

### UI代码
- **`ui/main_window.py`** - 主窗口（包含3个UMAP计算位置）

### 数据源
- **`data/soundminer_importer.py`** - Soundminer数据库导入
- **`data_config/user_config.json`** - 用户配置（数据库路径）
- **`data_config/presets.json`** - 预设分类规则

### 文档
- **`Docs/FRS`** - 功能需求规格说明书（产品功能预期）
- **`Docs/Phase3_Progress_Status.md`** - 项目进度状态
- **`Docs/SUPER_ANCHOR_STRATEGY.md`** - 超级锚点策略详细说明
- **`Docs/WEIGHT_TUNING_GUIDE.md`** - 权重调优指南

---

## 🔍 常见问题快速定位

### Q1: UMAP参数在哪里修改？
**答案**: `core/umap_config.py` - 单一配置源，修改后所有脚本自动生效

### Q2: "大陆漂移"问题（子类离开大类范围）如何解决？
**相关文件**:
- `core/layout_engine.py` - 定锚群岛策略实现（`compute_ucs_layout()`）
- `data_config/ucs_coordinates.json` - UCS坐标配置文件
- `tools/extract_category_centroids.py` - 生成坐标配置脚本

**解决方案**: 使用**定锚群岛策略**（Fixed Archipelago Strategy）
- UCS模式使用固定坐标配置文件（`ucs_coordinates.json`）
- 每个大类独立运行局部UMAP，确保0%漂移
- 如果大类半径设置不合适，运行 `tools/extract_category_centroids.py` 重新生成配置

### Q3: 参数修改后需要改哪些文件？
**答案**: 只需修改`core/umap_config.py`！所有脚本（`recalculate_umap.py`, `rebuild_atlas.py`, `tools/verify_subset.py`, `ui/main_window.py`）都从此文件读取参数。

### Q4: UCS坐标配置文件如何生成？
**答案**: 使用 `tools/extract_category_centroids.py`：
- 从现有 `coordinates_ucs.npy` 或 `coordinates.npy` 提取82个大类的质心
- 使用中位数（Median）计算质心，避免离群点影响
- 使用1.5×IQR过滤离群点，2%-98%分位数范围计算半径
- 生成 `data_config/ucs_coordinates.json` 初稿，可手动微调

### Q5: 如何验证参数修改效果？
**步骤**:
1. 修改`core/umap_config.py`中的参数
2. 运行`python tools/verify_subset.py --all --limit 1000`
3. 查看生成的`verify_output/verify_ALL_details_*.csv`
4. 使用`python tools/compare_umap_params.py <旧CSV> <新CSV>`对比

### Q6: UCS模式地图如何生成？
**相关文件**:
- `recalculate_umap.py --mode ucs` - 使用现有向量缓存重算坐标
- `rebuild_atlas.py` - 完整重建（包含向量化）
- `core/layout_engine.py` - `compute_ucs_layout()`函数

**流程**:
1. 确保存在 `data_config/ucs_coordinates.json`（如不存在，运行 `tools/extract_category_centroids.py`）
2. 加载向量和元数据
3. 按主类别分组数据
4. 对每个大类单独运行局部UMAP（使用 `UCS_LOCAL_N_NEIGHBORS_*` 和 `UCS_LOCAL_MIN_DIST`）
5. 将局部坐标归一化并平移到固定中心
6. 保存到 `cache/coordinates_ucs.npy`

**关键点**: UCS模式**不再使用向量注入**，而是使用固定坐标+局部UMAP

### Q7: UCS模式和Gravity模式的区别？
**答案**: 
- **UCS模式**: 使用定锚群岛策略，固定坐标+局部UMAP，确保0%漂移
  - 坐标文件: `cache/coordinates_ucs.npy`
  - 配置文件: `data_config/ucs_coordinates.json`
  - 每个大类独立计算，互不影响
- **Gravity模式**: 纯无监督全局UMAP，基于声学特征相似度
  - 坐标文件: `cache/coordinates_gravity.npy`
  - 使用全局UMAP，可以发现跨类别相似性

### Q8: Gravity模式的实现位置？
**答案**: 
- UI逻辑: `ui/main_window.py` - 模式切换和视图渲染
- UMAP计算: `core/layout_engine.py` - `compute_gravity_layout()`函数（纯无监督全局UMAP）
- 搜索逻辑: `core/search_core.py` - AI语义搜索

### Q9: Dynamic Axes功能如何实现？
**答案**: 目前是规划阶段，技术可行性：
- 方案A: 使用PCA/因子分析提取概念维度（如"Organic"），投影到UMAP空间
- 方案B: 重新计算UMAP（但性能开销大）
- 位置: 需要在Gravity模式下实现（UCS模式不可用）

### Q10: 文件数据结构和缓存位置？
**数据流**:
1. `data/soundminer_importer.py` - 从SQLite数据库读取
2. `core/data_processor.py` - 处理和缓存向量
3. `cache/` - 向量缓存目录（`*.npy`文件）
4. **坐标文件**:
   - `cache/coordinates_ucs.npy` - UCS模式坐标（定锚群岛策略）
   - `cache/coordinates_gravity.npy` - Gravity模式坐标（全局UMAP）
5. `data_config/ucs_coordinates.json` - UCS坐标配置（82个大类的固定坐标）

---

## 🏗️ 技术架构速览

### 数据流（双模式架构）

**UCS模式流程**:
```
Soundminer数据库 (SQLite)
    ↓
SoundminerImporter (导入)
    ↓
DataProcessor (向量化 + 分类 + 缓存)
    ↓
按主类别分组
    ↓
对每个大类运行局部UMAP (core/layout_engine.py)
    ↓
归一化并平移到固定坐标 (ucs_coordinates.json)
    ↓
坐标存储 (coordinates_ucs.npy)
    ↓
UI渲染 (QPainter + Hexbin)
```

**Gravity模式流程**:
```
Soundminer数据库 (SQLite)
    ↓
SoundminerImporter (导入)
    ↓
DataProcessor (向量化 + 缓存)
    ↓
全局无监督UMAP (core/layout_engine.py)
    ↓
归一化到 0-3000 范围
    ↓
坐标存储 (coordinates_gravity.npy)
    ↓
UI渲染 (QPainter + Hexbin)
```

### 关键算法

**定锚群岛策略**（Fixed Archipelago Strategy）:
```python
# 位置: core/layout_engine.py
# 函数: compute_ucs_layout()
# 作用: UCS模式布局计算（固定坐标+局部UMAP）
# 关键:
#   - 使用固定坐标配置文件 (ucs_coordinates.json)
#   - 每个大类独立运行局部UMAP
#   - 确保0%漂移（大类位置固定）
```

**参数配置系统**:
```python
# 位置: core/umap_config.py
# 函数: get_umap_params()
# 作用: 统一参数管理，避免硬编码
# UCS模式参数:
#   - UCS_LOCAL_N_NEIGHBORS_SMALL = 5
#   - UCS_LOCAL_N_NEIGHBORS_LARGE = 30
#   - UCS_LOCAL_MIN_DIST = 0.05
```

### 模式区分

| 模式 | UMAP类型 | 坐标文件 | 坐标配置 | 搜索方式 |
|------|---------|---------|---------|---------|
| **UCS模式** | 局部UMAP（每大类独立） | `coordinates_ucs.npy` | `ucs_coordinates.json` | 传统metadata搜索 |
| **Gravity模式** | 全局无监督UMAP | `coordinates_gravity.npy` | ❌ 无 | AI语义搜索 |
| **Preset模式** | 混合 | 依赖UCS/Gravity | 基于预设关键词 | AI语义搜索 |
| **Library模式** | ❌ 不使用UMAP | ❌ | ❌ | 文件路径搜索 |

---

## 🐛 常见Bug定位

### Bug: "大陆漂移"（子类分离）- 已解决
**症状**: 同一大类的子类分布在不同的"大陆"区域  
**定位**: 使用定锚群岛策略后，此问题已彻底解决  
**修复**: UCS模式使用固定坐标+局部UMAP，确保大类位置固定
- 如果仍有问题，检查 `data_config/ucs_coordinates.json` 中的 `radius` 设置
- 运行 `tools/extract_category_centroids.py` 重新生成配置

### Bug: 点过度重叠
**症状**: 可视化图中所有点挤在一起  
**定位**: `core/umap_config.py` - `MIN_DIST`太小  
**修复**: 增大`MIN_DIST`（当前0.1，可尝试0.2-0.3）

### Bug: UMAP计算不一致
**症状**: 离线脚本和UI计算结果不同  
**定位**: 检查是否都使用了`core/umap_config.py`  
**修复**: 确保所有脚本从统一配置读取参数

### Bug: UCS坐标配置文件缺失
**症状**: `FileNotFoundError: UCS坐标配置文件不存在`  
**定位**: `data_config/ucs_coordinates.json` 不存在  
**修复**: 运行 `python tools/extract_category_centroids.py` 生成配置

### Bug: UCS模式计算失败
**症状**: `compute_ucs_layout()` 报错或大类数据分散  
**定位**: 
- `ucs_coordinates.json` 中的 `radius` 设置不合适
- 局部UMAP参数需要调整  
**修复**: 
- 运行 `tools/extract_category_centroids.py` 重新生成配置
- 调整 `core/umap_config.py` 中的 `UCS_LOCAL_MIN_DIST` 等参数

---

## 📊 关键参数速查表

| 参数 | 位置 | 当前值 | 作用 | 调优方向 |
|------|------|--------|------|---------|
| `UCS_LOCAL_N_NEIGHBORS_SMALL` | `core/umap_config.py` | 5 | UCS模式小类别邻居数 | ↓ 减小更多细节，↑ 提升更稳定 |
| `UCS_LOCAL_N_NEIGHBORS_LARGE` | `core/umap_config.py` | 30 | UCS模式大类别邻居数 | ↓ 减小更多细节，↑ 提升更稳定 |
| `UCS_LOCAL_MIN_DIST` | `core/umap_config.py` | 0.05 | UCS模式局部UMAP最小距离 | ↑ 提升可分离点 |
| `GRAVITY_N_NEIGHBORS` | `core/umap_config.py` | 15 | Gravity模式邻居数量 | ↓ 减小更多局部细节 |
| `SPREAD` | `core/umap_config.py` | 1.0 | UMAP扩散参数 | ↑ 提升可增加分布范围 |

---

## 🔧 快速修改指南

### 场景1: UCS模式大类内部点过度紧密
```python
# 文件: core/umap_config.py
# 修改:
UCS_LOCAL_MIN_DIST = 0.1  # 从0.05提升，让点更分散
```

### 场景2: UCS模式大类半径不合适（数据超出范围）
```bash
# 运行脚本重新生成配置
python tools/extract_category_centroids.py

# 或手动编辑 data_config/ucs_coordinates.json
# 调整特定大类的 radius 值
```

### 场景3: 测试不同局部UMAP参数
```python
# 文件: core/umap_config.py
# 修改:
UCS_LOCAL_N_NEIGHBORS_LARGE = 50  # 测试值1
# 或
UCS_LOCAL_MIN_DIST = 0.02         # 测试值2（更紧密）
# 然后运行: python recalculate_umap.py --mode ucs
```

---

## 📖 详细文档索引

| 文档 | 内容 | 何时查阅 |
|------|------|---------|
| `Docs/FRS` | 产品功能规格 | 了解功能需求、LOD层级、模式定义 |
| `Docs/SUPER_ANCHOR_STRATEGY.md` | 超级锚点策略 | 理解向量注入原理 |
| `Docs/WEIGHT_TUNING_GUIDE.md` | 权重调优 | 需要调优UMAP参数时 |
| `Docs/Phase3_Progress_Status.md` | 项目进度 | 了解开发历史和当前状态 |

---

## ⚡ 快速命令参考

```bash
# 生成UCS坐标配置（首次运行UCS模式前必须）
python tools/extract_category_centroids.py

# 重新计算UCS模式坐标
python recalculate_umap.py --mode ucs

# 重新计算Gravity模式坐标
python recalculate_umap.py --mode gravity

# 同时计算两种模式
python recalculate_umap.py --mode both

# 完整重建地图（包含UCS和Gravity模式）
python rebuild_atlas.py

# 验证测试（全库，UCS模式）
python tools/verify_subset.py --all --limit 1000 --mode ucs

# 验证测试（特定类别，Gravity模式）
python tools/verify_subset.py ANIMALS --limit 500 --mode gravity

# 对比参数效果
python tools/compare_umap_params.py <旧CSV> <新CSV>

# 分析聚类效果
python tools/test_weight_progression.py <参考CSV> <测试CSV> ANIMALS
```

---

## 💡 AI助手提示

**当用户提问时，按以下顺序定位**:

1. **参数调优问题** → 查看`core/umap_config.py`
2. **功能实现问题** → 查看`Docs/FRS`了解需求
3. **Bug/错误问题** → 查看本文档的"常见Bug定位"章节
4. **架构理解问题** → 查看本文档的"技术架构速览"
5. **算法细节问题** → 查看`Docs/SUPER_ANCHOR_STRATEGY.md`

**关键原则**:
- ✅ 所有UMAP参数都在`core/umap_config.py`中
- ✅ 修改参数只需改一个文件
- ✅ UCS模式使用**定锚群岛策略**（固定坐标+局部UMAP），不再使用向量注入
- ✅ Gravity模式使用纯无监督全局UMAP
- ✅ UCS模式需要 `data_config/ucs_coordinates.json` 配置文件
- ✅ 两种模式使用不同的坐标文件（`coordinates_ucs.npy` vs `coordinates_gravity.npy`）
