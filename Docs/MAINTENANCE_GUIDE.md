# 维护指南

**更新时间**: 2025-01-05  
**目标**: 提供清晰的维护流程和最佳实践

## 快速参考

### 常用命令

```bash
# 1. 标准化 CSV（首次运行或格式更新后）
python tools/standardize_alias_csv.py

# 2. 从 CSV 生成规则
python tools/generate_rules_json.py

# 3. 快速验证分类效果
python tools/verify_subset.py AIR
python tools/verify_subset.py WEAPON

# 4. 重新生成质心（更新 ucs_definitions.json 后）
python tools/generate_platinum_centroids.py

# 5. 全量构建（验证通过后）
python rebuild_atlas.py
```

## 数据治理流程

### 添加新的关键词映射

1. **编辑 `data_config/ucs_alias.csv`**
   ```csv
   Keyword, CatID
   new keyword, CATID
   ```

2. **重新生成规则**
   ```bash
   python tools/generate_rules_json.py
   ```

3. **验证效果**
   ```bash
   python tools/verify_subset.py "new keyword"
   ```

### 更新 UCS 定义

1. **编辑 `data_config/ucs_definitions.json`**
   - 添加排他性描述（如 "Not magic, not spell"）
   - 更新类别描述

2. **重新生成质心**
   ```bash
   python tools/generate_platinum_centroids.py
   ```

3. **验证 AI 分类效果**
   ```bash
   python tools/verify_subset.py <相关关键词>
   ```

## 关键概念

### 整词匹配（Whole Word Matching）

- **原理**：使用正则表达式 `\b{keyword}\b` 确保只匹配完整单词
- **好处**：避免 "train" 匹配 "training" 的问题
- **示例**：
  - 规则：`"metal door" -> METLDoor`
  - ✅ 匹配：`"metal door slam"`（"door" 是完整单词）
  - ❌ 不匹配：`"metaldoor"`（没有单词边界）

### 关键词长度排序

- **原理**：规则按关键词长度降序排序
- **好处**：确保长关键词优先匹配
- **示例**：
  - `"metal door"` (len 10) 优先于 `"door"` (len 4)
  - 避免短关键词误匹配长短语

### 空格保留归一化

- **原理**：归一化时保留单词之间的空格
- **好处**：区分 "metal door" 和 "metaldoor"
- **示例**：
  - `normalize_text("metal door")` → `"metal door"`（保留空格）
  - `normalize_text("metal_door")` → `"metal door"`（下划线替换为空格）

## 故障排查

### 规则不生效

1. **检查关键词格式**
   - 确保 CSV 中的关键词格式正确
   - 运行 `python tools/generate_rules_json.py` 查看警告

2. **检查整词匹配**
   - 使用 `verify_subset.py` 验证匹配逻辑
   - 查看报告中的 "Level 0 (Rule)" 比例

3. **检查关键词长度**
   - 确保长关键词在 CSV 中排在前面
   - 规则生成时会自动按长度排序

### AI 分类不准确

1. **更新 UCS 定义**
   - 编辑 `data_config/ucs_definitions.json`
   - 添加排他性描述
   - 重新生成质心

2. **验证质心质量**
   - 使用 `verify_subset.py` 查看 AI 预测比例
   - 检查 "Level 2 (AI Prediction)" 的准确性

### CSV 格式问题

1. **运行标准化工具**
   ```bash
   python tools/standardize_alias_csv.py
   ```

2. **检查表头**
   - 确保 CSV 有表头：`Keyword, CatID`
   - 如果没有，标准化工具会自动添加

3. **检查 CatID 有效性**
   - 运行 `generate_rules_json.py` 查看无效 CatID 警告
   - 参考 `ucs_catid_list.csv` 确认有效 CatID

## 最佳实践

1. **数据更新流程**
   - 先更新 CSV/JSON
   - 重新生成规则/质心
   - 使用 `verify_subset.py` 快速验证
   - 验证通过后再运行全量构建

2. **关键词设计**
   - 使用完整短语（如 "metal door" 而非 "door"）
   - 避免过于通用的关键词
   - 考虑同义词和变体

3. **版本控制**
   - CSV 和 JSON 文件应纳入版本控制
   - 标准化工具会自动创建备份

4. **性能优化**
   - 规则按长度排序，减少匹配次数
   - 使用 `verify_subset.py` 限制查询数量进行测试

## 相关文档

- [Phase 3.5 工具链文档](Phase3.5_Toolchain_DataPipeline.md)
- [Phase 3 进度状态](Phase3_Progress_Status.md)
- [项目结构](PROJECT_STRUCTURE.md)

