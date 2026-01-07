# Phase 3.5: 工具链与数据管道重构

**更新时间**: 2025-01-05  
**状态**: ✅ 已完成

## 概述

Phase 3.5 的核心目标是建立快速验证工具链，打通数据管道，实现数据驱动的规则生成系统。通过创建微缩验证工具和重构规则生成流程，实现从硬编码到数据驱动的转变。

## 目标

1. **建立快速验证工具**：30秒内验证分类效果，无需运行全量构建
2. **打通数据管道**：从 CSV 文件动态生成规则，而非硬编码
3. **实现数据治理闭环**：数据更新 → 规则生成 → 验证 → 迭代

## 三阶段实施路线图

### 🟢 第一阶段：工具链与基础设施建设

#### 1.1 微缩验证工具 `tools/verify_subset.py`

**功能**：
- 接受关键词参数（如 'AIR', 'WEAPON'），从 SQLite 数据库提取相关数据（几百条）
- 运行 DataProcessor 的分类逻辑（规则 + AI）
- 使用 matplotlib 生成静态散点图（保存为 PNG）
- 不同 UCS 大类用不同颜色标记
- 控制台打印每条数据的最终 CatID 和来源（Level 0 规则命中或 Level 2 AI 命中）

**使用方法**：
```bash
# 验证 'AIR' 关键词的分类效果（默认输出 verification_result.png）
python tools/verify_subset.py AIR

# 指定数据库和输出路径
python tools/verify_subset.py WEAPON --db ./test_assets/Sonic.sqlite --output verify_weapon.png

# 限制查询数量
python tools/verify_subset.py VEHICLE --limit 200
```

**输出**：
- PNG 图片文件（默认 `verification_result.png`）
- 控制台分类报告（分类来源统计、类别分布、详细结果）
- **报告格式**：`Matched 'train horn 01' -> TRNHorn via Level 0 (Rule)`

#### 1.2 文本归一化工具 `core/text_utils.py`

**功能**：
- `normalize_text(text: str, remove_numbers: bool = False) -> str`
- **关键特性**：保留单词之间的空格，确保 "metal door" 与 "metaldoor" 区分
- 归一化规则：
  1. 转小写
  2. 将下划线/连字符替换为空格
  3. 移除文件扩展名和版本号（如 '01', 'v2'）
  4. **保留单词之间的空格**（关键：'metal door' vs 'metaldoor'）
  5. 去除首尾空白

**使用场景**：
- CSV 关键词归一化
- 文件名匹配
- 规则生成时的键值归一化

**API**：
```python
from core.text_utils import normalize_text, normalize_keyword, normalize_filename

# 基础归一化（保留空格）
normalize_text("Train_Horn-01.wav")  # -> "train horn 01"
normalize_text("Train_Horn-01.wav", remove_numbers=True)  # -> "train horn"
normalize_text("metal door")  # -> "metal door" (保留空格)
normalize_text("laser gun")  # -> "laser gun" (保留空格)

# 关键词归一化
normalize_keyword("laser gun")  # -> "laser gun" (保留空格)

# 文件名归一化
normalize_filename("/path/to/Train_Horn-01.wav")  # -> "train horn 01"
```

### 🟡 第二阶段：打通数据管道

#### 2.1 重构 `tools/generate_rules_json.py`

**修改前**：
- 硬编码了巨大的 rules 字典（200+ 行）
- 无法从外部数据源动态生成规则

**修改后**：
- 从 `data_config/ucs_alias.csv` 读取关键词映射
- 对关键词进行归一化处理（使用 `text_utils.normalize_keyword`，**保留空格**）
- **按关键词长度降序排序**（最长优先），确保 "metal door" (len 10) 在 "door" (len 4) 之前匹配
- 验证 CatID 是否在 UCS 标准列表中存在
- 生成 `data_config/rules.json`

**使用方法**：
```bash
# 从 ucs_alias.csv 生成 rules.json
python tools/generate_rules_json.py
```

**CSV 格式要求**：
- 表头：`Keyword, CatID`
- 数据行：`laser gun, LASRGun` 或 `metal door, METLDoor`
- 支持多行，每行一个映射
- **注意**：关键词中的空格会被保留，用于整词匹配

**验证逻辑**：
- 读取 `data_config/ucs_catid_list.csv` 获取有效 CatID 集合
- 如果 CSV 中的 CatID 不存在，报错或跳过（带警告）

**排序策略**：
- 规则按关键词长度降序排序
- 确保长关键词（如 "metal door"）优先于短关键词（如 "door"）匹配
- 避免短关键词误匹配长短语

#### 2.2 标准化 `data_config/ucs_alias.csv`

**当前状态**：
- 文件存在但格式不标准（无表头，格式混乱）

**标准化工具**：`tools/standardize_alias_csv.py`

**功能**：
- 添加表头：`Keyword, CatID`
- 规范化 CatID 格式（转大写，验证有效性）
- 备份原文件

**使用方法**：
```bash
# 标准化 ucs_alias.csv
python tools/standardize_alias_csv.py
```

**注意**：
- 会创建备份文件 `ucs_alias.csv.backup`
- 无效的 CatID 会被标记但保留

### 🔴 第三阶段：数据注入与迭代闭环

#### 3.1 数据治理流程

**完整迭代流程**：

1. **更新 `ucs_alias.csv`**
   - 添加新的关键词映射
   - 格式：`keyword, CATID`
   - 使用归一化后的关键词（小写，无符号）

2. **重新生成规则**
   ```bash
   python tools/generate_rules_json.py
   ```

3. **更新质心定义（如需要）**
   - 编辑 `data_config/ucs_definitions.json`
   - 添加排他性描述（例如在 Fire 里加 "Not magic, not spell"）

4. **重新生成质心**
   ```bash
   python tools/generate_platinum_centroids.py
   ```

5. **快速验证**
   ```bash
   # 验证几个大类
   python tools/verify_subset.py AIR
   python tools/verify_subset.py WEAPON
   python tools/verify_subset.py VEHICLE
   ```

6. **全量构建（验证通过后）**
   ```bash
   python rebuild_atlas.py
   ```

## 快速测试指南

### 场景 1: 验证新添加的关键词映射

```bash
# 1. 在 ucs_alias.csv 中添加新映射
# 例如：lasergun, LASRGun

# 2. 重新生成规则
python tools/generate_rules_json.py

# 3. 快速验证
python tools/verify_subset.py LASER
```

### 场景 2: 验证 AI 分类效果

```bash
# 验证某个大类下 AI 预测的准确率
python tools/verify_subset.py SCIFI --limit 300

# 查看报告中的 "Level 2 (AI预测)" 比例
```

### 场景 3: 验证规则命中率

```bash
# 验证规则是否生效
python tools/verify_subset.py WEAPON --limit 500

# 查看报告中的 "Level 0 (规则)" 比例
# 如果比例太低，说明需要添加更多关键词映射
```

### 场景 4: 完整数据治理迭代

```bash
# 1. 标准化 CSV（首次运行）
python tools/standardize_alias_csv.py

# 2. 更新 CSV（手动编辑或使用 LLM 处理）

# 3. 重新生成规则
python tools/generate_rules_json.py

# 4. 更新质心定义（如需要）
# 编辑 data_config/ucs_definitions.json

# 5. 重新生成质心
python tools/generate_platinum_centroids.py

# 6. 快速验证多个大类
python tools/verify_subset.py AIR
python tools/verify_subset.py WEAPON
python tools/verify_subset.py VEHICLE

# 7. 如果验证通过，运行全量构建
python rebuild_atlas.py
```

## 工具清单

| 工具 | 路径 | 功能 | 状态 |
|------|------|------|------|
| 微缩验证工具 | `tools/verify_subset.py` | 快速验证分类效果 | ✅ 已完成 |
| 文本归一化工具 | `core/text_utils.py` | 文本归一化函数 | ✅ 已完成 |
| 规则生成工具 | `tools/generate_rules_json.py` | 从 CSV 生成规则 | ✅ 已重构 |
| CSV 标准化工具 | `tools/standardize_alias_csv.py` | 标准化 CSV 格式 | ✅ 已完成 |

## 数据文件

| 文件 | 路径 | 格式 | 说明 |
|------|------|------|------|
| 别名映射 | `data_config/ucs_alias.csv` | `Keyword, CatID` | 关键词到 CatID 的映射 |
| 规则文件 | `data_config/rules.json` | JSON | 自动生成，用于 Level 0 规则匹配 |
| UCS 定义 | `data_config/ucs_definitions.json` | JSON | UCS 类别定义，用于生成质心 |
| CatID 列表 | `data_config/ucs_catid_list.csv` | CSV | UCS 标准 CatID 列表 |

## 分类逻辑说明

### Level 0: 强规则匹配（整词匹配）

- **来源**：`data_config/rules.json`
- **匹配方式**：使用**整词正则匹配**（Whole Word Regex Matching）
  - 使用 `re.search(rf"\b{re.escape(keyword_lower)}\b", text_lower)` 
  - 确保只匹配完整单词，避免 "train" 匹配 "training"
  - 关键词已按长度降序排序，长关键词优先匹配
- **返回**：直接返回 CatID

**示例**：
- 规则：`"metal door" -> METLDoor`
- 文本：`"metal door slam"` ✅ 匹配
- 文本：`"metaldoor"` ❌ 不匹配（整词匹配）
- 文本：`"metal doors"` ✅ 匹配（"door" 是完整单词）

### Level 1: 显式 Metadata

- **来源**：数据库中的 `category` 字段
- **验证**：通过 UCSManager 验证 CatID 有效性
- **返回**：验证后的 CatID

### Level 2: AI 向量匹配

- **来源**：Platinum Centroids（从 `ucs_definitions.json` 生成）
- **匹配方式**：计算向量与质心的余弦相似度
- **阈值**：> 0.4
- **返回**：最佳匹配的 CatID

## 注意事项

1. **关键词归一化**：
   - CSV 中的关键词会被自动归一化（转小写，下划线/连字符替换为空格）
   - **空格会被保留**：`"metal door"` 与 `"metaldoor"` 是不同的关键词
   - 文件扩展名和版本号会被自动移除

2. **整词匹配**：
   - 规则匹配使用整词边界（`\b`），确保只匹配完整单词
   - 避免 "train" 匹配 "training" 的问题
   - 关键词按长度降序排序，长关键词优先匹配

3. **CatID 格式**：CatID 必须是有效的 UCS CatID（参考 `ucs_catid_list.csv`）

4. **备份数据**：标准化 CSV 时会自动创建备份

5. **验证顺序**：先验证小规模数据，再运行全量构建

6. **性能考虑**：`verify_subset.py` 限制默认 500 条，可根据需要调整

7. **输出文件**：验证工具默认输出为 `verification_result.png`，可通过 `--output` 参数自定义

## 下一步

- [ ] 完善 `ucs_alias.csv` 数据（使用 LLM 处理 BoomList）
- [ ] 优化 `ucs_definitions.json`（添加排他性描述）
- [ ] 建立自动化测试流程
- [ ] 集成到 CI/CD 流程（如需要）

## 相关文档

- [Phase 3 进度状态](Phase3_Progress_Status.md)
- [项目结构](PROJECT_STRUCTURE.md)
- [架构文档](The%20Architecture)

