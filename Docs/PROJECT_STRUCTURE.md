# Sonic Compass 项目结构

## 目录结构

```
SonicCompass/
├── main.py                    # 主入口文件（启动应用）
├── gui_main.py                # 向后兼容入口（重定向到 ui 模块）
├── visualizer.py              # 向后兼容（重定向到 ui.visualizer）
├── rebuild_atlas.py           # 星图重建脚本（初次运行或强制重建数据）
│
├── core/                      # 核心业务逻辑模块
│   ├── __init__.py
│   ├── data_processor.py      # 数据处理器 - 索引构建器
│   ├── search_core.py         # 搜索算法核心
│   ├── vector_engine.py       # AI 向量引擎
│   ├── ucs_manager.py         # UCS 分类管理
│   ├── category_color_mapper.py  # Category 颜色映射器（基于 UCS Category 大类）
│   └── text_utils.py          # 文本归一化工具（Phase 3.5）
│
├── data/                      # 数据导入和配置模块
│   ├── __init__.py
│   ├── importer.py            # Soundminer 数据库导入器
│   ├── config_loader.py       # 配置加载器
│   └── database_config.py     # 数据库配置模块（统一数据库路径管理）
│
├── tools/                     # 工具脚本
│   ├── __init__.py
│   ├── deploy_model.py        # 模型部署工具
│   ├── generate_rules_json.py # 生成 rules.json 规则文件（Phase 3.5: 从 CSV 读取）
│   ├── generate_platinum_centroids.py # 生成白金质心
│   ├── verify_phase2.py       # Phase 2 验证脚本
│   ├── verify_pipeline.py     # 流水线验证脚本
│   ├── verify_subset.py       # 微缩验证工具（Phase 3.5，支持 CSV 导出和时间戳）
│   ├── standardize_alias_csv.py  # CSV 标准化工具（Phase 3.5）
│   └── standardize_alias_csv.py  # CSV 标准化工具（Phase 3.5）
│
├── ui/                        # UI 模块
│   ├── __init__.py
│   ├── main_window.py         # 主窗口
│   ├── styles.py              # 全局样式
│   ├── components/            # UI 组件
│   │   ├── canvas_view.py     # 画布视图
│   │   ├── search_bar.py      # 搜索栏
│   │   ├── inspector_panel.py # 检查器面板
│   │   └── universal_tagger.py # 通用标注器
│   └── visualizer/            # 可视化引擎
│       ├── sonic_universe.py  # 主场景
│       ├── hex_grid_item.py   # 六边形项
│       ├── scatter_item.py    # 散点项
│       └── errors.py          # 错误类
│
├── data_config/               # 数据配置文件
│   ├── axis_definitions.json  # 轴定义
│   ├── presets.json           # 预设配置
│   ├── ucs_catid_list.csv    # UCS 分类列表
│   ├── ucs_alias.csv          # UCS 别名
│   ├── rules.json             # 关键词到 CatID 映射规则（自动生成）
│   └── pillars_data.csv       # 引力桩数据
│
├── cache/                     # 缓存目录
│   ├── coordinates.npy        # UMAP 坐标缓存
│   ├── embeddings.npy         # 向量嵌入缓存
│   ├── metadata.pkl           # 元数据缓存
│   ├── index_info.pkl         # 索引信息
│   └── platinum_centroids_754.pkl  # Platinum 质心（用于 AI 预测）
│
├── verify_output/             # 测试输出目录（Phase 3.5）
│   ├── verify_*.png          # 验证结果图片（带时间戳）
│   └── verify_*_details_*.csv  # 详细数据表（带时间戳）
│
├── models/                    # AI 模型目录
│   └── bge-m3/                # BGE-M3 模型文件
│
├── test_assets/               # 测试资源
│   ├── Nas_SoundLibrary.sqlite  # 正式数据库（4.6 GB, 1,948,566 条记录）⭐ 当前使用
│   └── Sonic.sqlite              # 测试数据库（41 MB, 13,850 条记录）
│
└── Docs/                      # 文档目录
    ├── Phase1_Technical_Summary.md
    ├── Phase2_Technical_Summary.md
    ├── Phase3_Progress_Status.md
    ├── Phase3.5_Toolchain_DataPipeline.md  # Phase 3.5 工具链文档
    ├── 分类流程细节.md                      # 分类流程详细说明
    ├── 数据处理1.md                        # 数据处理工作流说明
    ├── DATABASE_CONFIG.md                  # 数据库配置说明
    ├── CatID_Format_Standardization.md      # CatID 格式标准化说明
    ├── Misc_Delay_Confirmation_Design.md    # Misc 延迟确认设计
    ├── MAINTENANCE_GUIDE.md                 # 维护指南
    ├── PROJECT_STRUCTURE.md                 # 项目结构说明
    └── 归档/                                # 归档文档
    └── The Architecture
```

## 模块说明

### 核心模块 (core/)
- **data_processor.py**: 数据处理器，批量向量化数据并构建索引缓存
- **search_core.py**: 提供极速的向量检索功能，支持文本搜索、ID搜索和引力计算
- **vector_engine.py**: 使用 BGE-M3 模型将文本转换为向量（1024维）
- **ucs_manager.py**: 管理 UCS 分类系统，处理 CatID 映射和别名解析
- **category_color_mapper.py**: Category 颜色映射器，基于 UCS Category 大类（82 个大类）分配统一颜色

### 数据模块 (data/)
- **config_loader.py**: 加载和管理配置文件（轴定义、预设等）

### 工具模块 (tools/)
- **deploy_model.py**: 模型部署工具
- **verify_phase2.py**: Phase 2 功能验证脚本
- **verify_pipeline.py**: 完整流水线验证脚本

### UI 模块 (ui/)
- **main_window.py**: 主窗口类，整合所有 UI 组件
- **components/**: 可复用的 UI 组件（画布视图、搜索栏、检查器面板、通用标注器）
- **visualizer/**: 高性能可视化引擎（批量渲染架构，三级 LOD 系统，Gravity Mode 向日葵螺旋）

## 启动应用

```bash
python main.py
```

## 向后兼容

为了保持向后兼容，以下文件保留在根目录：
- `gui_main.py`: 重定向到 `ui.main_window`
- `visualizer.py`: 重定向到 `ui.visualizer`

## 最新更新

### 2025-01-09 - Phase 3.5: 短路逻辑修复与数据库配置系统

**短路逻辑修复**:
- ✅ 修复 `resolve_category_from_filename` 返回格式问题
- ✅ 现在返回原始格式的 CatID（如 `ANMLAqua`），保持官方 UCS 格式
- ✅ 所有包含标准 CatID 的文件名都能被正确识别为 Level -1（文件名短路）

**数据库配置系统**:
- ✅ 新增 `data/database_config.py` - 统一的数据库路径配置模块
- ✅ 更新 `data_config/user_config.json` - 添加 `database_path` 字段
- ✅ 所有脚本和软件都从配置文件读取数据库路径
- ✅ 创建 `Docs/DATABASE_CONFIG.md` - 数据库配置说明文档

**测试脚本改进**:
- ✅ 所有测试输出文件统一保存到 `verify_output/` 文件夹
- ✅ 文件命名自动添加时间戳（格式：`MMDDHHmm`）
- ✅ CSV 导出包含详细数据（文件名、CatID、主类别、分类来源、UMAP 坐标）
- ✅ 添加 UMAP 坐标含义说明和聚类效果验证方法

### 2025-01-05 - Phase 3.5: 工具链与数据管道重构

**工具链建设**:
- ✅ 新增 `tools/verify_subset.py` - 微缩验证工具（30秒内验证分类效果）
- ✅ 新增 `core/text_utils.py` - 文本归一化工具（保留空格，整词匹配）
- ✅ 新增 `tools/standardize_alias_csv.py` - CSV 标准化工具

**规则系统重构**:
- ✅ `tools/generate_rules_json.py` 从硬编码改为读取 `ucs_alias.csv`
- ✅ 规则按关键词长度降序排序（最长优先）
- ✅ 关键词归一化保留空格（区分 "metal door" 和 "metaldoor"）
- ✅ 所有规则基于 CSV 真实数据生成

**分类逻辑升级**:
- ✅ `core/data_processor.py` 使用整词匹配（Whole Word Matching）
- ✅ 使用正则表达式 `\b{keyword}\b` 确保只匹配完整单词
- ✅ 避免误匹配（如 "train" 不会匹配 "training"）

**颜色映射系统重构**:
- ✅ CategoryColorMapper 支持 Category Name（第一列）作为 key
- ✅ 修复"色盲眼"问题：现在可以识别大类全名
- ✅ 支持三种查询方式：Category Name、CatID、CatShort

**聚类逻辑修正**:
- ✅ rebuild_atlas.py 使用 Category Name 而非 Code 进行聚合
- ✅ UCSManager 优化，确保正确读取 CSV 列

### 2025-01-04 - 数据源切换与问题修复

**数据源切换**:
- ✅ 数据源从 `Sonic.sqlite` 切换到 `Nas_SoundLibrary.sqlite`（正式数据库）
- ✅ 数据规模：从 13,850 条增加到 1,948,566 条（约 140 倍增长）
- ✅ 所有相关文件路径已更新（rebuild_atlas.py, main_window.py, 工具脚本）

**GPU 加速状态**:
- ✅ GPU 加速已启用（PyTorch 2.5.1+cu121, NVIDIA RTX 3070）
- ✅ 向量化已完成（1,948,566 条记录，7.43 GB embeddings）
- ✅ 性能提升：约 17 倍（从 ~11 条/秒到 ~192 条/秒）

**问题修复**:
- ✅ 修复缩放导致 UI 消失问题（场景矩形基于实际数据坐标）
- ✅ 修复视图适配重复调用问题
- ⚠️ UMAP 内存错误待解决（195 万条数据需要调整参数）

### 2025-01-02 - 可视化核心修复

**可视化核心修复**:
- ✅ 散点分布算法：实现局部向日葵螺旋布局，解决重叠问题
- ✅ 点击命中测试：使用最终显示坐标构建 cKDTree，确保坐标一致性
- ✅ LOD 标签逻辑：LOD 1 使用 Counter 统计 keywords/subcategory 的 Mode
- ✅ 视觉与颜色：统一使用 CategoryColorMapper 获取颜色
- ✅ 视图控制：添加 min/max zoom 限制，双击重置视图功能
- ✅ Inspector 面板增强：新增库、文件路径、描述显示

**技术改进**:
- 数据密度优化：归一化范围从 10000.0 减小到 3500.0
- 散点规整化：向日葵螺旋布局，确保点在六边形内部
- LOD 优化：降低聚类阈值，改进字体缩放公式
- 颜色统一：所有颜色从 CategoryColorMapper 获取

## 注意事项

1. **缓存目录**: `cache/` 目录包含预计算的数据，首次运行需要生成
2. **模型目录**: `models/bge-m3/` 需要包含完整的 BGE-M3 模型文件
3. **数据源**: 当前使用 `Nas_SoundLibrary.sqlite`（正式数据库，4.6 GB）
4. **GPU 加速**: 已启用 GPU 加速（CUDA 12.1），性能提升约 17 倍
5. **UMAP 计算**: 大规模数据（195 万条）可能需要调整参数以避免内存错误
6. **缩放功能**: 双击画布或按 R 键可重置视图
7. **场景矩形**: 基于实际数据坐标自动设置，确保缩放时内容可见

