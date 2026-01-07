"""
生成 rules.json 文件
从 ucs_alias.csv 读取关键词映射，生成关键词到 CatID 的映射规则
"""

import json
import pandas as pd
import sys
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入文本归一化工具
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.text_utils import normalize_keyword


def generate_rules_json():
    """
    从 ucs_alias.csv 生成 rules.json
    
    流程：
    1. 读取 data_config/ucs_catid_list.csv 验证 CatID 有效性
    2. 读取 data_config/ucs_alias.csv 获取关键词映射
    3. 对关键词进行归一化处理
    4. 验证所有 CatID 存在
    5. 生成 data_config/rules.json
    """
    config_dir = Path(__file__).parent.parent / "data_config"
    alias_csv_path = config_dir / "ucs_alias.csv"
    catid_csv_path = config_dir / "ucs_catid_list.csv"
    output_path = config_dir / "rules.json"
    
    # 1. 读取 ucs_catid_list.csv 验证 CatID
    if not catid_csv_path.exists():
        print(f"[ERROR] CatID CSV 文件不存在: {catid_csv_path}")
        sys.exit(1)
    
    print(f"[INFO] 读取 CatID CSV 文件: {catid_csv_path}")
    try:
        catid_df = pd.read_csv(catid_csv_path, encoding='utf-8')
    except:
        catid_df = pd.read_csv(catid_csv_path, encoding='latin1')
    
    catid_df.columns = [c.strip() for c in catid_df.columns]
    
    # 构建有效 CatID 集合
    valid_catids = set()
    for _, row in catid_df.iterrows():
        cat_id = str(row.get('CatID', '')).strip()
        if cat_id:
            valid_catids.add(cat_id)
    
    print(f"[INFO] 找到 {len(valid_catids)} 个有效的 CatID")
    
    # 2. 读取 ucs_alias.csv
    if not alias_csv_path.exists():
        print(f"[ERROR] Alias CSV 文件不存在: {alias_csv_path}")
        print(f"   请创建 {alias_csv_path} 文件，格式：Keyword, CatID")
        sys.exit(1)
    
    print(f"[INFO] 读取 Alias CSV 文件: {alias_csv_path}")
    try:
        alias_df = pd.read_csv(alias_csv_path, encoding='utf-8')
    except:
        alias_df = pd.read_csv(alias_csv_path, encoding='latin1')
    
    alias_df.columns = [c.strip() for c in alias_df.columns]
    
    # 检查是否有表头，如果没有则添加
    if 'Keyword' not in alias_df.columns or 'CatID' not in alias_df.columns:
        # 假设第一行是表头，或者没有表头
        if len(alias_df.columns) >= 2:
            # 重命名列
            alias_df.columns = ['Keyword', 'CatID'] + list(alias_df.columns[2:])
        else:
            print(f"[ERROR] Alias CSV 格式错误，需要至少两列：Keyword, CatID")
            sys.exit(1)
    
    # 3. 构建规则字典
    rules_list = []  # 使用列表存储，以便排序
    # 遍历 CSV 行，构建规则
    invalid_catids = []
    skipped_rows = 0
    
    for idx, row in alias_df.iterrows():
        keyword_raw = str(row.get('Keyword', '')).strip()
        cat_id_raw = str(row.get('CatID', '')).strip()
        
        # 跳过空行
        if not keyword_raw or not cat_id_raw:
            skipped_rows += 1
            continue
        
        # 归一化关键词（保留空格）
        keyword_normalized = normalize_keyword(keyword_raw)
        
        # 验证 CatID
        cat_id_upper = cat_id_raw.upper()
        if cat_id_upper not in valid_catids:
            invalid_catids.append((keyword_raw, cat_id_raw))
            continue
        
        # 存储为元组 (keyword, cat_id, length) 以便排序
        rules_list.append((keyword_normalized, cat_id_upper, len(keyword_normalized)))
    
    print(f"[INFO] 从 CSV 读取了 {len(alias_df)} 行数据")
    print(f"[INFO] 跳过了 {skipped_rows} 个空行")
    print(f"[INFO] 生成了 {len(rules_list)} 条规则")
    
    # 报告无效的 CatID
    if invalid_catids:
        print(f"[WARNING] 发现 {len(invalid_catids)} 个无效的 CatID（已跳过）:")
        for keyword, cat_id in invalid_catids[:10]:  # 只显示前10个
            print(f"  {keyword} -> {cat_id} (不存在)")
        if len(invalid_catids) > 10:
            print(f"  ... 还有 {len(invalid_catids) - 10} 个无效项")
    
    # 按关键词长度降序排序（最长优先）
    # 这确保 "metal door" (len 10) 在 "door" (len 4) 之前匹配
    rules_list.sort(key=lambda x: x[2], reverse=True)
    
    # 转换为字典（如果关键词重复，保留第一个，即最长的）
    rules = {}
    seen_keywords = set()
    for keyword, cat_id, length in rules_list:
        if keyword not in seen_keywords:
            rules[keyword] = cat_id
            seen_keywords.add(keyword)
    
    print(f"[INFO] 排序后保留 {len(rules)} 条唯一规则（按长度降序）")
    
    # 保存为 JSON
    print(f"[INFO] 生成 rules.json: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
    
    print(f"[INFO] 成功生成 {len(rules)} 条规则")
    print(f"[INFO] 文件已保存: {output_path}")


if __name__ == "__main__":
    try:
        generate_rules_json()
    except Exception as e:
        print(f"[ERROR] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

