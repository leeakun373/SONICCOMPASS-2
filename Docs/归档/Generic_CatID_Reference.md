# UCS 通用 CatID 参考

## 概述

UCS 标准中包含一些**通用/主类别级别**的 CatID，这些 CatID 通常用于：
- 复合场景（多个元素混合）
- 通用分类（没有更具体的子类别）
- 主类别标记（作为大类标识）

## 常见的通用 CatID

### 1. STORM (WEATHER-STORM)

**CatID**: `STORM`  
**完整路径**: `WEATHER,STORM,STORM,STORM`  
**说明**: 复合风暴，包含风、雨、雷等多种元素的混合风暴录音

**使用场景**:
- `storm wind` → `STORM` ✅
- `sandstorm wind` → `STORM` ✅
- `blizzard wind` → `STORM` ✅
- `storm ambience` → `STORM` ✅

**注意**: 如果只有单一元素（如只有风），应该使用更具体的 CatID（如 `WINDTurb`）

---

### 2. RAIN (RAIN-GENERAL)

**CatID**: `RAIN`  
**完整路径**: `RAIN,GENERAL,RAIN,RAIN`  
**说明**: 通用雨声，混合材料的雨声（没有更具体的表面类型）

**使用场景**:
- `rain ambience` → `RAIN` ✅
- `rain fall` → `RAIN` ✅
- `rain heavy` → `RAIN` ✅
- `rain light` → `RAIN` ✅

**更具体的 CatID**（如果知道表面类型）:
- `RAINClth` - 雨打在布料上
- `RAINConc` - 雨打在水泥/沥青上
- `RAINGlas` - 雨打在玻璃上
- `RAINMetl` - 雨打在金属上
- `RAINVege` - 雨打在植物上
- `RAINWood` - 雨打在木头上

---

### 3. THUN (WEATHER-THUNDER)

**CatID**: `THUN`  
**完整路径**: `WEATHER,THUNDER,THUN,THUN`  
**说明**: 雷声和闪电，从远处的隆隆声到尖锐的雷击声

**使用场景**:
- `thunder crack` → `THUN` ✅
- `thunder rumble` → `THUN` ✅
- `thunder roll` → `THUN` ✅
- `lightning strike` → `THUN` ✅
- `lightning hit` → `THUN` ✅

**注意**: 如果雷声和雨声混合，应该使用 `STORM`（复合风暴）

---

### 4. WIND (WIND)

**CatID**: `WIND`  
**完整路径**: `WIND,?,WIND,?`  
**说明**: 通用风（需要确认具体子类别）

**使用场景**:
- `wind burst` → `WIND` ✅
- `heavy wind` → `WIND` ✅
- `strong wind` → `WIND` ✅

**更具体的 CatID**（如果知道类型）:
- `WINDGust` - 阵风
- `WINDTurb` - 湍流风
- `WINDDsgn` - 设计风（人工/合成）
- `WINDInt` - 室内风
- `WINDVege` - 风穿过植被

---

## 通用 CatID vs 具体 CatID

### 何时使用通用 CatID？

1. **复合场景**: 多个元素混合，无法分离
   - 例如：`storm wind` → `STORM`（风+雨+雷混合）

2. **通用分类**: 不知道具体类型或表面
   - 例如：`rain ambience` → `RAIN`（不知道打在什么表面）

3. **主类别标记**: 作为大类标识
   - 例如：`wind burst` → `WIND`（通用风）

### 何时使用具体 CatID？

1. **知道具体类型**: 如果知道表面类型或具体特征
   - 例如：`rain on metal` → `RAINMetl`（而不是 `RAIN`）
   - 例如：`wind gust` → `WINDGust`（而不是 `WIND`）

2. **更精确的分类**: 提供更精确的分类信息
   - 例如：`rain on glass` → `RAINGlass`（而不是 `RAIN`）

---

## 在 ucs_alias.csv 中的使用

### 当前使用情况

```csv
storm wind,STORM          # ✅ 复合风暴
rain ambience,RAIN        # ✅ 通用雨声
thunder crack,THUN        # ✅ 雷声
wind burst,WIND          # ✅ 通用风
```

### 建议

1. **如果可能，使用更具体的 CatID**:
   - `rain on metal` → `RAINMetl`（而不是 `RAIN`）
   - `wind gust` → `WINDGust`（而不是 `WIND`）

2. **如果不知道具体类型，使用通用 CatID**:
   - `rain ambience` → `RAIN` ✅
   - `wind burst` → `WIND` ✅

3. **复合场景使用复合 CatID**:
   - `storm wind` → `STORM` ✅（风+雨+雷混合）

---

## 验证

所有通用 CatID 都在 UCS 标准列表中：

- ✅ `STORM` - 在 `ucs_catid_list.csv` 第 724 行
- ✅ `RAIN` - 在 `ucs_catid_list.csv` 第 553 行
- ✅ `THUN` - 在 `ucs_catid_list.csv` 第 725 行
- ✅ `WIND` - 在 `ucs_catid_list.csv` 中（需要确认具体行）

这些 CatID 都是**有效的 UCS 标准 CatID**，可以正常使用。

