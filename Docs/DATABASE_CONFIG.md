# 数据库配置说明

## 概述

Sonic Compass 使用统一的配置文件来管理数据库路径，方便用户在不同数据库之间切换，无需修改代码。

## 配置文件位置

**配置文件**: `data_config/user_config.json`

## 配置格式

```json
{
  "library_root": "K:/1000-SFX Library",
  "database_path": "./test_assets/Boom_Test_AlienLife.sqlite"
}
```

### 配置项说明

- **`library_root`**: 音频库根目录路径（用于文件路径解析）
- **`database_path`**: SQLite 数据库文件路径（**所有脚本和软件都使用此配置**）

## 如何修改数据库路径

### 方法 1: 直接编辑配置文件（推荐）

1. 打开 `data_config/user_config.json`
2. 修改 `database_path` 字段的值
3. 保存文件

**示例**:
```json
{
  "library_root": "K:/1000-SFX Library",
  "database_path": "./test_assets/Boom_Test_AlienLife.sqlite"
}
```

### 方法 2: 使用命令行参数（临时覆盖）

某些脚本支持 `--db` 参数来临时覆盖配置：

```bash
# 测试脚本示例
python tools/verify_subset.py WEAPON --db ./test_assets/AnotherDatabase.sqlite
```

## 默认值

如果配置文件中没有设置 `database_path`，系统会使用默认值：
- **默认路径**: `./test_assets/Sonic.sqlite`

## 使用此配置的组件

以下组件都会自动从配置文件读取数据库路径：

1. **主程序** (`main.py`, `gui_main.py`)
2. **重建脚本**:
   - `rebuild_atlas.py` - 完整重建
   - `recalculate_umap.py` - 重新计算 UMAP
   - `rebuild_vectors_only.py` - 仅重新向量化
3. **测试脚本**:
   - `tools/verify_subset.py` - 微缩验证工具
   - `tools/verify_pipeline.py` - 管道验证
   - `tools/verify_phase2.py` - Phase 2 验证
4. **UI 界面** (`ui/main_window.py`)

## 配置验证

系统会在启动时自动验证数据库文件是否存在：

- ✅ **如果文件存在**: 正常加载
- ⚠️ **如果文件不存在**: 显示警告，并使用默认路径（如果默认路径也不存在，则报错）

## 路径格式

支持以下路径格式：

- **相对路径**: `./test_assets/Boom_Test_AlienLife.sqlite`
- **绝对路径**: `E:/Audio_Projects/Tools/SonicCompass/test_assets/Boom_Test_AlienLife.sqlite`
- **Windows 路径**: `E:\Audio_Projects\Tools\SonicCompass\test_assets\Boom_Test_AlienLife.sqlite`

## 测试配置

运行以下命令测试配置是否正确：

```bash
python -c "from data.database_config import get_database_path; print('数据库路径:', get_database_path())"
```

## 常见问题

### Q: 修改配置后，软件还是使用旧路径？

**A**: 确保配置文件格式正确（JSON 格式），并且路径字符串用双引号包裹。

### Q: 如何查看当前使用的数据库路径？

**A**: 运行测试命令（见上方），或在软件启动时查看控制台输出。

### Q: 可以同时使用多个数据库吗？

**A**: 可以，但需要手动切换配置文件，或使用命令行参数临时覆盖。

## 技术实现

配置系统使用以下模块：

- **`data/config_loader.py`**: 配置加载器，负责读取和保存配置
- **`data/database_config.py`**: 数据库配置模块，提供统一的 `get_database_path()` 函数

所有组件都通过 `get_database_path()` 函数获取数据库路径，确保配置的一致性。

