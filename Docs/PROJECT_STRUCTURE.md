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
│   └── category_color_mapper.py  # Category 颜色映射器（基于 UCS Category 大类）
│
├── data/                      # 数据导入和配置模块
│   ├── __init__.py
│   ├── importer.py            # Soundminer 数据库导入器
│   └── config_loader.py       # 配置加载器
│
├── tools/                     # 工具脚本
│   ├── __init__.py
│   ├── deploy_model.py        # 模型部署工具
│   ├── verify_phase2.py       # Phase 2 验证脚本
│   └── verify_pipeline.py     # 流水线验证脚本
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
│   └── pillars_data.csv       # 引力桩数据
│
├── cache/                     # 缓存目录
│   ├── coordinates.npy        # UMAP 坐标缓存
│   ├── embeddings.npy         # 向量嵌入缓存
│   ├── metadata.pkl           # 元数据缓存
│   └── index_info.pkl         # 索引信息
│
├── models/                    # AI 模型目录
│   └── bge-m3/                # BGE-M3 模型文件
│
├── test_assets/               # 测试资源
│   ├── Nas_SoundLibrary.sqlite
│   └── Sonic.sqlite
│
└── Docs/                      # 文档目录
    ├── Phase1_Technical_Summary.md
    ├── Phase2_Technical_Summary.md
    ├── Phase3_Progress_Status.md
    ├── Refactoring_Summary.md
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

## 注意事项

1. **缓存目录**: `cache/` 目录包含预计算的数据，首次运行需要生成
2. **模型目录**: `models/bge-m3/` 需要包含完整的 BGE-M3 模型文件
3. **测试资源**: `test_assets/` 包含测试用的 SQLite 数据库文件

