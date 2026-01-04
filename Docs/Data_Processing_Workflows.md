# 数据处理工作流说明

## 概述

Sonic Compass 提供了多个数据处理脚本，用于不同的场景和需求。

## 工作流分类

### 1. 完整重建流程 (Full Rebuild)

**脚本**: `rebuild_atlas.py`

**功能**: 
- 重新向量化所有数据（使用GPU加速）
- 计算Category质心（用于AI语义仲裁）
- 计算Supervised UMAP坐标
- 保存所有缓存文件

**适用场景**:
- 首次运行
- 数据库更新（新增/删除文件）
- 向量模型更新
- 需要重新计算质心

**耗时**: 最长（取决于数据量，通常10-30分钟）

**输出文件**:
- `cache/metadata.pkl` - 元数据
- `cache/embeddings.npy` - 向量矩阵
- `cache/coordinates.npy` - UMAP坐标

---

### 2. 仅重新计算UMAP坐标 (UMAP Recalculation Only)

**脚本**: `recalculate_umap.py`

**功能**:
- 加载现有向量缓存（不重新向量化）
- 使用新参数重新计算UMAP坐标
- 仅更新坐标文件

**适用场景**:
- 调整UMAP参数（n_neighbors, min_dist等）
- 快速测试不同参数效果
- 向量数据未变化，只需更新布局

**耗时**: 中等（通常2-5分钟，取决于数据量）

**前提条件**:
- 必须存在 `cache/metadata.pkl` 和 `cache/embeddings.npy`

**输出文件**:
- `cache/coordinates.npy` - 更新的UMAP坐标

---

### 3. 仅重新向量化 (Vectors Rebuild Only)

**脚本**: `rebuild_vectors_only.py`

**功能**:
- 重新向量化所有数据
- 保留现有UMAP坐标（但会失效）

**适用场景**:
- 向量模型更新
- 需要重新计算质心
- **注意**: 向量化后必须重新计算UMAP坐标

**耗时**: 较长（通常5-20分钟）

**警告**: 
- 向量化完成后，现有UMAP坐标将不再匹配
- 必须随后运行 `recalculate_umap.py`

**输出文件**:
- `cache/metadata.pkl` - 更新的元数据
- `cache/embeddings.npy` - 更新的向量矩阵

---

## 工作流选择指南

### 场景1: 首次运行
```
python rebuild_atlas.py
```

### 场景2: 调整UMAP参数（已有向量缓存）
```
python recalculate_umap.py
```

### 场景3: 数据库更新（新增文件）
```
python rebuild_atlas.py  # 完整重建
```

### 场景4: 向量模型更新
```
python rebuild_vectors_only.py  # 重新向量化
python recalculate_umap.py      # 重新计算坐标
```

### 场景5: 仅测试UMAP参数效果
```
python recalculate_umap.py  # 快速迭代
```

---

## 软件内按钮

在软件UI中，提供了两个按钮：

1. **🔄 Rebuild Atlas (Full)**
   - 对应 `rebuild_atlas.py`
   - 完整重建流程
   - 在后台线程执行，UI不卡死

2. **🔄 Recalc UMAP Only**
   - 对应 `recalculate_umap.py`
   - 仅重新计算坐标
   - 在后台线程执行，UI不卡死

---

## 参数说明

### UMAP参数（当前设置）

- `n_neighbors=30`: 增强全局结构，形成紧密大陆
- `min_dist=0.01`: 允许紧密堆积，减少蜂窝间缝隙
- `target_weight=0.7`: 70%依赖分类标签，30%语义漂移
- `target_metric='categorical'`: 适用于离散分类标签

### 坐标归一化

- 范围: `0-3000`
- 目的: 减少"海洋"空隙，让数据更紧凑

---

## 性能对比

| 工作流 | 向量化 | UMAP计算 | 总耗时 | 适用场景 |
|--------|--------|----------|--------|----------|
| Full Rebuild | ✅ | ✅ | 10-30分钟 | 首次/数据库更新 |
| UMAP Only | ❌ | ✅ | 2-5分钟 | 参数调整 |
| Vectors Only | ✅ | ❌ | 5-20分钟 | 模型更新 |

---

## 注意事项

1. **缓存一致性**: 
   - 向量和坐标必须匹配
   - 如果只更新向量，必须重新计算坐标

2. **内存占用**:
   - UMAP计算时，`n_neighbors=30` 比 `n_neighbors=15` 占用更多内存
   - 大数据集（>100万条）可能需要调整参数

3. **线程安全**:
   - 软件内的重建操作在后台线程执行
   - 不会阻塞UI

4. **进度反馈**:
   - 所有操作都有进度条显示
   - 关键步骤会输出日志

