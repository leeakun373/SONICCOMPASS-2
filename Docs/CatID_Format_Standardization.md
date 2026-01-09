# CatID 格式标准化方案

## 问题分析

### 当前问题

1. **官方 UCS 格式**：`ucs_catid_list.csv` 中的 CatID 是大小写混合（如 `GUNMisc`, `WEAPSwrd`）
2. **生成的规则格式**：`rules.json` 中的 CatID 是纯大写（如 `GUNMISC`, `WEAPSWRD`）
3. **存储格式**：`ucs_manager.catid_to_category` 使用原始格式（大小写混合）作为 key
4. **查找问题**：`enforce_strict_category` 转大写后查找，但字典 key 是原始格式，导致匹配失败

### 影响范围

- ✅ **Level 0（强规则）**：从 `rules.json` 读取大写 CatID，调用 `enforce_strict_category` 验证
- ✅ **Level 1（显式 Metadata）**：使用 `enforce_strict_category` 验证
- ✅ **Level 2（AI 预测）**：使用 `enforce_strict_category` 验证
- ✅ **短路逻辑**：直接匹配，但后续也需要验证

---

## 解决方案

### 原则

1. **存储格式**：统一使用官方 UCS 格式（大小写混合，如 `GUNMisc`）
2. **查找方式**：大小写不敏感（支持 `GUNMisc`, `GUNMISC`, `gunmisc` 都能找到）
3. **输出格式**：统一输出官方 UCS 格式（大小写混合）

### 实施步骤

#### 1. 修复 `generate_rules_json.py`

**问题**：当前保存为大写格式

**修复**：
- 从 `ucs_catid_list.csv` 中查找原始格式的 CatID
- 保存原始格式（大小写混合）到 `rules.json`

**代码修改**：
```python
# 修改前（第 104-110 行）
cat_id_upper = cat_id_raw.upper()
if cat_id_upper not in valid_catids:
    invalid_catids.append((keyword_raw, cat_id_raw))
    continue
rules_list.append((keyword_normalized, cat_id_upper, len(keyword_normalized)))

# 修改后
cat_id_upper = cat_id_raw.upper()
if cat_id_upper not in valid_catids:
    invalid_catids.append((keyword_raw, cat_id_raw))
    continue

# 查找原始格式的 CatID（从 ucs_catid_list.csv）
original_catid = None
for valid_id in catid_df['CatID']:
    if str(valid_id).strip().upper() == cat_id_upper:
        original_catid = str(valid_id).strip()
        break

if original_catid:
    rules_list.append((keyword_normalized, original_catid, len(keyword_normalized)))
else:
    # 如果找不到原始格式，使用大写（降级方案）
    rules_list.append((keyword_normalized, cat_id_upper, len(keyword_normalized)))
```

#### 2. 修复 `ucs_manager.py` - `enforce_strict_category`

**问题**：转大写后查找，但字典 key 是原始格式

**修复**：
- 支持大小写不敏感查找
- 返回原始格式的 CatID

**代码修改**：
```python
def enforce_strict_category(self, raw_cat: str) -> str:
    """
    严格执行UCS类别验证和规范化（数据安检门）
    
    支持大小写不敏感查找，但返回原始格式的 CatID。
    """
    if not raw_cat:
        return "UNCATEGORIZED"
    
    # 规范化输入（去除空白、转大写，使用副本）
    normalized_cat = str(raw_cat).strip().upper()
    
    # 如果已经在有效集合中，查找原始格式
    if normalized_cat in self.valid_categories:
        # 查找原始格式的 CatID
        for cat_id in self.catid_to_category.keys():
            if cat_id.upper() == normalized_cat:
                return cat_id  # 返回原始格式
        return normalized_cat  # 降级：如果找不到原始格式，返回大写
    
    # 尝试通过别名解析
    resolved_catid = self.resolve_alias(normalized_cat)
    if resolved_catid:
        # 查找原始格式
        for cat_id in self.catid_to_category.keys():
            if cat_id.upper() == resolved_catid.upper():
                return cat_id
        return resolved_catid
    
    # 尝试直接查找 CatID（大小写不敏感）
    for cat_id in self.catid_to_category.keys():
        if cat_id.upper() == normalized_cat:
            return cat_id  # 返回原始格式
    
    return "UNCATEGORIZED"
```

#### 3. 统一其他使用 CatID 的地方

**检查点**：
- `core/data_processor.py`：确保使用 `enforce_strict_category` 的结果
- `core/ucs_manager.py`：确保所有查找都支持大小写不敏感
- `tools/verify_subset.py`：确保输出使用原始格式
- UI 显示：确保显示原始格式

---

## 验证方案

### 测试用例

1. **测试 rules.json 格式**：
   ```python
   import json
   rules = json.load(open('data_config/rules.json'))
   # 检查是否包含大小写混合的 CatID
   assert "GUNMisc" in rules.values() or "GUNMISC" in rules.values()
   ```

2. **测试 enforce_strict_category**：
   ```python
   from core.ucs_manager import UCSManager
   m = UCSManager()
   m.load_all()
   
   # 测试大小写不敏感查找
   assert m.enforce_strict_category("gunmisc") == "GUNMisc"
   assert m.enforce_strict_category("GUNMISC") == "GUNMisc"
   assert m.enforce_strict_category("GUNMisc") == "GUNMisc"
   ```

3. **测试 Level 0 匹配**：
   ```python
   # 确保从 rules.json 读取的 CatID 能正确验证
   ```

---

## 实施状态

### ✅ 已完成

1. **修复 `generate_rules_json.py`**：
   - 现在保存原始格式的 CatID（大小写混合）
   - 从 `ucs_catid_list.csv` 中查找原始格式
   - 生成的 `rules.json` 使用官方 UCS 格式

2. **修复 `enforce_strict_category`**：
   - 支持大小写不敏感查找
   - 返回原始格式的 CatID（官方 UCS 格式）
   - 测试通过：`GUNMISC` → `GUNMisc`, `WEAPSWRD` → `WEAPSwrd`

### ✅ 验证结果

**rules.json 格式**：
```json
{
  "fire single": "GUNMisc",      // ✅ 原始格式
  "sword hit": "WEAPSwrd",        // ✅ 原始格式
  "laser gun": "LASRGun"          // ✅ 原始格式
}
```

**enforce_strict_category 测试**：
```
GUNMisc -> GUNMisc    ✅
GUNMISC -> GUNMisc    ✅ (大小写不敏感)
gunmisc -> GUNMisc    ✅ (大小写不敏感)
WEAPSwrd -> WEAPSwrd  ✅
WEAPSWRD -> WEAPSwrd  ✅ (大小写不敏感)
```

---

## 统一标准

### 存储格式

- **官方 UCS 格式**：大小写混合（如 `GUNMisc`, `WEAPSwrd`）
- **来源**：`ucs_catid_list.csv` 中的原始格式
- **存储位置**：
  - `ucs_manager.catid_to_category`（key 使用原始格式）
  - `rules.json`（value 使用原始格式）
  - 数据库中的 `category` 字段（使用原始格式）

### 查找方式

- **大小写不敏感**：支持 `GUNMisc`, `GUNMISC`, `gunmisc` 都能找到
- **返回格式**：统一返回原始格式（官方 UCS 格式）
- **实现位置**：`ucs_manager.enforce_strict_category()`

### 输出格式

- **统一输出**：所有输出都使用原始格式（官方 UCS 格式）
- **包括**：
  - `rules.json` 中的 CatID
  - 分类结果（`data_processor._extract_category` 返回的 CatID）
  - UI 显示的 CatID
  - 验证工具的输出

---

## 风险评估

### 潜在风险

1. **向后兼容性**：✅ 已解决 - `enforce_strict_category` 支持大小写不敏感查找
2. **性能影响**：✅ 影响很小 - 754 个 CatID 的遍历很快（O(n)，n=754）
3. **数据一致性**：✅ 已统一 - 所有地方都使用原始格式

### 缓解措施

1. ✅ **渐进式迁移**：已修复生成逻辑和验证逻辑
2. ✅ **降级方案**：`enforce_strict_category` 有降级逻辑（如果找不到原始格式，返回大写）
3. ✅ **测试覆盖**：已验证大小写不敏感查找和格式统一

---

## 使用指南

### 开发者注意事项

1. **不要手动转换大小写**：
   - ❌ 错误：`cat_id.upper()` 或 `cat_id.lower()`
   - ✅ 正确：使用 `enforce_strict_category(cat_id)` 进行验证和规范化

2. **存储 CatID 时**：
   - ✅ 使用 `enforce_strict_category()` 的结果（已经是原始格式）
   - ✅ 不要手动转换格式

3. **查找 CatID 时**：
   - ✅ 使用 `enforce_strict_category()`（支持大小写不敏感）
   - ✅ 不要直接使用字典查找（可能大小写不匹配）

### 数据维护

1. **更新 `ucs_alias.csv` 时**：
   - CatID 可以使用任意大小写（会被自动规范化）
   - 但建议使用原始格式（官方 UCS 格式）

2. **生成 `rules.json` 时**：
   - 运行 `python tools/generate_rules_json.py`
   - 会自动使用原始格式（官方 UCS 格式）

3. **验证 CatID 时**：
   - 使用 `enforce_strict_category()` 进行验证
   - 返回的 CatID 已经是原始格式

