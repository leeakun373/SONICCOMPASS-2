# Sonic Compass - AI快速参考文档

**版本**: v2.0  
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
- 超级锚点策略：强制同一大类数据聚集（解决"大陆漂移"问题）

---

## 📁 关键文件位置速查

### 配置文件（参数调优）
- **`core/umap_config.py`** ⭐ - **UMAP参数统一配置**（所有参数在这里！）
  - `CATEGORY_WEIGHT`: 类别锚点权重（当前150.0）
  - `MIN_DIST`: 最小距离（当前0.1）
  - `N_NEIGHBORS`: 邻居数量（当前30）
  - **修改此文件即可调整所有脚本的参数**

### 核心模块
- **`core/data_processor.py`** - 数据处理、缓存、`inject_category_vectors()`函数
- **`core/vector_engine.py`** - BGE-M3向量化引擎
- **`core/ucs_manager.py`** - UCS分类系统管理
- **`core/search_core.py`** - 搜索核心逻辑
- **`core/category_color_mapper.py`** - 类别颜色映射

### 主要脚本
- **`recalculate_umap.py`** - 重新计算UMAP坐标（离线脚本）
- **`rebuild_atlas.py`** - 完整重建地图（向量化+UMAP）
- **`tools/verify_subset.py`** - 验证工具（生成可视化图和CSV）

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
- `core/umap_config.py` - 调整`CATEGORY_WEIGHT`（当前150.0，可提升到200+）
- `core/data_processor.py` - `inject_category_vectors()`函数实现
- `Docs/SUPER_ANCHOR_STRATEGY.md` - 策略说明

**解决方案**: 提升`CATEGORY_WEIGHT`（50.0→75.0→100.0→150.0...）

### Q3: 参数修改后需要改哪些文件？
**答案**: 只需修改`core/umap_config.py`！所有脚本（`recalculate_umap.py`, `rebuild_atlas.py`, `tools/verify_subset.py`, `ui/main_window.py`）都从此文件读取参数。

### Q4: 测试脚本的权重为什么不一样？
**答案**: 测试脚本使用自适应权重（`use_adaptive=True`）：
- 小数据集（<500）: `CATEGORY_WEIGHT_SMALL`
- 大数据集（>=500）: `CATEGORY_WEIGHT_LARGE`
- 配置在`core/umap_config.py`中统一管理

### Q5: 如何验证参数修改效果？
**步骤**:
1. 修改`core/umap_config.py`中的参数
2. 运行`python tools/verify_subset.py --all --limit 1000`
3. 查看生成的`verify_output/verify_ALL_details_*.csv`
4. 使用`python tools/compare_umap_params.py <旧CSV> <新CSV>`对比

### Q6: UCS模式地图如何生成？
**相关文件**:
- `recalculate_umap.py` - 使用现有向量缓存重算坐标
- `rebuild_atlas.py` - 完整重建（包含向量化）
- 都使用`inject_category_vectors()`注入类别向量

**参数**:
- `category_weight=150.0`（强制大类聚合）
- `min_dist=0.1`（防止过度重叠）
- `target_weight=1.0`（监督学习权重，影响较小）

### Q7: target_weight参数是否有影响？
**答案**: 在`category_weight=150.0`的情况下，`target_weight`的影响几乎为零（已验证：0.5 vs 1.0 结果完全相同）。向量注入是主导因素。

### Q8: Gravity模式的实现位置？
**答案**: 
- UI逻辑: `ui/main_window.py` - 模式切换和视图渲染
- UMAP计算: 需要禁用向量注入（`category_weight=0`或不调用`inject_category_vectors`）
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
4. `coordinates.npy` - UMAP坐标缓存

---

## 🏗️ 技术架构速览

### 数据流
```
Soundminer数据库 (SQLite)
    ↓
SoundminerImporter (导入)
    ↓
DataProcessor (向量化 + 缓存)
    ↓
inject_category_vectors() (向量注入 - UCS模式)
    ↓
UMAP降维 (监督学习)
    ↓
坐标存储 (coordinates.npy)
    ↓
UI渲染 (QPainter + Hexbin)
```

### 关键算法

**超级锚点策略**（Super-Anchor Strategy）:
```python
# 位置: core/data_processor.py
# 函数: inject_category_vectors()
# 作用: 将主类别的One-Hot向量注入到音频embedding
# 权重: category_weight=150.0 (50倍音频权重)
```

**参数配置系统**:
```python
# 位置: core/umap_config.py
# 函数: get_umap_params(), get_injection_params()
# 作用: 统一参数管理，避免硬编码
```

### 模式区分

| 模式 | UMAP类型 | 向量注入 | 搜索方式 |
|------|---------|---------|---------|
| **UCS模式** | 监督学习 | ✅ category_weight=150.0 | 传统metadata搜索 |
| **Gravity模式** | 无监督 | ❌ 不使用 | AI语义搜索 |
| **Preset模式** | 混合 | ✅ 基于预设关键词 | AI语义搜索 |
| **Library模式** | ❌ 不使用UMAP | ❌ | 文件路径搜索 |

---

## 🐛 常见Bug定位

### Bug: "大陆漂移"（子类分离）
**症状**: 同一大类的子类分布在不同的"大陆"区域  
**定位**: `core/umap_config.py` - `CATEGORY_WEIGHT`太小  
**修复**: 提升权重（当前150.0，可尝试200.0）

### Bug: 点过度重叠
**症状**: 可视化图中所有点挤在一起  
**定位**: `core/umap_config.py` - `MIN_DIST`太小  
**修复**: 增大`MIN_DIST`（当前0.1，可尝试0.2-0.3）

### Bug: UMAP计算不一致
**症状**: 离线脚本和UI计算结果不同  
**定位**: 检查是否都使用了`core/umap_config.py`  
**修复**: 确保所有脚本从统一配置读取参数

### Bug: OneHotEncoder错误（-1陷阱）
**症状**: `ValueError: -1 not in categories`  
**定位**: `inject_category_vectors()`传入编码后的整数而非字符串  
**修复**: 确保传入原始字符串列表（包含"UNCATEGORIZED"）

---

## 📊 关键参数速查表

| 参数 | 位置 | 当前值 | 作用 | 调优方向 |
|------|------|--------|------|---------|
| `CATEGORY_WEIGHT` | `core/umap_config.py` | 150.0 | 强制大类聚合 | ↑ 提升可增强聚合 |
| `MIN_DIST` | `core/umap_config.py` | 0.1 | 防止点重叠 | ↑ 提升可分离点 |
| `N_NEIGHBORS` | `core/umap_config.py` | 30 | 局部结构保留 | ↓ 减小更多细节 |
| `TARGET_WEIGHT` | `core/umap_config.py` | 1.0 | 监督学习权重 | ⚠️ 影响很小（被向量注入掩盖） |

---

## 🔧 快速修改指南

### 场景1: 子类仍然分离
```python
# 文件: core/umap_config.py
# 修改:
CATEGORY_WEIGHT = 200.0  # 从150.0提升
MIN_DIST = 0.15          # 配合提升，防止过度重叠
```

### 场景2: 点过度紧密
```python
# 文件: core/umap_config.py
# 修改:
MIN_DIST = 0.2           # 从0.1提升
SPREAD = 1.5             # 从1.0提升，增加扩散
```

### 场景3: 测试不同权重
```python
# 文件: core/umap_config.py
# 修改:
CATEGORY_WEIGHT = 75.0   # 测试值1
# 或
CATEGORY_WEIGHT = 100.0  # 测试值2
# 然后运行: python tools/verify_subset.py --all
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
# 重新计算UMAP坐标
python recalculate_umap.py

# 完整重建地图
python rebuild_atlas.py

# 验证测试（全库）
python tools/verify_subset.py --all --limit 1000

# 验证测试（特定类别）
python tools/verify_subset.py ANIMALS --limit 500

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
- ✅ 向量注入是UCS模式的核心（`inject_category_vectors()`）
- ✅ Gravity模式不使用向量注入（无监督UMAP）
- ✅ 测试脚本使用自适应权重，但配置统一管理
