# Sonic Compass 2.0

一个基于 AI 的音频资源管理和可视化工具，采用赛博朋克风格的可视化界面。

## 功能特性

- **智能搜索**: 基于 BGE-M3 模型的语义搜索
- **可视化地图**: 使用 UMAP 降维的 2D 可视化，支持三级 LOD 系统
- **重力模式**: 搜索结果以向日葵螺旋布局展示
- **分类系统**: 支持 UCS 分类标准，自动颜色映射
- **交互操作**: 
  - 滚轮缩放
  - 左键拖拽平移
  - 右键框选

## 技术栈

- **GUI 框架**: PySide6 (Qt)
- **AI 模型**: BGE-M3 (BAAI General Embedding)
- **降维算法**: UMAP
- **数据存储**: SQLite

## 安装依赖

```bash
pip install PySide6
pip install umap-learn scikit-learn
pip install sentence-transformers
pip install numpy pandas
```

## 首次运行

1. **安装模型**:
   - 下载 BGE-M3 模型到 `models/bge-m3/` 目录
   - 或运行 `tools/deploy_model.py` 自动下载

2. **构建数据索引**:
   ```bash
   python rebuild_atlas.py
   ```

3. **启动应用**:
   ```bash
   python main.py
   ```

## 项目结构

```
SonicCompass/
├── core/              # 核心模块
│   ├── data_processor.py    # 数据处理
│   ├── search_core.py       # 搜索核心
│   ├── vector_engine.py     # 向量引擎
│   └── ucs_manager.py       # UCS 分类管理
├── data/              # 数据模块
│   ├── importer.py          # 数据导入
│   └── config_loader.py     # 配置加载
├── ui/                # UI 模块
│   ├── main_window.py       # 主窗口
│   ├── components/          # UI 组件
│   └── visualizer/         # 可视化引擎
├── data_config/       # 配置文件
│   ├── ucs_catid_list.csv   # UCS 分类列表
│   └── presets.json         # 预设配置
└── tools/             # 工具脚本
    └── deploy_model.py      # 模型部署
```

## 开发状态

当前版本：Phase 3 - Visual Finalization

已完成功能：
- ✅ 三级 LOD 系统（LOD 0/1/2）
- ✅ 标签聚类算法
- ✅ Gravity Mode 向日葵螺旋布局
- ✅ 视觉优化（六边形内缩、硬朗边框、径向渐变）
- ✅ 交互操作（缩放、平移、框选）

## 许可证

MIT License

## 作者

leeakun373

