# 颜色映射规范

## 核心设计原则

### 映射流程（唯一正确路径）

```
CatID (如 "AIRBLOW", "AEROHELI", "WPNGUN")
    ↓ 查表 catid_to_category
主类别 Category (如 "AIR", "AIRCRAFT", "WEAPONS")  ← 只有 82 个
    ↓ 查表 category_to_color
颜色 QColor  ← 82 种唯一颜色
```

### 为什么这样设计

1. **CatID 有数百个**（754+），不可能为每个单独配置颜色
2. **主类别只有 82 个**，是 UCS 标准定义的固定数量
3. **同一主类别下的所有 CatID 应该使用相同颜色**，这是视觉一致性的基础

## 关键实现要点

### 1. 大小写统一（Critical）

所有键必须转为**大写**存储和查询：

```python
# 加载时
cat_id = str(row['CatID']).strip().upper()  # "AIRBlow" → "AIRBLOW"
category = str(row['Category']).strip().upper()  # "Air" → "AIR"

# 查询时
normalized_key = str(key).strip().upper()  # 统一转大写
```

**禁止**：保留原始大小写，会导致查找失败。

### 2. QColor 比较（Critical）

**禁止**使用对象引用比较：

```python
# ❌ 错误：比较对象引用，可能永远为 True
if color != QColor('#333333'):
    ...

# ✅ 正确：比较颜色值
if color.name() != '#333333':
    ...
```

**原因**：`QColor('#333333') != QColor('#333333')` 在 Python/Qt 中可能返回 `True`，因为是不同对象实例。

### 3. 颜色生成算法

使用**黄金分割角度**分布，确保相邻主类别颜色差异明显：

```python
def _generate_category_color(self, category: str, index: int, total: int) -> QColor:
    golden_angle = 137.508  # 黄金分割角度
    hue = (index * golden_angle) % 360
    saturation = 200  # 高饱和度
    value = 220  # 中高亮度
    return QColor.fromHsv(int(hue), saturation, value)
```

**禁止**：使用不完整的硬编码颜色字典（如只定义 30 个颜色，而有 82 个主类别）。

### 4. 回退机制

当 CatID 未找到时的回退链：

```python
# 1. 精确匹配 CatID
category = catid_to_category.get(normalized_key)

# 2. 前缀匹配（3-5 字符）
if not category:
    for prefix_len in [3, 4, 5]:
        prefix = normalized_key[:prefix_len]
        if prefix in catid_to_category:
            category = catid_to_category[prefix]
            break

# 3. 哈希兜底（确保同一 key 总是相同颜色）
if not category:
    hash_val = hashlib.md5(key.encode()).hexdigest()
    return QColor.fromHsv(int(hash_val, 16) % 360, 200, 220)
```

## 文件职责

| 文件 | 职责 |
|------|------|
| `core/category_color_mapper.py` | 颜色映射器，CatID → 主类别 → 颜色 |
| `core/ucs_manager.py` | UCS 数据管理，提供 `get_main_category_by_id()` |
| `data_config/ucs_catid_list.csv` | 数据源：Category, CatID, CatShort 映射表 |

## 常见错误及修复

### 错误 1：所有颜色都是灰色

**原因**：大小写不匹配，查表失败
**修复**：确保加载和查询时都转大写

### 错误 2：同一主类别显示不同颜色

**原因**：直接用 CatID 哈希生成颜色，而不是通过主类别
**修复**：CatID → 主类别 → 颜色，确保中间步骤

### 错误 3：部分主类别是灰色

**原因**：颜色字典不完整，fallback 到灰色
**修复**：为所有 82 个主类别自动生成颜色，不依赖硬编码字典

### 错误 4：QColor 比较逻辑错误

**原因**：`color != QColor('#333333')` 比较的是对象引用
**修复**：使用 `color.name() != '#333333'` 比较字符串值

## 测试检查点

修改颜色相关代码后，必须验证：

```python
from core.category_color_mapper import CategoryColorMapper
mapper = CategoryColorMapper()

# 1. 同一主类别的 CatID 颜色相同
assert mapper.get_color('AIRBLOW').name() == mapper.get_color('AIRBRST').name()

# 2. 不同主类别的颜色不同
assert mapper.get_color('AIR').name() != mapper.get_color('WEAPONS').name()

# 3. 颜色不是灰色（除非是 UNCATEGORIZED）
assert mapper.get_color('AIR').name() != '#333333'
```

## 版本历史

- 2026-01-09: 彻底重构，简化为 CatID → 主类别 → 颜色 的单一路径

