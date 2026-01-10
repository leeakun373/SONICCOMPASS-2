# 测试指南 - Fixed Archipelago Strategy

## 📋 实施完成检查

### ✅ 已完成的任务

根据计划文件，所有任务均已完成：

1. ✅ **核心模块创建**
   - `core/layout_engine.py` - 布局引擎（包含所有必需函数）
   - `core/data_processor.py` - 支持多坐标文件
   - `core/umap_config.py` - UCS/Gravity模式参数

2. ✅ **工具脚本创建**
   - `tools/extract_category_centroids.py` - 坐标提取脚本
   - `tools/plot_ucs_layout.py` - 可视化调试工具

3. ✅ **脚本更新**
   - `rebuild_atlas.py` - 支持 `--mode` 参数
   - `recalculate_umap.py` - 支持 `--mode` 参数
   - `tools/verify_subset.py` - 支持 `--mode` 参数

4. ✅ **UI更新**
   - `ui/main_window.py` - 模式切换支持
   - `ui/visualizer/sonic_universe.py` - 坐标更新方法

5. ⚠️ **配置文件**
   - `data_config/ucs_coordinates.json` - **需要先运行提取脚本生成**

---

## 🚀 测试流程

### 步骤 1：生成UCS坐标配置文件（首次使用）

**重要**：在使用UCS模式之前，必须先生成 `ucs_coordinates.json` 配置文件。

#### 1.1 前提条件

确保你已经运行过至少一次完整的地图重建，生成了 `cache/coordinates.npy` 和 `cache/metadata.pkl`：

```bash
# 如果没有，先运行完整重建（使用旧逻辑）
python rebuild_atlas.py
```

#### 1.2 提取类别质心

运行提取脚本，从现有坐标生成 UCS 配置初稿：

```bash
python tools/extract_category_centroids.py
```

**输出**：
- 生成 `data_config/ucs_coordinates.json`
- 显示每个类别的中心坐标、半径和点数
- 自动计算 `gap_buffer`（半径的15%）

#### 1.3 可视化并调整配置（可选）

使用可视化工具查看82个大类的布局：

```bash
# 显示在窗口中
python tools/plot_ucs_layout.py

# 或保存为图片
python tools/plot_ucs_layout.py --output ucs_layout_preview.png
```

**检查点**：
- 是否有类别重叠（WARNING日志）
- 布局是否合理（语义相关的类别是否相邻）
- 半径是否合适（大的类别是否分配了更大的空间）

**手动调整**（如果需要）：
- 编辑 `data_config/ucs_coordinates.json`
- 调整 `x`, `y`, `radius`, `gap_buffer`
- 重新运行可视化工具验证

---

### 步骤 2：测试UCS模式计算

#### 2.1 计算UCS模式坐标

```bash
# 只计算UCS模式（需要 ucs_coordinates.json）
python rebuild_atlas.py --mode ucs

# 或同时计算两种模式（推荐）
python rebuild_atlas.py --mode both
```

**预期输出**：
```
🗺️  UCS模式: 定锚群岛策略 (Fixed Archipelago Strategy)
📋 加载UCS坐标配置...
   已加载 82 个大类的坐标配置
🏷️  按主类别分组数据...
   分组完成: 82 个类别, X 个未分类
🚀 开始局部UMAP计算...
   计算 ANIMALS: 1234 个点... ✅
   计算 WEAPONS: 567 个点... ✅
   ...
🔗 合并坐标...
✅ UCS坐标计算完成并保存
```

**检查点**：
- `cache/coordinates_ucs.npy` 文件是否生成
- 每个大类是否显示计算进度
- 是否有碰撞检测警告

#### 2.2 验证UCS坐标

使用验证脚本测试UCS模式：

```bash
# 测试全库（UCS模式，默认）
python tools/verify_subset.py --all --mode ucs

# 测试特定类别
python tools/verify_subset.py WEAPON --mode ucs
```

**验证要点**：
- 同一主类别的数据是否聚集在预设中心周围
- 是否还有"大陆漂移"现象（应该没有）
- 每个大类内部是否保持了局部结构

---

### 步骤 3：测试Gravity模式计算

#### 3.1 计算Gravity模式坐标

```bash
# 只计算Gravity模式
python rebuild_atlas.py --mode gravity

# 或使用 recalculate_umap.py（如果已有向量缓存）
python recalculate_umap.py --mode gravity
```

**预期输出**：
```
🌌 Gravity模式: 纯无监督全局UMAP
🌌 计算Gravity模式布局（纯无监督全局UMAP）...
   ✅ Gravity布局计算完成: (N, 2)
✅ Gravity坐标计算完成并保存
```

**检查点**：
- `cache/coordinates_gravity.npy` 文件是否生成
- 全局分布是否自然（无强制聚类）
- 跨类别相似性是否可见

#### 3.2 验证Gravity坐标

```bash
# 测试全库（Gravity模式）
python tools/verify_subset.py --all --mode gravity
```

**验证要点**：
- 分布是否自然（基于纯声学特征）
- 是否有跨类别聚类（这是Gravity模式的特性）
- 搜索结果是否能基于语义相似度重排

---

### 步骤 4：测试模式切换（UI测试）

#### 4.1 启动应用程序

```bash
python main.py
```

或

```bash
python gui_main.py
```

#### 4.2 验证初始加载

**检查点**：
- 应用启动时是否自动加载UCS模式坐标（默认）
- 如果没有坐标文件，是否提示重新计算
- 坐标是否与embeddings一致（validate_consistency）

#### 4.3 测试模式切换

**操作**：
1. 点击 **Explorer Mode** 按钮（UCS模式）
   - 应该加载 `coordinates_ucs.npy`
   - 视图应该重置到世界地图范围
   - 同一大类的数据应该聚集在一起

2. 点击 **Gravity Mode** 按钮
   - 应该加载 `coordinates_gravity.npy`
   - 视图应该重置到数据分布中心
   - 应该显示纯声学特征的全局分布

**检查点**：
- 模式切换是否平滑
- 坐标是否正确加载
- 视图是否自动重置（避免空白）
- 是否有漂移现象（UCS模式下不应该有）

---

### 步骤 5：性能测试

#### 5.1 比较计算时间

**UCS模式**（局部UMAP）：
```bash
time python rebuild_atlas.py --mode ucs
```

**Gravity模式**（全局UMAP）：
```bash
time python rebuild_atlas.py --mode gravity
```

**预期**：
- UCS模式可能更快（82个小数据集 vs 1个大数据集）
- 如果使用并行化，UCS模式速度提升更明显

#### 5.2 内存使用检查

- UCS模式：内存使用分散（多个小计算）
- Gravity模式：内存使用集中（一个大数据集）

---

## 🔍 验证检查清单

### UCS模式验证

- [ ] `data_config/ucs_coordinates.json` 存在且格式正确
- [ ] `cache/coordinates_ucs.npy` 成功生成
- [ ] 每个大类内部数据聚集在预设中心周围
- [ ] 没有"大陆漂移"现象（同一大类的子类不会分离）
- [ ] 大类内部保持了局部结构（LOD 1/2 可见）
- [ ] 碰撞检测没有严重警告（如果有，调整配置）

### Gravity模式验证

- [ ] `cache/coordinates_gravity.npy` 成功生成
- [ ] 全局分布自然（无强制聚类）
- [ ] 跨类别相似性可见（例如：枪声和爆炸声可能接近）
- [ ] 搜索结果能基于语义相似度重排

### UI功能验证

- [ ] 启动时正确加载默认模式坐标
- [ ] 模式切换功能正常
- [ ] 视图自动重置（避免空白）
- [ ] 坐标一致性验证通过
- [ ] 缺失坐标时自动重新计算

### 向后兼容性

- [ ] 旧版本的 `coordinates.npy` 仍可加载（向后兼容）
- [ ] 旧脚本仍能工作（如果有）

---

## ⚠️ 常见问题排查

### 问题 1：UCS模式计算失败

**错误信息**：`FileNotFoundError: UCS坐标配置文件不存在`

**解决方案**：
```bash
# 1. 先运行提取脚本生成配置文件
python tools/extract_category_centroids.py

# 2. 如果提取脚本失败，先运行完整重建
python rebuild_atlas.py
```

### 问题 2：类别重叠警告

**错误信息**：`[WARNING] 类别重叠: ANIMALS 与 WEAPONS`

**解决方案**：
1. 使用可视化工具查看布局：
   ```bash
   python tools/plot_ucs_layout.py
   ```
2. 编辑 `data_config/ucs_coordinates.json`：
   - 增加类别间的距离
   - 减小 `radius`
   - 增加 `gap_buffer`
3. 重新运行计算

### 问题 3：坐标文件与embeddings不一致

**错误信息**：`[WARNING] 坐标文件与embeddings不一致: 1000 vs 999`

**解决方案**：
```bash
# 重新计算坐标
python rebuild_atlas.py --mode ucs
# 或
python recalculate_umap.py --mode ucs
```

### 问题 4：小类别处理异常

**症状**：某些类别（< 5个样本）显示异常

**原因**：小类别使用特殊排列策略，可能看起来不自然

**解决方案**：
- 这是预期行为（小类别使用多边形排列）
- 如果数据量增加，会自动使用UMAP计算

### 问题 5：性能问题

**症状**：UCS模式计算很慢

**原因**：顺序执行82个局部UMAP（并行化尚未实现）

**解决方案**：
- 当前版本使用顺序执行
- 后续版本将支持并行化（ProcessPoolExecutor）
- 临时方案：可以修改 `core/layout_engine.py` 中的 `use_parallel=True` 为 `use_parallel=False`

---

## 📊 测试数据对比

### 测试前（旧版本）

- 同一大类的子类可能会分离（"大陆漂移"）
- 例如：ANMLAqua 和 ANMLWcat 可能相距很远

### 测试后（新版本 - UCS模式）

- 同一大类的所有子类强制聚集在预设中心周围
- 例如：所有 ANIMALS 子类都在 ANIMALS 大陆内
- 0%漂移（硬规则保证）

### 测试后（新版本 - Gravity模式）

- 纯声学特征分布
- 跨类别相似性可见
- 搜索结果能重排分布

---

## 🎯 快速测试命令

### 完整测试流程（首次使用）

```bash
# 1. 生成配置文件（如果还没有 coordinates.npy，先运行完整重建）
python tools/extract_category_centroids.py

# 2. 可视化配置（检查布局）
python tools/plot_ucs_layout.py

# 3. 计算两种模式坐标
python rebuild_atlas.py --mode both

# 4. 测试UCS模式
python tools/verify_subset.py --all --mode ucs

# 5. 测试Gravity模式
python tools/verify_subset.py --all --mode gravity

# 6. 启动UI测试模式切换
python main.py
```

### 仅重新计算坐标（已有向量缓存）

```bash
# 重新计算UCS坐标
python recalculate_umap.py --mode ucs

# 重新计算Gravity坐标
python recalculate_umap.py --mode gravity

# 同时计算两种
python recalculate_umap.py --mode both
```

### 快速验证（小数据集）

```bash
# 测试特定类别
python tools/verify_subset.py WEAPON --mode ucs --limit 100
python tools/verify_subset.py ANIMAL --mode ucs --limit 100
```

---

## 📝 测试报告模板

测试完成后，请记录以下信息：

```
测试日期: YYYY-MM-DD
测试人员: [姓名]

1. 配置文件生成
   - [ ] extract_category_centroids.py 运行成功
   - [ ] ucs_coordinates.json 生成
   - [ ] 类别数量: __/82
   - [ ] 重叠警告数量: __

2. UCS模式计算
   - [ ] rebuild_atlas.py --mode ucs 运行成功
   - [ ] coordinates_ucs.npy 生成
   - [ ] 计算时间: __ 秒
   - [ ] 是否有漂移: [是/否]

3. Gravity模式计算
   - [ ] rebuild_atlas.py --mode gravity 运行成功
   - [ ] coordinates_gravity.npy 生成
   - [ ] 计算时间: __ 秒
   - [ ] 分布是否自然: [是/否]

4. UI测试
   - [ ] 启动成功
   - [ ] UCS模式加载正确
   - [ ] Gravity模式切换正常
   - [ ] 视图重置正常

5. 问题记录
   - [问题描述]
   - [解决方案]

6. 性能对比
   - 旧版本计算时间: __ 秒
   - 新版本UCS时间: __ 秒
   - 新版本Gravity时间: __ 秒
```

---

## 🎉 预期效果

### ✅ 成功指标

1. **UCS模式**：
   - ✅ 0%漂移（同一大类的子类不会分离）
   - ✅ 大类内部保持局部结构
   - ✅ 82个大类分布在预设位置

2. **Gravity模式**：
   - ✅ 纯声学特征分布
   - ✅ 跨类别相似性可见
   - ✅ 搜索结果能重排

3. **性能**：
   - ✅ UCS模式可能更快（局部计算）
   - ✅ 内存使用更分散

4. **用户体验**：
   - ✅ 模式切换平滑
   - ✅ 视图自动重置
   - ✅ 无空白或异常显示

---

## 📚 相关文档

- [Fixed Archipelago Strategy 详细说明](./SUPER_ANCHOR_STRATEGY.md)
- [项目结构说明](./PROJECT_STRUCTURE.md)
- [AI快速参考](./AI_QUICK_REFERENCE.md)

---

## 💡 提示

1. **首次使用**：必须先运行 `extract_category_centroids.py` 生成配置文件
2. **配置调整**：使用 `plot_ucs_layout.py` 可视化并调整配置
3. **性能优化**：后续版本将支持并行化，当前使用顺序执行
4. **向后兼容**：旧版本的 `coordinates.npy` 仍可加载

---

**祝测试顺利！** 🚀
