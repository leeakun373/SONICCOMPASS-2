"""
标准化 ucs_alias.csv 格式
添加表头，规范化 CatID 格式
"""

import pandas as pd
import sys
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.ucs_manager import UCSManager


def standardize_alias_csv():
    """标准化 ucs_alias.csv"""
    config_dir = Path(__file__).parent.parent / "data_config"
    csv_path = config_dir / "ucs_alias.csv"
    backup_path = config_dir / "ucs_alias.csv.backup"
    
    if not csv_path.exists():
        print(f"[ERROR] CSV 文件不存在: {csv_path}")
        sys.exit(1)
    
    print(f"[INFO] 读取 CSV 文件: {csv_path}")
    
    # 读取 CSV（自动检测是否有表头）
    try:
        # 先尝试读取第一行，检查是否是表头
        first_line = pd.read_csv(csv_path, nrows=1, encoding='utf-8')
        if 'Keyword' in first_line.columns and 'CatID' in first_line.columns:
            # 有表头，正常读取
            df = pd.read_csv(csv_path, encoding='utf-8')
            print(f"[INFO] 检测到 CSV 已有表头: {list(df.columns)}")
        else:
            # 没有表头，添加表头
            df = pd.read_csv(csv_path, header=None, names=['Keyword', 'CatID'], encoding='utf-8')
            print(f"[INFO] CSV 无表头，已添加表头")
    except Exception as e:
        # 如果 UTF-8 失败，尝试 latin1
        try:
            first_line = pd.read_csv(csv_path, nrows=1, encoding='latin1')
            if 'Keyword' in first_line.columns and 'CatID' in first_line.columns:
                df = pd.read_csv(csv_path, encoding='latin1')
                print(f"[INFO] 检测到 CSV 已有表头（latin1）: {list(df.columns)}")
            else:
                df = pd.read_csv(csv_path, header=None, names=['Keyword', 'CatID'], encoding='latin1')
                print(f"[INFO] CSV 无表头，已添加表头（latin1）")
        except Exception as e2:
            print(f"[ERROR] 无法读取 CSV 文件: {e2}")
            sys.exit(1)
    
    # 确保列名正确
    if 'Keyword' not in df.columns or 'CatID' not in df.columns:
        print(f"[ERROR] CSV 列名不正确，期望 'Keyword' 和 'CatID'，实际: {list(df.columns)}")
        sys.exit(1)
    
    print(f"[INFO] 读取了 {len(df)} 行数据")
    
    # 备份原文件
    import shutil
    shutil.copy2(csv_path, backup_path)
    print(f"[INFO] 已备份原文件到: {backup_path}")
    
    # 加载 UCSManager 用于验证 CatID
    print(f"[INFO] 加载 UCSManager 验证 CatID...")
    ucs_manager = UCSManager()
    ucs_manager.load_all()  # 【修复】必须调用 load_all() 才能加载数据
    print(f"[INFO] 已加载 {len(ucs_manager.catid_to_category)} 个有效 CatID")
    
    valid_catids = set()
    for cat_id in ucs_manager.catid_to_category.keys():
        valid_catids.add(cat_id.upper())
        valid_catids.add(cat_id)  # 也保留原始格式
    
    # 规范化数据
    print(f"[INFO] 规范化数据...")
    cleaned_rows = []
    invalid_items = []  # 存储所有无效项，包含行号
    
    # 注意：pandas 的 iterrows() 中 idx 是 DataFrame 的索引（从 0 开始）
    # 但 CSV 文件的实际行号 = idx + 2（因为第 1 行是表头，从第 2 行开始是数据）
    for idx, row in df.iterrows():
        keyword = str(row['Keyword']).strip()
        cat_id_raw = str(row['CatID']).strip()
        
        # 跳过空行
        if not keyword or not cat_id_raw:
            continue
        
        # 计算实际行号（CSV 文件中的行号，从 1 开始）
        # idx 是 DataFrame 索引（从 0 开始），加上表头（1行），所以实际行号 = idx + 2
        csv_line_number = idx + 2
        
        # 尝试规范化 CatID
        cat_id_upper = cat_id_raw.upper()
        
        # 检查是否是有效的 CatID（直接匹配或尝试查找）
        if cat_id_upper in valid_catids:
            # 找到原始格式的 CatID
            original_catid = None
            for valid_id in ucs_manager.catid_to_category.keys():
                if valid_id.upper() == cat_id_upper:
                    original_catid = valid_id
                    break
            
            if original_catid:
                cleaned_rows.append({
                    'Keyword': keyword,
                    'CatID': original_catid
                })
            else:
                cleaned_rows.append({
                    'Keyword': keyword,
                    'CatID': cat_id_upper
                })
        else:
            # 无效的 CatID，记录行号和详细信息
            invalid_items.append({
                'line': csv_line_number,
                'keyword': keyword,
                'catid': cat_id_raw
            })
            cleaned_rows.append({
                'Keyword': keyword,
                'CatID': cat_id_upper  # 至少转大写
            })
    
    # 完整显示所有无效的 CatID（带行号）
    if invalid_items:
        print(f"\n[WARNING] 发现 {len(invalid_items)} 个无效的 CatID（已跳过）:")
        print("=" * 80)
        for item in invalid_items:
            print(f"  行 {item['line']:4d}: {item['keyword']:30s} -> {item['catid']}")
        print("=" * 80)
        print(f"[WARNING] 这些 CatID 不在 UCS 标准列表中，请检查并修正")
    else:
        print(f"[INFO] ✅ 所有 CatID 都有效！")
    
    # 创建新的 DataFrame
    new_df = pd.DataFrame(cleaned_rows)
    
    # 保存（带表头）
    print(f"[INFO] 保存标准化后的 CSV...")
    new_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"[INFO] ✅ 标准化完成！")
    print(f"   原始行数: {len(df)}")
    print(f"   清理后行数: {len(new_df)}")
    print(f"   无效 CatID: {len(invalid_items)}")
    print(f"   文件已保存: {csv_path}")


if __name__ == "__main__":
    try:
        standardize_alias_csv()
    except Exception as e:
        print(f"[ERROR] 标准化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

