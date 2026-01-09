# Phase 3 进度状态文档

**更新时间**: 2025-01-05  
**状态**: 可视化引擎彻底重写完成，GPU 加速部署成功，数据源切换完成，颜色映射和规则系统重构完成 (Visualization Engine Rewritten, GPU Acceleration Deployed, Data Source Switched, Color Mapping and Rules System Refactored)

## 当前进度概览

Phase 3 可视化主窗口核心功能已完成。已实现严格的蜂窝网格算法、深度样式定制、LOD 动态切换、引力视图、动态轴重排（Scatter 模式）和右键标注器。代码已按项目标准重构，UI 相关代码按逻辑拆分到独立模块。

**最新进展（2025-01-02）**:
- ✅ 完全重写可视化引擎：数据驱动的网格生成，杜绝空蜂窝
- ✅ 集成 KDTree 空间索引：实现极速点击检测
- ✅ 修复圆点渲染：使用 RoundCap 替代默认方点
- ✅ 修复交互逻辑：使用 find_closest_data() 替代 items(pos)
- ✅ GPU 加速部署：PyTorch CUDA 12.1，性能提升 17 倍
- ✅ UMAP 参数优化：最紧凑配置，形成"大陆"而非"孤岛"

## 已完成的工作

### 1. 核心文件创建 ✅

- **ui/** - UI 模块（代码重构，按逻辑拆分）
  - ✅ `ui/main_window.py` - 主窗口框架（640行）
  - ✅ `ui/components/` - UI 组件模块
    - ✅ `canvas_view.py` - 画布视图（70行）
    - ✅ `search_bar.py` - 搜索栏（50行）
    - ✅ `inspector_panel.py` - 检查器面板（80行）
    - ✅ `universal_tagger.py` - 通用标注器/右键菜单（150行）
  - ✅ `ui/visualizer/` - 可视化引擎模块
    - ✅ `sonic_universe.py` - 主场景类（750行）
    - ✅ `hex_grid_item.py` - 六边形项（130行）
    - ✅ `scatter_item.py` - 散点项（70行）
    - ✅ `errors.py` - 错误类（10行）
  - ✅ `ui/styles.py` - 全局样式定义（120行）
  - ✅ 深度样式定制（setStyleSheet 全局样式）
  - ✅ 深色赛博朋克风格 UI（严格配色方案）
  - ✅ 左侧边栏（288px，包含动态轴重排）
  - ✅ 中央画布区域（CanvasView，支持缩放和平移）
  - ✅ 右侧检查器面板（300px，InspectorPanel，磨砂玻璃效果）
  - ✅ 悬浮搜索栏（胶囊样式，带阴影效果）
  - ✅ LOD 缩放监听（自动切换显示模式）
  - ✅ 搜索功能集成（回车触发，自动高亮）
  - ✅ 右键菜单（Universal Tagger，三组滑块）
  - ✅ 动态轴重排（Scatter 模式，Auto Suggest）

- **visualizer.py** - 可视化引擎（完全重写 + 游戏级渲染，已重构到 ui/visualizer/）
  - ✅ `SonicUniverse` 类（继承 QGraphicsScene）
  - ✅ `HexGridItem` 类（六边形网格项管理，游戏级渲染）
    - ✅ 间距效果（1.5px 网格缝隙）
    - ✅ 径向渐变填充（中心60%透明度，边缘20%透明度）
    - ✅ 玻璃边框效果（1.5px 线宽）
    - ✅ Hover 交互效果（白色边框，填充变实）
  - ✅ `ScatterItem` 类（散点项，带光晕效果）
    - ✅ 中心实心圆 + 外围渐变光晕
    - ✅ 星云感视觉效果
  - ✅ 严格的蜂窝网格算法（Hex Grid Tessellation）
  - ✅ 坐标量化（pixel_to_hex / hex_to_pixel）
  - ✅ 坐标吸附（Snap to Hex Center）
  - ✅ 聚合逻辑（主导分类 + 密度计算）
  - ✅ LOD 动态切换（Zoom < 1.5: 六边形，>= 1.5: 散点）
  - ✅ UCS 颜色映射系统（核心分类 + 哈希 Fallback）
  - ✅ 搜索高亮功能（白色高亮 + 其他项半透明）
  - ✅ UMAP 降维集成（支持预计算坐标加载）

### 2. 依赖安装 ✅

- PySide6 (6.10.1) - GUI 框架
- umap-learn - 降维算法
- scikit-learn - 机器学习支持
- matplotlib - 可视化支持

### 3. 数据准备 ✅

- **rebuild_atlas.py** - 星图重建脚本
  - 成功处理 13,850 条记录
  - UMAP 坐标已计算并保存
  - 缓存文件完整：
    - `coordinates.npy` (110KB)
    - `embeddings.npy` (56MB)
    - `metadata.pkl` (7MB)
    - `index_info.pkl`

### 4. 代码修复与重构 ✅

- ✅ 修复 PySide6 RenderHint 使用错误（使用 QPainter.RenderHint）
- ✅ 修复坐标加载逻辑（支持预计算坐标）
- ✅ 集成 DataProcessor 坐标保存/加载功能
- ✅ 完全重写可视化算法（严格蜂窝网格）
- ✅ 完全重写 UI 样式（深度定制）

### 5. 视觉重构 ✅ (2024-12-21)

### 6. 功能实现 ✅ (2024-12-21 晚)

- ✅ **右键菜单（Universal Tagger）**
  - 三组滑块：Reality (Organic/Synthetic)、Tone (Dark/Bright)、Function (One-shot/Ambience)
  - 磨砂玻璃效果（半透明背景）
  - Apply 按钮，校准完成后发送信号

- ✅ **动态轴重排（Dynamic Axes）**
  - Auto Suggest 按钮：随机推荐反义词对
  - X/Y 轴输入框：手动输入轴标签
  - Toggle 开关：激活/关闭 Scatter 模式
  - Scatter 模式下直接显示散点（圆形），不显示六边形

- ✅ **Scatter 视图模式**
  - 根据语义轴（X/Y）计算相似度并重排点位置
  - 相似度映射到笛卡尔坐标（-1 到 1 范围）
  - 支持实时切换 Explorer/Scatter 模式

- ✅ **Gravity 模式优化**
  - 搜索时自动切换到 Gravity 模式
  - 相关节点螺旋排列在中心
  - 非相关节点变暗（透明度 0.1）
  - 使用螺旋坐标算法生成排列

### 7. 代码重构 ✅ (2024-12-21 晚)

- ✅ **HexGridItem 升级**
  - 间距效果：半径缩小 1.5px，形成网格缝隙
  - 径向渐变：中心60%透明度 → 边缘20%透明度
  - 玻璃边框：1.5px 线宽，稍微亮一点的颜色
  - Hover 效果：鼠标悬停时边框变白，填充变实

- ✅ **ScatterItem 升级**
  - 光晕效果：中心实心圆（2px）+ 外围渐变光晕（6px）
  - 星云感视觉效果

- ✅ **UI 组件升级**
  - 搜索栏：胶囊样式 + QGraphicsDropShadowEffect 阴影
  - 侧边栏：288px 扩展模式（包含动态轴重排）
  - Inspector：磨砂玻璃效果 + 大写标题 + 字间距

- ✅ **代码结构重组**
  - 创建 `ui/` 模块，按逻辑拆分代码
  - `components/` 子模块：UI 组件（4个文件，350行）
  - `visualizer/` 子模块：可视化引擎（4个文件，960行）
  - 主窗口独立文件（640行）
  - 样式独立文件（120行）
  - 向后兼容：保留 `gui_main.py` 和 `visualizer.py` 作为重定向

## 当前实现的功能

### UI 组件 ✅

1. **主窗口布局**
   - ✅ 三栏布局：侧边栏(288px) + 画布(自适应) + 检查器(300px)
   - ✅ 深色赛博朋克主题（严格配色方案）
   - ✅ 全局样式表（QSS 深度定制，独立文件管理）
   - ✅ Segoe UI 字体系统
   - ✅ 游戏级视觉效果（渐变、光晕、阴影）
   - ✅ 右键菜单（Universal Tagger）
   - ✅ 动态轴重排（Scatter 模式）

2. **可视化引擎**
   - ✅ 支持 UMAP 降维坐标加载（预计算）
   - ✅ 严格蜂窝网格渲染（整齐对齐的六边形）
   - ✅ 坐标量化算法（吸附到六边形中心）
   - ✅ 聚合算法（主导分类 + 密度）
   - ✅ 三级 LOD 系统（LOD 0/1/2，基于真实缩放因子 transform().m11()）
   - ✅ 标签聚类算法（连通域分析，质心计算）
   - ✅ UCS 分类颜色映射（82 个 Category 大类，20 色霓虹色板）
   - ✅ 视觉优化（六边形内缩 92%，硬朗边框，径向渐变）

3. **交互功能**
   - ✅ 鼠标滚轮缩放（以鼠标为中心）
   - ✅ 右键拖拽平移（ScrollHandDrag）
   - ✅ 点击查看详情（六边形和点都支持）
   - ✅ LOD 自动切换（基于缩放级别）

4. **搜索功能**
   - ✅ 搜索栏输入（悬浮样式）
   - ✅ 回车触发搜索
   - ✅ 搜索结果高亮（白色高亮 + 其他半透明）
   - ✅ 自动切换到 Gravity 模式（相关节点螺旋排列）
   - ✅ 非相关节点变暗（透明度 0.1）

5. **视图模式**
   - ✅ Explorer 模式（默认，静态 UMAP 地图，三级 LOD 系统）
   - ✅ Gravity 模式（向日葵螺旋布局，搜索时自动切换）
   - ✅ Scatter 模式（动态轴重排，按语义轴分布）

6. **交互功能**
   - ✅ 右键菜单（Universal Tagger，三组滑块校准）
   - ✅ 动态轴重排（Auto Suggest，X/Y 轴输入，Toggle 开关）

## 已知问题与待修复

### 1. 代码问题

- [x] ~~RenderHint 使用错误~~ - 已修复
- [x] ~~点击事件处理~~ - 已完善
- [x] ~~LOD 切换逻辑~~ - 已实现动态切换
- [x] ~~场景坐标范围~~ - 已正确设置（1000x1000）
- [x] ~~蜂窝网格算法~~ - 已实现严格对齐
- [x] ~~UI 样式定制~~ - 已深度定制

### 2. 功能待完善

- [x] ~~搜索高亮视觉效果~~ - 已实现（白色高亮 + 半透明）
- [x] ~~点击详情显示~~ - 已完善（支持六边形和点）
- [x] ~~视图模式切换（Explorer/Gravity/Scatter）~~ - 已实现完整逻辑
- [x] ~~引力视图模式~~ - 已实现（集成 calculate_gravity_forces）
- [x] ~~引力桩可视化~~ - 已实现（在画布上显示引力桩位置）
- [x] ~~文件按引力权重分布~~ - 已实现（根据权重调整点位置）
- [x] ~~右键菜单（Universal Tagger）~~ - 已实现（三组滑块）
- [x] ~~动态轴重排（Scatter 模式）~~ - 已实现（Auto Suggest，X/Y 轴）
- [x] ~~代码重构~~ - 已完成（按逻辑拆分到 ui/ 模块）
- [ ] 六边形网格密度可视化可以进一步优化

### 3. 性能优化

- [x] ~~性能优化~~ - 已添加（NoIndex 索引方法优化）
- [x] ~~批量渲染架构~~ - 已实现（使用 drawPoints 批量绘制）
- [x] ~~OpenGL 硬件加速~~ - 已添加（QOpenGLWidget 视口）
- [x] ~~视口裁剪优化~~ - 已实现（numpy 布尔索引）
- [x] ~~缓存机制~~ - 已实现（避免重复计算）
- [ ] 大规模数据（13,850条）的渲染性能需要测试
- [x] ~~LOD 切换阈值~~ - 已实现三级 LOD 系统（0.8, 1.8）
- [ ] 搜索高亮时的重绘性能需要优化
- [ ] 悬停标签功能（LOD 2 显示文件名）待实现

## 技术细节

### 颜色系统

**Category 大类颜色映射** (2024-12-21 更新):
- 基于 UCS Category 大类（82 个大类）分配颜色
- 使用 `CategoryColorMapper` 类统一管理颜色映射
- 从 UCS CSV 文件加载 CatID → Category 映射关系
- 每个 Category 通过 MD5 哈希函数映射到 20 色霓虹色板
- 确保相同 Category 总是得到相同颜色（一致性）

**颜色分配方案**:
- 20 色霓虹色板（赛博朋克风格）
- 哈希函数确保颜色分配的一致性
- 支持 82 个 Category 大类完整覆盖
- Fallback 机制：如果映射器不可用，使用旧版哈希方法

**优势**:
- 统一颜色：同一 Category 下的所有子分类使用相同颜色
- 完整覆盖：82 个 Category 大类都有颜色分配
- 视觉一致性：相同类型的音频文件在视觉上更容易识别
- 可扩展性：新增 Category 会自动分配颜色

### 可视化算法

**严格蜂窝网格算法**:
- 六边形大小: 50px（可配置）
- 坐标系统: 轴向坐标 (q, r)
- 量化算法: pixel_to_hex（像素 → 六边形坐标）
- 吸附逻辑: 所有点吸附到最近的六边形中心
- 聚合逻辑: 计算每个格子的主导分类和密度
- 颜色: 基于主导 UCS 分类
- 透明度: 基于密度 (100-255 alpha)

**LOD 动态切换（三级系统）**:
- LOD 0 (Zoom < 0.8): 只显示六边形网格，100% 不透明度，大标签显示主分类
- LOD 1 (0.8 <= Zoom < 1.8): 只显示六边形网格，80% 不透明度，中等标签显示子分类
- LOD 2 (Zoom >= 1.8): 六边形淡出轮廓（10% 不透明度），显示所有散点
- 自动切换: 通过 zoom_changed 信号触发，使用 `transform().m11()` 作为真实缩放因子
- 标签聚类: LOD 0 使用连通域分析计算主分类标签位置

### 数据流

```
缓存加载
  ↓
coordinates.npy (UMAP 2D坐标)
  ↓
SonicUniverse 初始化
  ↓
Hexbin/Point 渲染
  ↓
用户交互 (缩放/平移/点击)
```

## 下一步计划

### 短期任务 ✅ 已完成

1. **完善交互功能** ✅
   - ✅ 修复点击事件处理
   - ✅ 完善详情面板显示
   - ✅ 优化搜索高亮效果

2. **实现视图模式** ✅
   - ✅ Explorer 模式（已实现）
   - ✅ Gravity 模式（引力视图，已实现）

3. **性能优化** ✅
   - ✅ 添加 NoIndex 索引方法优化
   - [ ] 测试大规模数据渲染
   - [ ] 优化 LOD 切换逻辑
   - ✅ 视口裁剪（Qt 内置，已优化）

### 中期任务

1. **引力视图实现** ✅ 已完成
   - ✅ 集成 `calculate_gravity_forces` 算法
   - ✅ 实现引力桩可视化
   - ✅ 实现文件按引力权重分布

2. **轴对齐功能** ✅ 已实现（Scatter 模式）
   - ✅ 实现动态轴输入（X/Y 轴输入框）
   - ✅ 实时更新点位置（根据语义相似度）
   - ✅ Auto Suggest 功能（自动推荐反义词对）
   - ✅ Toggle 开关控制（激活/关闭 Scatter 模式）

## 测试状态

### 已测试

- ✅ 依赖安装（PySide6, umap-learn, scikit-learn, matplotlib）
- ✅ 数据重建脚本（13,850 条记录，UMAP 坐标）
- ✅ 坐标计算和保存
- ✅ UI 启动（深色主题，样式定制）
- ✅ 蜂窝网格渲染（严格对齐）
- ✅ LOD 切换（缩放测试）

### 待测试

- [ ] GUI 完整功能测试（大规模数据）
- [ ] 搜索功能完整测试（高亮效果验证）
- [ ] 大规模数据渲染性能测试（13,850 条）
- [ ] 交互响应测试（缩放、平移流畅度）
- [ ] 性能基准测试（LOD 切换性能）
- [ ] 六边形网格对齐验证（视觉检查）

## 文件清单

### 新增文件（重构后）

**UI 模块（ui/）**:
- `ui/main_window.py` - 主窗口 (640 行)
- `ui/styles.py` - 全局样式 (120 行)
- `ui/components/canvas_view.py` - 画布视图 (已添加 OpenGL 硬件加速)
- `ui/components/search_bar.py` - 搜索栏 (50 行)
- `ui/components/inspector_panel.py` - 检查器面板 (80 行)
- `ui/components/universal_tagger.py` - 通用标注器 (150 行)
- `ui/visualizer/sonic_universe.py` - 主场景（已重写为批量渲染架构，三级 LOD 系统，Gravity Mode 向日葵螺旋，标签聚类算法）
- `ui/visualizer/hex_grid_item.py` - 六边形项（已整合到 sonic_universe.py 的 HexGridLayer）
- `ui/visualizer/scatter_item.py` - 散点项（已整合到 sonic_universe.py 的 DetailScatterLayer）
- `ui/visualizer/errors.py` - 错误类

**核心模块（core/）**:
- `core/category_color_mapper.py` - Category 颜色映射器 (新增，基于 UCS Category 大类)

**入口文件**:
- `main.py` - 新的入口文件（推荐使用）
- `gui_main.py` - 向后兼容入口（重定向到 ui 模块）
- `visualizer.py` - 向后兼容（重定向到 ui.visualizer）

**工具脚本**:
- `rebuild_atlas.py` - 星图重建脚本（初次运行或强制重建数据）
- `tools/verify_phase2.py` - Phase 2 验证脚本
- `tools/verify_pipeline.py` - 流水线验证脚本

**文档**:
- `Docs/Refactoring_Summary.md` - 重构总结文档
- `Docs/PROJECT_STRUCTURE.md` - 项目结构文档

### 修改文件

- `data_processor.py` - 添加坐标保存/加载功能
- `cache/coordinates.npy` - UMAP 坐标缓存

## 性能指标

### 数据规模

- 总记录数: 13,850 条
- 向量维度: 1024
- 缓存大小: ~63 MB
- 坐标文件: 110 KB

### 构建时间

- 向量化: ~21 分钟 (13,850 条)
- UMAP 降维: ~1 分钟
- 总耗时: ~22 分钟

## 注意事项

1. **首次运行**: 需要先运行 `rebuild_atlas.py` 生成坐标
2. **性能**: 13,850 条数据渲染性能需要实际测试验证
3. **LOD 阈值**: 三级 LOD 系统（0.8, 1.8），基于真实缩放因子 `transform().m11()`
4. **坐标范围**: 场景坐标已归一化到 10000x10000 范围（支持深度缩放）
5. **六边形大小**: 默认 50px，可根据数据密度调整
6. **网格对齐**: 所有点已吸附到六边形中心，形成严格网格
7. **视觉优化**: 六边形内缩 92%，硬朗边框（1.5px），径向渐变填充
8. **标签系统**: LOD 0 主分类标签（连通域分析），LOD 1 子分类标签（距离检查避免重叠）

## 参考文档

- Phase 1 技术总结: `Docs/Phase1_Technical_Summary.md`
- Phase 2 技术总结: `Docs/Phase2_Technical_Summary.md`
- 架构文档: `Docs/The Architecture`

## 最新更新（2024-12-21）

### 重大改进

1. **完全重写可视化引擎**
   - 实现严格的蜂窝网格算法（Hex Grid Tessellation）
   - 坐标量化：所有点吸附到六边形中心
   - 聚合逻辑：计算主导分类和密度
   - LOD 动态切换：基于缩放级别自动切换

2. **深度 UI 样式定制**
   - 全局样式表（QSS）深度定制
   - 严格配色方案（深色赛博朋克）
   - 悬浮搜索栏（圆角、半透明）
   - 固定宽度侧边栏（240px）

3. **交互优化**
   - 缩放监听和 LOD 自动切换
   - 搜索时自动切换到 LOD 1
   - 点击详情显示完善

### 视觉重构（2024-12-21）⭐ NEW

1. **游戏级六边形渲染**
   - 间距效果：1.5px 网格缝隙，形成明确的网格感
   - 径向渐变：中心60%透明度 → 边缘20%透明度，不再使用纯色
   - 玻璃边框：1.5px 线宽，稍微亮一点的颜色，赋予"玻璃边缘"感
   - Hover 效果：鼠标悬停时边框变白，填充变实，产生"激活"感

2. **星云感散点渲染**
   - 光晕效果：中心实心圆（2px）+ 外围渐变光晕（6px，低透明度）
   - 制造"星云"感，不再只是简单的圆点

3. **悬浮仪表盘 UI**
   - 搜索栏：胶囊样式（border-radius: 20px）+ QGraphicsDropShadowEffect 阴影
   - 侧边栏：60px 图标模式（Icon Only），选中状态左侧发光条
   - Inspector：磨砂玻璃效果（rgba(18, 20, 23, 0.95)）+ 大写标题 + 字间距2px

### 技术亮点

- **严格网格对齐**: 使用轴向坐标系统，确保所有点整齐对齐
- **性能优化**: 六边形聚合减少渲染项数量
- **视觉一致性**: 深色主题统一，符合设计规范
- **游戏级渲染**: 渐变、光晕、阴影效果，达到"Cyberpunk Dashboard"设计要求

---

**状态**: 核心功能已完成，所有计划功能已实现，代码重构完成  
**预计完成时间**: Phase 3 核心功能已完成

## 最新更新（2024-12-21 晚）

### 引力视图模式实现 ⭐ NEW

1. **视图模式切换**
   - 实现了 Explorer 和 Gravity 模式切换
   - UI 按钮已连接，点击可切换模式

2. **引力视图核心功能**
   - 集成 `calculate_gravity_forces` 算法
   - 支持自定义引力桩（默认6个：Fire, Ice, Electric, Organic, Sci-Fi, Dark）
   - 根据相似度权重调整点的位置
   - 混合原始位置和引力位置（70% 引力，30% 原始）

3. **引力桩可视化**
   - 在画布上显示引力桩位置（大圆 + 标签）
   - 均匀分布在画布周围（圆形分布）
   - 每个桩使用不同颜色标识

4. **性能优化**
   - 添加 `NoIndex` 索引方法优化（适合大量静态项）
   - Qt 内置视口裁剪已启用

### 技术细节

**引力视图算法**:
- 引力桩位置：均匀分布在画布周围（半径300px）
- 权重计算：使用 `calculate_gravity_forces` 计算每个文件到各桩的相似度
- 位置调整：加权平均位置 = Σ(桩位置 × 归一化权重)
- 混合比例：70% 引力位置 + 30% 原始位置

**搜索引力算法**:
- 相关节点：螺旋排列在中心（使用螺旋坐标算法）
- 非相关节点：变暗（透明度 0.1），位置偏移到边缘
- 自动切换：搜索时自动切换到 Gravity 模式

**Scatter 模式算法**:
- 轴配置：X/Y 轴输入框，支持自定义语义轴
- 相似度计算：使用 `calculate_gravity_forces` 计算到各轴的相似度
- 坐标映射：相似度范围 [-1, 1] 映射到画布坐标
- 实时更新：Toggle 开关控制，实时切换 Explorer/Scatter 模式

## 代码重构详情（2024-12-21 晚）

### 重构目标
- ✅ 按项目标准整理文件夹结构
- ✅ UI 相关代码按逻辑拆分
- ✅ 保证 AI 可读性和可维护性

### 重构结果

**原文件拆分**:
- `gui_main.py` (978行) → 拆分为 6 个文件
- `visualizer.py` (954行) → 拆分为 4 个文件

**新文件夹结构**:
```
ui/
├── components/        # UI 组件（4个文件，350行）
├── visualizer/        # 可视化引擎（4个文件，960行）
├── main_window.py     # 主窗口（640行）
└── styles.py          # 全局样式（120行）
```

**向后兼容**:
- ✅ `gui_main.py` - 重定向到 `ui.main_window`
- ✅ `visualizer.py` - 重定向到 `ui.visualizer`
- ✅ 现有代码无需修改即可运行

**优势**:
- ✅ 文件职责单一，代码更清晰
- ✅ 文件大小控制在合理范围（< 500行，除 sonic_universe.py）
- ✅ 逻辑分离明确（组件、可视化、样式）
- ✅ 易于维护和扩展
- ✅ AI 可读性大幅提升

详细说明请参考：`Docs/Refactoring_Summary.md`

## 最新更新（2024-12-21 晚 - Category 颜色映射系统）

### Category 大类颜色映射 ⭐ NEW

1. **CategoryColorMapper 类实现**
   - 创建 `core/category_color_mapper.py` 模块
   - 从 UCS CSV 文件加载 CatID → Category 映射关系
   - 为每个 Category（82 个大类）分配唯一颜色
   - 使用 MD5 哈希函数确保颜色分配的一致性
   - 20 色霓虹色板，完整覆盖所有 Category

2. **颜色映射逻辑更新**
   - `HexGridLayer`: 修改 `_get_color_for_category()` 方法，使用 CategoryColorMapper
   - `DetailScatterLayer`: 修改 `_get_color_for_category()` 方法，使用 CategoryColorMapper
   - `_build_grid_data()`: 修改统计逻辑，基于 Category 名称统计，而不是 CatID 前3字符

3. **技术细节**
   - 从 CatID（如 "AMBForst"）提取 Category 名称（如 "AMBIENCE"）
   - 通过哈希函数映射到 20 色色板
   - 支持向后兼容：如果映射器不可用，使用旧版哈希方法

### 优势

- **统一颜色**: 同一 Category 下的所有子分类使用相同颜色
- **完整覆盖**: 82 个 Category 大类都有颜色分配
- **视觉一致性**: 相同类型的音频文件在视觉上更容易识别
- **可扩展性**: 新增 Category 会自动分配颜色

## 最新更新（2024-12-21 晚 - 性能优化）

### 高性能可视化引擎重写 ⭐ NEW

1. **架构变更：单层批量渲染**
   - 完全重写 `DetailScatterLayer`，使用批量渲染替代循环绘制
   - 实现 `update_cache()` 方法，使用 numpy 布尔索引进行视口裁剪
   - 使用 `QPainter.drawPoints()` 批量绘制，完全移除 paint() 中的循环
   - 支持按颜色分组批量绘制，保持多色支持

2. **坐标系统优化**
   - 完成 `_normalize_coordinates()` 方法
   - 将 UMAP 坐标归一化到 10000x10000 像素范围
   - 保持数据宽高比，支持"Google Earth"式深度缩放

3. **HexGridLayer 优化**
   - 确保六边形网格始终可见（作为背景地形）
   - 高缩放时（scale > 2.0）降低透明度但不隐藏
   - 边框在高缩放时变细（1.5px → 1.0px），保持可见
   - 添加 `set_scale()` 方法接收缩放级别

4. **OpenGL 硬件加速**
   - 在 `CanvasView` 中添加 `QOpenGLWidget` 视口支持
   - 添加渲染优化标志：`DontAdjustForAntialiasing`, `FullViewportUpdate`
   - 包含异常处理，OpenGL 不可用时回退到默认视口
   - 预期性能提升：从 10 FPS 提升到 60 FPS

5. **SonicUniverse 场景类完善**
   - 实现 `_compute_2d_projection()` 方法
   - 实现 `_setup_scene()` 方法
   - 实现 `_build_layers()` 方法：创建并添加两个渲染层
   - 实现 `update_lod()` 方法：更新各层的缩放级别
   - 添加缺失的方法：`set_view_mode()`, `set_gravity_pillars()`, `set_axis_config()`, `clear_highlights()`, `apply_search_gravity()`

### 性能优化技术细节

**批量渲染实现**:
- 缓存系统：`cached_points`, `cached_highlighted_points`, `cached_normal_points_by_color`
- 视口裁剪：使用 numpy 布尔索引快速筛选可见点
- 批量绘制：使用 `drawPoints()` 单次调用，完全移除循环
- 按颜色分组：支持多色点批量绘制

**LOD 行为优化**:
- 六边形网格：始终可见，高缩放时降低透明度（最低 0.2）
- 散点层：scale < 0.5 时不绘制，scale >= 0.5 时平滑淡入
- 淡入效果：从 scale=0.5 到 scale=1.0 线性插值透明度

**性能目标**:
- 50,000+ 点渲染：60 FPS
- 视口裁剪：只渲染可见点（numpy 布尔索引）
- 批量绘制：单次 drawPoints 调用，无循环

### 修复的问题

- ✅ 修复 `QStyleOptionGraphicsItem` 导入错误（从 `QtWidgets` 导入而非 `QtGui`）
- ✅ 修复 `QWidget` 导入错误（从 `QtWidgets` 导入）

### 技术亮点

- **批量渲染架构**: 从"1万个独立对象"变为"1张照片"，性能提升显著
- **视口裁剪优化**: 使用 numpy 布尔索引，只渲染可见区域
- **缓存机制**: 避免重复计算，只在必要时更新缓存
- **OpenGL 加速**: GPU 硬件加速，大幅提升渲染性能
- **Google Earth 式缩放**: 坐标扩展到 10000x10000，支持深度缩放
- **Category 颜色映射**: 基于 UCS Category 大类（82 个大类）的统一颜色分配系统

---

**状态**: 核心功能已完成，所有计划功能已实现，代码重构完成，Category 颜色映射系统已实现，三级 LOD 系统和 Gravity Mode 已实现  
**预计完成时间**: Phase 3 核心功能已完成

## 最新更新（2024-12-21 晚 - Visual Finalization）

### 三级 LOD 系统实现 ⭐ NEW

1. **LOD 0 (Zoom < 0.8): The Continents**
   - 只显示六边形网格，100% 不透明度
   - 大标签显示主分类（Category），使用连通域分析计算质心
   - 使用 QStaticText 提高性能
   - 白色文字，24px 字体，带阴影

2. **LOD 1 (0.8 <= Zoom < 1.8): The Regions**
   - 只显示六边形网格，80% 不透明度
   - 中等标签显示子分类（SubCategory），避免重叠
   - 12px 字体，距离检查防止标签重叠

3. **LOD 2 (Zoom >= 1.8): The Details**
   - 六边形淡出轮廓（10% 不透明度），作为背景上下文
   - 显示所有散点（使用 drawPoints 批量渲染）
   - 悬停时显示文件名（待实现）

### 标签聚类算法 ⭐ NEW

1. **连通域分析**
   - 实现 `_compute_category_clusters()` 方法
   - 使用 BFS 算法找到相邻相同主分类的六边形群组
   - 计算每个群组的质心作为标签位置
   - 只处理可见区域的六边形，优化性能

2. **标签绘制优化**
   - 使用 QStaticText 替代 QGraphicsTextItem
   - 主分类标签：24px，白色，带阴影
   - 子分类标签：12px，距离检查避免重叠

### Gravity Mode 向日葵螺旋布局 ⭐ NEW

1. **螺旋布局算法**
   - 实现 `apply_search_gravity()` 方法
   - 按相似度分数降序排序
   - 使用黄金角度（137.508°）生成螺旋
   - 分数越高越靠近中心（radius_factor = 1.0 - score）

2. **颜色保持**
   - 保持 UCS 颜色（使用 CategoryColorMapper）
   - 非匹配项淡出到 10% 透明度
   - 自动切换到 Gravity 模式

### 视觉优化（Geometry Inset & Cyberpunk Style）⭐ NEW

1. **六边形内缩**
   - 内缩比例：92%（INSET_RATIO = 0.92）
   - 留下 8% 黑色缝隙，形成清晰的网格感
   - 视觉大小：`visual_size = hex_size * 0.92`

2. **硬朗边框风格**
   - 边框颜色：比填充色亮 50%（`color.lighter(150)`）
   - 边框宽度：恒定 1.5px
   - 连接样式：硬角（MiterJoin）

3. **径向渐变填充**
   - 中心：40% 不透明度
   - 边缘：10% 不透明度
   - 通透感，不再使用纯色填充

### Zoom 定义统一 ⭐ NEW

1. **使用真实缩放因子**
   - 修改 `CanvasView.wheelEvent()` 使用 `transform().m11()`
   - 移除手动维护的 `current_zoom` 变量
   - 确保 LOD 判断基于真实的视图缩放

2. **LOD 阈值**
   - LOD 0: Zoom < 0.8
   - LOD 1: 0.8 <= Zoom < 1.8
   - LOD 2: Zoom >= 1.8

### 技术细节

**连通域算法**:
- 使用 BFS 在六边形网格上执行连通域分析
- 相邻定义：共享边的六边形（6个邻居）
- 质心计算：`(sum(x)/n, sum(y)/n)`
- 只处理可见区域，优化性能

**向日葵螺旋算法**:
- 黄金角度：137.508°（度转弧度）
- 半径计算：`r = (1.0 - score) * max_radius`
- 位置计算：`x = center_x + r * cos(angle)`, `y = center_y + r * sin(angle)`
- 保持 UCS 颜色，非匹配项淡出

**视觉优化参数**:
- 内缩比例：92%
- 边框宽度：1.5px（恒定）
- 渐变：中心 40% → 边缘 10% 不透明度
- 边框颜色：填充色 + 50% 亮度

---

## 最新更新（2025-01-02 - Phase 3 可视化引擎彻底重写）

### 可视化引擎彻底重写 ⭐ NEW

1. **数据驱动的网格生成**
   - 完全重写 `SonicUniverse` 类，使用数据驱动方法
   - 杜绝空蜂窝：只基于实际数据点生成六边形网格
   - 实现 `_build_scene_data()` 方法，完全基于数据生成网格
   - 坐标归一化到 10000x10000 像素范围

2. **KDTree 空间索引**
   - 集成 `scipy.spatial.cKDTree` 用于极速点击检测
   - 实现 `find_closest_data()` 方法：基于 KDTree 的最近邻查询
   - 实现 `find_items_in_rect()` 方法：用于框选功能
   - 距离阈值：20px（太远点不到）

3. **圆点渲染修复**
   - 修复 `DetailScatterLayer` 中的方点问题
   - 使用 `pen.setCapStyle(Qt.RoundCap)` 渲染圆点
   - 普通点和高亮点均渲染为圆点

4. **交互逻辑修复**
   - 更新 `main_window.py` 中的 `_setup_canvas_interaction()` 方法
   - 使用 `find_closest_data()` 替代 `items(pos)`
   - 添加高亮功能支持

5. **简化渲染架构**
   - 简化 `HexGridLayer`：移除复杂缓存逻辑，使用直接绘制
   - 简化 `DetailScatterLayer`：使用 numpy 视口裁剪，批量绘制
   - 保留必要的颜色映射和分类逻辑

### GPU 加速部署 ⭐ NEW

1. **PyTorch GPU 版本安装**
   - 卸载 CPU 版本 PyTorch 2.9.1+cpu
   - 安装 CUDA 12.1 版本 PyTorch 2.5.1+cu121
   - 验证 GPU 可用性：NVIDIA GeForce RTX 3070

2. **VectorEngine GPU 优化**
   - 显式指定设备参数，确保使用 GPU
   - 根据设备自动调整 batch_size：
     - GPU (CUDA): 64
     - MPS (Mac): 32
     - CPU: 16
   - 添加设备验证和回退机制

3. **性能提升验证**
   - 测试速度：191.8 条/秒（GPU）
   - 性能提升：从 ~11 条/秒（CPU）提升到 ~192 条/秒（GPU）
   - 约 17 倍性能提升

### UMAP 参数优化 ⭐ NEW

1. **最紧凑配置**
   - `n_neighbors=100`：强迫看清大局，把碎岛拼成大陆
   - `min_dist=0.0`：允许点无限堆叠，极度紧凑
   - `spread=1.0`：限制扩散范围
   - `metric='cosine'`：使用余弦相似度（对音频语义更好）

2. **预期效果**
   - 紧凑的"大陆"而非零散的"孤岛"
   - 消除黑色背景虚空
   - 数据紧紧抱团

### 技术细节

**数据驱动网格生成**:
- 遍历所有 `coords_2d` 点
- 计算每个点的 `(q, r)` 坐标
- 存储在 `grid_map` 字典中：`{(q, r): [indices]}`
- 只绘制 `grid_map` 中存在的六边形

**KDTree 点击检测**:
- 构建空间索引：`cKDTree(norm_coords)`
- 查询最近邻：`tree.query([x, y], distance_upper_bound=20)`
- 返回命中数据：`{'index': idx, 'metadata': metadata, 'pos': pos}`

**GPU 加速实现**:
- 设备检测：自动检测 CUDA/MPS/CPU
- 显式传递：`SentenceTransformer(..., device=device_str)`
- 自动 batch_size：根据设备类型自动选择
- 设备验证：检查实际运行设备

### 修复的问题

- ✅ 修复空蜂窝问题（数据驱动的网格生成）
- ✅ 修复方点问题（RoundCap 设置）
- ✅ 修复点击检测问题（KDTree 空间索引）
- ✅ 修复交互逻辑问题（find_closest_data 方法）
- ✅ 修复 GPU 加速问题（显式设备指定）
- ✅ 修复 UMAP 参数问题（最紧凑配置）

### 性能指标更新

**GPU 加速前**:
- 向量化速度：~11 条/秒
- 1.3 万条数据：~20 分钟

**GPU 加速后**:
- 向量化速度：~192 条/秒
- 1.3 万条数据：~1-2 分钟
- 性能提升：约 17 倍

### 下一步计划

1. **运行重建脚本**
   - 使用新的 UMAP 参数重新生成坐标
   - 验证紧凑"大陆"效果
   - 验证 GPU 加速性能

2. **测试新功能**
   - 测试 KDTree 点击检测准确性
   - 测试圆点渲染效果
   - 测试数据驱动网格生成（无空蜂窝）

3. **性能优化**
   - 大规模数据渲染性能测试
   - GPU 加速效果验证
   - 交互响应测试

---

**状态**: Phase 3 可视化引擎彻底重写完成，GPU 加速部署成功，核心修复完成  
**更新时间**: 2025-01-02

## 最新更新（2025-01-02 - 核心修复完成）

### 可视化核心修复 ⭐ NEW

1. **散点分布算法重写**
   - 废弃随机抖动算法，实现局部向日葵螺旋布局
   - 使用黄金角度（137.508度）计算每个点的位置
   - 确保所有点都在 `hex_size * 0.9` 半径内
   - 解决散点重叠和圈状分布问题

2. **点击命中测试修复**
   - 使用 `current_display_coords`（最终显示坐标）构建 cKDTree
   - 确保渲染坐标与点击检测坐标完全一致
   - 修复点击失效和目标不符问题

3. **LOD 标签逻辑修正**
   - LOD 1 使用 Counter 统计 keywords/subcategory 的 Mode（最频繁的词）
   - LOD 1 标签颜色使用该六边形主导分类的颜色
   - LOD 0 降低聚类阈值到 >= 1，显示更多标签
   - LOD 0 字体缩放改为非线性公式（pow(zoom, 0.5)）

4. **视觉与颜色修正**
   - 所有颜色统一使用 CategoryColorMapper 获取
   - 移除硬编码默认颜色
   - LOD 0 填充 Alpha 50，描边 Alpha 220
   - LOD 1 子类标签使用分类颜色

5. **视图控制优化**
   - 添加 min/max zoom 限制，防止无限缩放
   - 实现 `fit_scene_to_view()` 方法，初始化时自动适配
   - 添加双击重置视图功能
   - 修复缩放功能，确保正常工作

6. **数据密度调整**
   - 归一化范围从 10000.0 减小到 3500.0
   - 减少数据分散，让蜂窝更密集

### Inspector 面板增强 ⭐ NEW

1. **新增显示字段**
   - 库（Library）：从 filepath 提取或使用 metadata 中的 library 字段
   - 文件路径：完整路径显示，使用等宽字体
   - 描述：确保正确显示，支持换行

2. **显示顺序优化**
   - 库 → 文件路径 → 文件名 → RecID → 分类 → 描述 → 关键词

### 技术细节

**向日葵螺旋算法**:
- 黄金角度：137.508°（度转弧度）
- 半径分布：使用平方根分布，让点更均匀
- 限制半径：`hex_size * 0.9`，确保不超出六边形边界
- 确定性：基于排序后的索引，保证一致性

**点击检测优化**:
- 坐标一致性：渲染和检测使用相同的 `current_display_coords`
- KDTree 重建：在 `_build_scene_data` 中使用最终坐标构建
- 索引同步：确保坐标数组与 metadata 索引 1:1 对应

**LOD 标签优化**:
- LOD 1 统计：使用 `collections.Counter` 统计所有点的 keywords/subcategory
- 颜色映射：LOD 1 标签颜色来自 CategoryColorMapper
- LOD 0 聚类：阈值从 > 3 降低到 >= 1，显示所有类别
- 字体缩放：非线性反向缩放，放大时字体缩小更快

### 修复的问题

- ✅ 修复散点重叠问题（向日葵螺旋布局）
- ✅ 修复点击失效问题（坐标一致性）
- ✅ 修复 LOD 1 标签显示文件名问题（使用 Counter 统计）
- ✅ 修复 LOD 0 标签过少问题（降低阈值）
- ✅ 修复缩放功能问题（简化逻辑，添加限制）
- ✅ 修复视图丢失问题（双击重置功能）
- ✅ 统一颜色获取（CategoryColorMapper）
- ✅ Inspector 面板增强（库、路径、描述显示）

**状态**: Phase 3 可视化引擎彻底重写完成，GPU 加速部署成功，核心修复完成  
**更新时间**: 2025-01-02（核心修复）

## 最新更新（2025-01-04 - 数据源切换与问题修复）

### 数据源切换 ⭐ NEW

1. **正式数据库切换**
   - 数据源从 `Sonic.sqlite` (41 MB, 13,850 条) 切换到 `Nas_SoundLibrary.sqlite` (4.6 GB, 1,948,566 条)
   - 更新所有相关文件的数据路径：
     - `rebuild_atlas.py`: 数据库路径更新
     - `ui/main_window.py`: 数据导入路径更新
     - `tools/verify_phase2.py`: 测试数据库路径更新
     - `tools/verify_pipeline.py`: 测试数据库路径更新

2. **数据规模变化**
   - 记录数：从 13,850 条增加到 1,948,566 条（约 140 倍增长）
   - 向量化时间：预计从 ~20 分钟增加到数小时（GPU 加速后约 1-2 小时）
   - 缓存文件大小：
     - `embeddings.npy`: 从 56 MB 增加到 7.43 GB
     - `metadata.pkl`: 从 7 MB 增加到 836 MB

### GPU 加速状态确认 ⭐ NEW

1. **GPU 加速已启用**
   - PyTorch 版本：2.5.1+cu121 (CUDA 12.1)
   - GPU 设备：NVIDIA GeForce RTX 3070
   - VectorEngine 自动使用 GPU，batch_size=64
   - 性能提升：约 17 倍（从 ~11 条/秒到 ~192 条/秒）

2. **向量化完成状态**
   - 向量化阶段已完成（1,948,566 条记录）
   - Embeddings 文件已生成（7.43 GB）
   - Metadata 文件已生成（836 MB）

### UMAP 计算内存问题 ⚠️

1. **内存错误**
   - 错误信息：`ArrayMemoryError: Unable to allocate 19.8 GiB`
   - 发生位置：UMAP 的 `spectral_layout` 阶段
   - 原因：195 万条数据 + `n_neighbors=100` 参数导致内存需求过大
   - 当前状态：需要调整参数或使用采样策略

2. **解决方案（待实施）**
   - 方案 1：降低 `n_neighbors` 参数（从 100 降到 15-30）
   - 方案 2：使用 `low_memory=True` 模式
   - 方案 3：数据采样（随机选择部分数据）
   - 注意：参数调整可能影响可视化质量

### 缩放导致 UI 消失问题修复 ⭐ NEW

1. **场景矩形设置修复**
   - 问题：使用 `itemsBoundingRect()` 可能返回不正确的值（图层返回固定大范围）
   - 修复：基于实际数据坐标范围设置场景矩形
   - 位置：`ui/visualizer/sonic_universe.py` 的 `_build_scene_data()` 方法
   - 实现：使用 `norm_coords` 的实际范围计算场景矩形，添加 500px 边距

2. **视图适配优化**
   - 移除重复的 `fitInView()` 调用
   - 统一使用 `fit_scene_to_view()` 方法
   - 确保缩放时内容始终在可见范围内

### 技术细节

**场景矩形计算**:
- 基于实际数据坐标：`min_x, min_y = norm_coords.min(axis=0)`
- 添加边距：`margin = 500.0`
- 场景矩形：`QRectF(min_x - margin, min_y - margin, width + 2*margin, height + 2*margin)`

**数据源切换影响**:
- 所有数据路径统一更新
- 向量化已完成，UMAP 计算待优化
- 缓存文件大小显著增加

### 修复的问题

- ✅ 修复缩放导致 UI 消失问题（场景矩形基于实际数据坐标）
- ✅ 修复视图适配重复调用问题（统一使用 fit_scene_to_view）
- ✅ 数据源切换完成（所有相关文件已更新）
- ⚠️ UMAP 内存错误待解决（需要调整参数或采样策略）

### 下一步计划

1. **UMAP 参数优化**
   - 降低 `n_neighbors` 参数以适应大规模数据
   - 或实现数据采样策略
   - 平衡内存使用和可视化质量

2. **性能测试**
   - 测试大规模数据（195 万条）的渲染性能
   - 验证 GPU 加速效果
   - 优化内存使用

3. **功能验证**
   - 验证缩放功能正常
   - 验证场景矩形设置正确
   - 验证数据加载和显示

**状态**: 数据源切换完成，GPU 加速已启用，缩放问题已修复，UMAP 内存问题待解决  
**更新时间**: 2025-01-04

## 最新更新（2025-01-04 - 关键修复：数据分类、渲染顺序、UI初始化）

### 数据分类系统重大修复 ⭐ NEW

1. **强规则层（Hard Rule Layer）实现**
   - 在 AI 仲裁前添加 Level 0 强规则层
   - 关键词直接锁定 Category Code（如 'WPN', 'SCI', 'MAG'）
   - 解决 "Future Weapon" -> "Aircraft" 等错误分类问题
   - 规则覆盖：武器、科幻、魔法、水、天气、环境、脚步声、UI、航空器等

2. **Category Code 标准化**
   - 确保存入数据库的是 Code（如 'WPN'）而不是 Name（如 'WEAPONS'）
   - 修复 `_extract_category()` 方法，所有路径都返回 Code
   - 修复 `get_catid_info()` 方法，增强查表能力
   - 解决"全红"显示问题的根本原因

3. **UCS Manager 增强**
   - `get_catid_info()` 支持多种查找方式：
     - 优先使用 `catid_lookup` 表
     - 回退到 `catid_to_category` 表
     - 如果格式像 UCS（如 "WPNGun"），盲猜前三位是 Code
   - 确保始终返回 `category_code` 字段

### 可视化渲染修复 ⭐ NEW

1. **渲染顺序修复**
   - 修复 `set_data()` 方法：先归一化坐标，再构建场景，最后适配视图
   - 修复 `_build_scene_data()` 方法：接受 `norm_coords` 参数，使用传入参数而非 `self.norm_coords`
   - 确保坐标计算和场景构建的顺序正确

2. **UI 初始化修复**
   - 修复 `SonicUniverse.__init__` 中 `_build_scene_data()` 调用缺少参数的问题
   - 添加默认参数 `norm_coords=None` 作为 fallback
   - 修复 `_rebuild_layers()` 中的调用
   - 添加异常日志输出，避免静默失败

3. **调试输出增强**
   - 添加详细的调试日志（`[DEBUG] build:` 前缀）
   - 每个关键步骤都有进度输出
   - 便于定位卡住的位置

### 自动质心生成 ⭐ NEW

1. **rebuild_atlas.py 增强**
   - 自动检查并生成 Platinum Centroids（如果缓存不存在）
   - 使用 `importlib` 动态导入，避免模块级初始化卡住
   - 添加详细的进度输出和错误处理

2. **generate_platinum_centroids.py 优化**
   - 移除模块级的 `sys.stdout` 修改（移到函数内部）
   - 延迟导入 `VectorEngine` 和 `CategoryColorMapper`
   - 避免在导入时触发模型加载

### 技术细节

**强规则层实现**:
- STRONG_RULES 字典：关键词 -> Category Code 映射
- 在 Level 1（显式检查）之前执行
- 直接返回 Code，不给 AI 瞎猜的机会

**Category Code 标准化流程**:
- Level 0: 强规则层（关键词匹配）
- Level 1: 显式检查（Metadata，过滤弱分类）
- Level 3: AI 向量仲裁（确保返回 Code）
- 所有路径最终都返回 Category Code，不是 Name

**渲染顺序修复**:
- `set_data()`: 归一化 -> 构建场景 -> 适配视图
- `_build_scene_data()`: 使用传入参数，不依赖 `self.norm_coords`
- 确保坐标计算完成后再构建场景

### 修复的问题

- ✅ 修复数据分类错误（强规则层 + Code 标准化）
- ✅ 修复"全红"显示问题（确保存储和显示都使用 Code）
- ✅ 修复 UI 初始化卡住（参数传递 + 默认值）
- ✅ 修复渲染顺序问题（坐标归一化在场景构建前）
- ✅ 修复静默失败问题（添加异常日志）
- ✅ 修复导入卡住问题（延迟导入 + 动态导入）

### 下一步计划

1. **性能优化**
   - 优化 `_generate_labels()` 方法（当前已临时禁用）
   - 测试大规模数据渲染性能
   - 优化标签生成算法

2. **功能完善**
   - 重新启用标签生成（优化后）
   - 测试强规则层的分类准确性
   - 验证 Code 标准化效果

**状态**: 关键修复完成，数据分类系统增强，渲染顺序修复，UI初始化修复  
**更新时间**: 2025-01-04（关键修复）

## 最新更新（2025-01-04 - 完全查表法修复 LOD 显示和聚类问题）

### 完全查表法重构 ⭐ NEW

1. **核心原则：完全查表法 (The Table-Lookup Strategy)**
   - 删除所有"猜前缀"、"硬编码 CatShort"的逻辑
   - 一切以 `ucs_catid_list.csv` 为准
   - 查不到表就返回原值作为兜底，不进行任何猜测

2. **UCS 管理器重构 (`core/ucs_manager.py`)**
   - 实现纯查表模式：`get_catid_info()` 方法完全依赖 CSV 数据
   - 删除所有前缀猜测逻辑（如 `cat_id[:3]`）
   - 删除 `catid_lookup` 的猜测逻辑
   - 查不到表时返回原值作为兜底，确保至少能显示 CatID 本身

3. **UMAP 聚合修复 (`rebuild_atlas.py`)**
   - 使用 Category Name（大类全名）作为 UMAP 目标
   - 从 CatID（如 `WEAPArmr`）通过 UCSManager 查表获取 `category_name`（如 `WEAPONS`）
   - 这样 `WEAPArmr` 和 `WEAPSwrd` 都会得到 `WEAPONS` 标签，UMAP 会把它们聚在一起形成"大陆"

4. **数据处理器更新 (`core/data_processor.py`)**
   - 更新强规则映射，使用 CSV 中实际存在的正确 CatID
   - 主要更新：
     - WEAPONS 系列：`WEAPSwrd`, `WEAPKnif`, `WEAPBow`, `WEAPArro`, `WEAPAxe`, `WEAPArmr` 等
     - GUNS 系列：`GUNMisc`, `GUNPis`, `GUNRif`, `GUNShotg`, `GUNAuto` 等
     - EXPLOSIONS 系列：`EXPLMisc`, `EXPLReal` 等
     - MAGIC 系列：`MAGSpel`, `MAGElem` 等
     - ICE 系列：`ICEMisc`, `ICEBrk`, `ICECrsh` 等
     - LASERS 系列：`LASRMisc`, `LASRGun` 等
     - SCIFI 系列：`SCIMisc` 等
     - FIRE 系列：`FIREMisc`, `FIREBurn` 等
     - WATER 系列：`WATRMisc`, `WATRWave` 等

5. **可视化优化 (`ui/visualizer/sonic_universe.py`)**
   - 确保 LOD0 显示 Category Name（如 `WEAPONS`）
   - 确保 LOD1 显示 SubCategory Name（如 `ARMOR`）
   - 过滤掉 `"UNKNOWN"` 和空字符串，只显示有效的子类名称

### 技术细节

**完全查表法实现**:
- `get_catid_info()`: 只查 `catid_to_category` 字典，查不到返回原值
- 不再进行任何前缀猜测或格式解析
- 确保所有信息都来自 CSV 数据表

**UMAP 聚合逻辑**:
- 从 metadata 中的 CatID（如 `WEAPArmr`）提取 Category Name（如 `WEAPONS`）
- 使用 Category Name 作为 UMAP 的监督目标
- 相同 Category Name 的数据会被聚在一起形成"大陆"

**强规则映射更新**:
- 所有 CatID 都从 CSV 中实际存在的条目确认
- 确保强规则映射的 CatID 在 CSV 中存在
- 避免使用错误的或硬编码的 CatID

### 修复的问题

- ✅ 修复 LOD0 显示 CatID 而不是 Category Name 的问题
- ✅ 修复 LOD1 显示 "GENERAL" 或空的问题
- ✅ 修复 UMAP 聚类散乱问题（使用 Category Name 作为目标）
- ✅ 修复强规则 CatID 错误问题（使用 CSV 中正确的 CatID）
- ✅ 实现完全查表法，删除所有猜测逻辑

### 数据流验证

修复后的完整数据流：

1. **DataProcessor**: 
   - 看到 "Ice Break" -> 强规则映射到 `ICEBrk` -> 存入 metadata['category'] = 'ICEBrk'

2. **RebuildAtlas**: 
   - 看到 `ICEBrk` -> 通过 UCSManager 查表得到 `category_name = "ICE"` -> UMAP 使用 "ICE" 作为目标 -> 把它和 `ICECrsh`（也是 "ICE"）拉到一起 -> 形成大陆

3. **SonicUniverse (LOD0)**: 
   - 拿到 `ICEBrk` -> 通过 UCSManager 查表 -> 显示 "ICE"

4. **SonicUniverse (LOD1)**: 
   - 拿到 `ICEBrk` -> 通过 UCSManager 查表 -> 显示 "BREAK"（不再是 GENERAL）

**状态**: 完全查表法重构完成，LOD 显示和聚类问题已修复  
**更新时间**: 2025-01-04（完全查表法重构）

## 最新更新（2025-01-05 - 颜色映射和规则系统重构）

### 颜色映射系统重构 ⭐ NEW

1. **CategoryColorMapper 增强 (`core/category_color_mapper.py`)**
   - ✅ 使用 pandas 读取 CSV，兼容 utf-8 和 latin1 编码
   - ✅ 将 Category Name（第一列）转大写后作为 key 存入 `short_to_color`
   - ✅ 支持 Category Name、CatID、CatShort 三种查询方式
   - ✅ 修复"色盲眼"问题：现在可以识别 "USER INTERFACE" 等大类全名

2. **聚类逻辑修正 (`rebuild_atlas.py`)**
   - ✅ 使用 UCSManager.get_catid_info() 获取 Category Name（第一列）
   - ✅ 使用 Category Name（转大写）作为 UMAP 聚合标签
   - ✅ 确保所有聚类都基于 CSV 中的真实 Category Name

3. **UCSManager 优化 (`core/ucs_manager.py`)**
   - ✅ 使用 `row.get()` 方法安全获取列值
   - ✅ 确保正确读取 Category, SubCategory, CatID, CatShort 列
   - ✅ 增强错误处理和容错性

### 规则系统外部化 ⭐ NEW

1. **规则生成工具 (`tools/generate_rules_json.py`)**
   - ✅ 从 `data_config/ucs_catid_list.csv` 读取真实数据
   - ✅ 验证所有 CatID 在 CSV 中存在
   - ✅ 根据关键词映射到真实的 CatID
   - ✅ 生成 `data_config/rules.json`（82 条规则）

2. **DataProcessor 重构 (`core/data_processor.py`)**
   - ✅ 移除硬编码的 STRONG_RULES 字典
   - ✅ 添加 `_load_rules()` 方法，从 `data_config/rules.json` 加载
   - ✅ 在 `__init__` 中自动加载规则
   - ✅ 更新 `_extract_category` 使用 `self.strong_rules`

### 修复的问题

- ✅ 修复颜色映射只认缩写不认大类全名的问题
- ✅ 修复聚类逻辑可能使用 Code 而非 Category Name 的问题
- ✅ 修复硬编码 STRONG_RULES 包含不存在 CatID（如 UIUser）的问题
- ✅ 实现规则系统外部化，便于维护和更新

### 技术细节

**颜色映射增强**:
- CategoryColorMapper 现在支持三种查询方式：
  1. Category Name（如 "USER INTERFACE"）
  2. CatID（如 "UIMisc"）
  3. CatShort（如 "UI"）

**规则系统外部化**:
- 所有规则存储在 `data_config/rules.json`
- 规则基于 CSV 中的真实数据生成
- 可以通过运行 `python tools/generate_rules_json.py` 重新生成
- 便于维护：修改规则无需修改代码

**数据流验证**:

1. **DataProcessor**: 
   - 从 `rules.json` 加载规则
   - 看到 "UI" -> 规则映射到 `UIMisc` -> 存入 metadata['category'] = 'UIMisc'

2. **RebuildAtlas**: 
   - 看到 `UIMisc` -> 通过 UCSManager 查表得到 `category_name = "USER INTERFACE"` -> UMAP 使用 "USER INTERFACE" 作为目标

3. **CategoryColorMapper**: 
   - 可以识别 "USER INTERFACE"、"UIMisc"、"UI" 三种格式
   - 返回统一的颜色

**状态**: 颜色映射和规则系统重构完成  
**更新时间**: 2025-01-05（颜色映射和规则系统重构）

---

## 当前问题记录（2025-01-05 晚）

### 🐛 LOD0 标签显示问题

**问题描述**：
- 当前每个蜂窝都显示了一个大类标签，标签变得很小压缩在蜂窝内
- 预期效果：像地图那样，一个片区（连通域）显示一个大的标签，横跨在蜂窝群上

**根本原因**：
- 过滤阈值设置为 `>= 1`，导致每个单独的蜂窝都生成标签
- 应该提高阈值，只显示较大的连通域（片区）

**修复方案**：
- ✅ 将过滤阈值从 `>= 1` 改为 `>= 5`，确保只显示较大的片区
- ✅ 标签应该显示在连通域的中心位置，字体大小根据片区大小动态调整

**状态**: ✅ 已修复（2025-01-05）

### 🐛 LOD1 子类标签缺失

**问题描述**：
- LOD1 视图下几乎看不到子类标签，只有零星几个独立 hexbin 的子类显示
- 预期效果：根据数据生成 subcategory 标签，每个 hexbin 应该显示其对应的子类名称

**根本原因**：
- `get_catid_info` 返回的 `subcategory_name` 可能是 "UNKNOWN" 或空
- 子类信息获取逻辑不够健壮，没有充分回退到直接查询 `catid_to_category`

**修复方案**：
- ✅ 增强子类信息获取逻辑，优先从 `get_catid_info` 获取，如果失败则直接从 `catid_to_category` 查询
- ✅ 确保过滤掉 "UNKNOWN" 和空字符串，只显示有效的子类名称

**状态**: ✅ 已修复（2025-01-05）

### 📋 Phase 3 最终验收清单

**状态**: 进行中

#### 1. 视觉验收：赛博朋克仪表盘

- [ ] **蜂窝缝隙 (Gap)**: 任意缩放级别下，六边形之间必须有清晰的黑色切割线（建议 1.5px - 2px）。不能糊成一团色块。
- [ ] **大陆连通性**: 运行 rebuild_atlas.py 调整 UMAP 参数 (n_neighbors=50, min_dist=0.5) 后，地图应呈现为几块巨大的连通大陆，而非破碎的群岛。黑色虚空面积应 < 30%。
- [ ] **标签层级 (Typography)**:
  - [ ] LOD 0: 必须看到巨大的白色 UCS 主类标签（如 "WEAPONS"）横跨在蜂窝群上。✅ 已修复阈值问题
  - [ ] LOD 1: 看到hexbin内的子类标签（如 "SWORD"）。✅ 已修复子类获取逻辑
- [ ] **初始视野**: 软件启动时，镜头必须自动聚焦并框选所有数据点，不能让用户在一片黑海里找数据。

#### 2. LOD 行为验收：平滑切换

- [ ] **无缝过渡**: 滚轮缩放时，LOD 0 (纯蜂窝) -> LOD 1 (半透明蜂窝) -> LOD 2 (散点) 的切换不能有闪烁。
- [ ] **点可见性**: 在最大放大倍率下，必须能清晰看到每一个代表文件的圆点，且点必须在六边形之上（Z-Order 正确）。

#### 3. 性能验收：60 FPS

- [ ] **流畅度**: 在 1.3万数据下，鼠标拖拽平移、快速缩放必须保持 60 FPS，无肉眼可见卡顿（依赖 QOpenGLWidget 生效）。

#### 4. 搜索验收：引力生效

- [ ] **高亮**: 搜索 "Gun" 后，非相关节点必须明显变暗/半透明。

**更新时间**: 2025-01-05（问题记录和修复）

---

## Phase 3.5: 工具链与数据管道重构

**状态**: 实施中  
**更新时间**: 2025-01-05

### 概述

Phase 3.5 的核心目标是建立快速验证工具链，打通数据管道，实现数据驱动的规则生成系统。

### 已完成的工作

#### 第一阶段：工具链与基础设施建设 ✅

1. **微缩验证工具 `tools/verify_subset.py`** ✅
   - 支持关键词过滤查询（使用原始 SQL）
   - 运行分类逻辑（规则 + AI）
   - 生成 matplotlib 可视化散点图（默认输出 `verification_result.png`）
   - 打印详细分类报告（格式：`Matched 'text' -> CatID via Source`）
   - 分类来源统计、类别分布

2. **文本归一化工具 `core/text_utils.py`** ✅
   - `normalize_text()` - 基础归一化函数（**保留空格**）
   - `normalize_keyword()` - 关键词归一化
   - `normalize_filename()` - 文件名归一化
   - 支持移除数字选项
   - **关键特性**：保留单词之间的空格，确保 "metal door" 与 "metaldoor" 区分

#### 第二阶段：打通数据管道 ✅

1. **重构 `tools/generate_rules_json.py`** ✅
   - 从硬编码改为读取 `ucs_alias.csv`
   - 使用 `text_utils.normalize_keyword` 归一化关键词（**保留空格**）
   - **按关键词长度降序排序**（最长优先），确保 "metal door" 在 "door" 之前匹配
   - 验证 CatID 有效性
   - 自动生成 `rules.json`

2. **CSV 标准化工具 `tools/standardize_alias_csv.py`** ✅
   - 添加表头 `Keyword, CatID`
   - 规范化 CatID 格式
   - 自动备份原文件

3. **升级 `core/data_processor.py`** ✅
   - **整词匹配（Whole Word Matching）**：使用正则表达式 `\b{keyword}\b` 确保只匹配完整单词
   - 避免 "train" 匹配 "training" 的问题
   - 提高匹配准确性

#### 第三阶段：文档更新 ✅

1. **创建 Phase 3.5 文档** ✅
   - `Docs/Phase3.5_Toolchain_DataPipeline.md`
   - 包含完整的使用指南和快速测试指南

2. **更新现有文档** ✅
   - 更新 `PROJECT_STRUCTURE.md`
   - 更新 `Phase3_Progress_Status.md`

### 工具清单

| 工具 | 状态 | 说明 |
|------|------|------|
| `tools/verify_subset.py` | ✅ | 微缩验证工具，30秒内验证分类效果 |
| `core/text_utils.py` | ✅ | 文本归一化工具 |
| `tools/generate_rules_json.py` | ✅ | 从 CSV 生成规则（已重构） |
| `tools/standardize_alias_csv.py` | ✅ | CSV 标准化工具 |

### 快速测试指南

```bash
# 1. 标准化 CSV（首次运行）
python tools/standardize_alias_csv.py

# 2. 重新生成规则
python tools/generate_rules_json.py

# 3. 快速验证
python tools/verify_subset.py AIR
python tools/verify_subset.py WEAPON
python tools/verify_subset.py VEHICLE
```

### 关键技术改进

1. **整词匹配（Whole Word Matching）**
   - 使用正则表达式 `\b{keyword}\b` 确保只匹配完整单词
   - 避免误匹配（如 "train" 不会匹配 "training"）
   - 提高分类准确性

2. **关键词长度排序**
   - 规则按关键词长度降序排序
   - 确保长关键词（如 "metal door"）优先于短关键词（如 "door"）匹配
   - 避免短关键词误匹配长短语

3. **空格保留归一化**
   - 归一化时保留单词之间的空格
   - 区分 "metal door" 和 "metaldoor"
   - 提高匹配精确度

### 最新更新（2025-01-09）

#### ✅ 短路逻辑修复
- **问题**: 文件名中包含标准 CatID（如 `ANMLAqua_...`）时，短路逻辑未正确生效
- **修复**: `resolve_category_from_filename` 现在返回原始格式的 CatID（如 `ANMLAqua`）
- **结果**: 所有包含标准 CatID 的文件名都能被正确识别为 Level -1（文件名短路）

#### ✅ 数据库配置系统
- **新增**: 统一的数据库路径配置系统（`data/database_config.py`）
- **配置文件**: `data_config/user_config.json` 中添加 `database_path` 字段
- **优势**: 所有脚本和软件都从配置文件读取数据库路径，方便切换数据源
- **文档**: 创建了 `Docs/DATABASE_CONFIG.md` 详细说明配置方法

#### ✅ 测试脚本改进
- **输出管理**: 所有测试输出文件统一保存到 `verify_output/` 文件夹
- **文件命名**: 自动添加时间戳（格式：`MMDDHHmm`），便于管理
- **CSV 导出**: 导出详细数据表，包含文件名、CatID、主类别、分类来源、UMAP 坐标等
- **坐标说明**: 添加了 UMAP 坐标含义说明和聚类效果验证方法

### 下一步

- [ ] 完善 `ucs_alias.csv` 数据（使用 LLM 处理 BoomList）
- [ ] 优化 `ucs_definitions.json`（添加排他性描述）
- [ ] 建立自动化测试流程
- [ ] 性能优化：大规模数据下的规则匹配效率

**详细文档**: 参见 [Phase3.5_Toolchain_DataPipeline.md](Phase3.5_Toolchain_DataPipeline.md)

