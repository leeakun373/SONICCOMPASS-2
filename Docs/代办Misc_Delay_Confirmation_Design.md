# Misc 延迟确认逻辑设计

## 需求分析

**问题**：
- 在 Level 0（强规则/alias 检索）中，如果匹配到了 "xxxMisc" 这种模糊的 CatID
- 这些分类通常不够精确，因为关键词可能很通用、表达模糊
- 希望不要直接确定结果，而是继续到后续环节寻找更精确的分类

**目标**：
1. 如果 Level 0 匹配到 Misc 类别，不直接返回，保存为 fallback
2. 继续执行 Level 1（显式 Metadata）和 Level 2（AI 预测）
3. 如果后续环节找到了更精确的分类（非 Misc），使用更精确的
4. 如果后续环节都没找到，最后回退使用 Misc 分类

---

## 实现方案

### 1. 添加 Misc 类别检测方法

在 `UCSManager` 中添加方法，判断 CatID 是否是 Misc 类别：

```python
def is_misc_category(self, cat_id: str) -> bool:
    """
    判断 CatID 是否是 Misc 类别（模糊分类）
    
    Misc 类别的特征：
    1. CatID 本身包含 "MISC"（如 "WEAPMISC", "AIRMISC"）
    2. SubCategory 是 "MISC"
    3. Category 是 "MISC" 或 "MISCELLANEOUS"
    
    Args:
        cat_id: CatID 字符串
        
    Returns:
        True 如果是 Misc 类别，False 否则
    """
    if not cat_id:
        return False
    
    cat_id_upper = str(cat_id).strip().upper()
    
    # 检查 CatID 本身是否包含 "MISC"
    if "MISC" in cat_id_upper:
        return True
    
    # 检查 SubCategory 是否是 "MISC"
    if cat_id_upper in self.catid_to_category:
        category_obj = self.catid_to_category[cat_id_upper]
        if category_obj.subcategory.upper() == "MISC":
            return True
        if category_obj.category.upper() in ["MISC", "MISCELLANEOUS"]:
            return True
    
    return False
```

### 2. 修改 `_extract_category` 方法

修改分类流程，实现 Misc 延迟确认：

```python
def _extract_category(self, meta_dict: Dict) -> Optional[Tuple[str, str]]:
    """
    分类提取：4级瀑布流逻辑（支持 Misc 延迟确认）
    
    如果 Level 0 匹配到 Misc 类别，不直接返回，而是继续到后续环节寻找更精确的分类。
    """
    raw_cat = meta_dict.get('category', '').strip()
    rich_text = meta_dict.get('rich_context_text', '') or meta_dict.get('semantic_text', '')
    filename = meta_dict.get('filename', '').strip()
    
    # 用于保存 Misc 类别的 fallback
    misc_fallback_catid = None
    
    # --- Level -1: 短路逻辑 ---
    # （保持不变，如果匹配到就直接返回）
    
    # --- Level 0: 强规则 ---
    import re
    for keyword, target_id in self.strong_rules.items():
        keyword_lower = keyword.lower()
        text_lower = rich_text.lower() if rich_text else ""
        pattern = rf"\b{re.escape(keyword_lower)}\b"
        
        if re.search(pattern, text_lower):
            if self.ucs_manager:
                validated = self.ucs_manager.enforce_strict_category(target_id)
                
                # 【新增】检查是否是 Misc 类别
                if validated != "UNCATEGORIZED":
                    if self.ucs_manager.is_misc_category(validated):
                        # 如果是 Misc，保存为 fallback，继续执行后续环节
                        misc_fallback_catid = validated
                        break  # 跳出循环，继续到 Level 1
                    else:
                        # 如果不是 Misc，直接返回（原有逻辑）
                        return validated, ""
                else:
                    return target_id, ""
    
    # --- Level 1: 显式 Metadata ---
    if raw_cat and "MISC" not in raw_cat.upper() and raw_cat.upper() != "UNCATEGORIZED":
        if self.ucs_manager:
            validated_cat = self.ucs_manager.enforce_strict_category(raw_cat)
            if validated_cat != "UNCATEGORIZED":
                info = self.ucs_manager.get_catid_info(validated_cat)
                if info:
                    # 【新增】检查是否是 Misc 类别
                    if not self.ucs_manager.is_misc_category(validated_cat):
                        # 如果不是 Misc，直接返回（更精确的分类）
                        return validated_cat, ""
                    # 如果是 Misc，且之前没有 Misc fallback，保存它
                    elif not misc_fallback_catid:
                        misc_fallback_catid = validated_cat
    
    # --- Level 2: AI 向量匹配 ---
    if self.category_centroids and rich_text:
        try:
            vector = self.vector_engine.encode(rich_text)
            best_cat_id = None
            best_score = -1.0
            
            for cid, centroid in self.category_centroids.items():
                score = np.dot(vector, centroid)
                if score > best_score:
                    best_score = score
                    best_cat_id = cid
            
            if best_cat_id and best_score > 0.4:
                if self.ucs_manager:
                    validated = self.ucs_manager.enforce_strict_category(best_cat_id)
                    if validated != "UNCATEGORIZED":
                        # 【新增】检查是否是 Misc 类别
                        if not self.ucs_manager.is_misc_category(validated):
                            # 如果不是 Misc，直接返回（更精确的分类）
                            return validated, ""
                        # 如果是 Misc，且之前没有 Misc fallback，保存它
                        elif not misc_fallback_catid:
                            misc_fallback_catid = validated
    
    # --- Fallback: 使用 Misc 分类 ---
    # 如果所有环节都完成，还没有找到更精确的分类，使用 Misc fallback
    if misc_fallback_catid:
        return misc_fallback_catid, ""
    
    # 如果连 Misc fallback 都没有，返回 "UNCATEGORIZED"
    return "UNCATEGORIZED", ""
```

---

## 逻辑流程

```
输入: meta_dict
  │
  ├─→ Level -1: 短路逻辑（filename）
  │   ├─→ 找到 CatID? → ✅ 返回（结束）
  │   └─→ 未找到 → 继续
  │
  ├─→ Level 0: 强规则（rich_text）
  │   ├─→ 找到关键词?
  │   │   ├─→ 是 Misc? → 💾 保存为 fallback，继续
  │   │   └─→ 不是 Misc? → ✅ 返回（结束）
  │   └─→ 未找到 → 继续
  │
  ├─→ Level 1: 显式 Metadata（raw_cat）
  │   ├─→ 验证成功?
  │   │   ├─→ 是 Misc? → 💾 保存为 fallback（如果还没有），继续
  │   │   └─→ 不是 Misc? → ✅ 返回（结束，优先使用更精确的分类）
  │   └─→ 验证失败 → 继续
  │
  ├─→ Level 2: AI 向量匹配（rich_text）🤖
  │   ├─→ 相似度 > 0.4?
  │   │   ├─→ 是 Misc? → 💾 保存为 fallback（如果还没有），继续
  │   │   └─→ 不是 Misc? → ✅ 返回（结束，优先使用更精确的分类）
  │   └─→ 相似度 ≤ 0.4 → 继续
  │
  └─→ Fallback: 使用 Misc 分类
      ├─→ 有 Misc fallback? → ✅ 返回 Misc fallback
      └─→ 没有 Misc fallback? → ❌ 返回 "UNCATEGORIZED"
```

---

## 优势

1. **优先精确分类**：如果后续环节找到了更精确的分类（非 Misc），优先使用
2. **智能回退**：如果所有环节都只找到 Misc，最后使用 Misc 作为 fallback
3. **保持兼容性**：对于非 Misc 的分类，行为保持不变（直接返回）
4. **灵活扩展**：可以轻松调整 Misc 检测逻辑，或添加其他模糊类别的处理

---

## 注意事项

1. **性能影响**：Misc 检测需要额外的查表操作，但影响很小（O(1) 查找）
2. **Misc 定义**：需要明确定义哪些 CatID 被认为是 Misc 类别
3. **测试覆盖**：需要测试各种场景：
   - Level 0 匹配到 Misc，Level 1 找到精确分类
   - Level 0 匹配到 Misc，Level 2 找到精确分类
   - 所有环节都只找到 Misc
   - 所有环节都没找到分类

---

## 实现步骤

1. ✅ 在 `UCSManager` 中添加 `is_misc_category()` 方法
2. ✅ 修改 `DataProcessor._extract_category()` 方法
3. ✅ 添加测试用例验证逻辑
4. ✅ 更新文档说明

