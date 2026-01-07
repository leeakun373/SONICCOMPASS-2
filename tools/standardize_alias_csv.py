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
    
    # 读取 CSV（无表头）
    try:
        df = pd.read_csv(csv_path, header=None, names=['Keyword', 'CatID'], encoding='utf-8')
    except:
        df = pd.read_csv(csv_path, header=None, names=['Keyword', 'CatID'], encoding='latin1')
    
    print(f"[INFO] 读取了 {len(df)} 行数据")
    
    # 备份原文件
    import shutil
    shutil.copy2(csv_path, backup_path)
    print(f"[INFO] 已备份原文件到: {backup_path}")
    
    # 加载 UCSManager 用于验证 CatID
    print(f"[INFO] 加载 UCSManager 验证 CatID...")
    ucs_manager = UCSManager()
    valid_catids = set()
    for cat_id in ucs_manager.catid_to_category.keys():
        valid_catids.add(cat_id.upper())
        valid_catids.add(cat_id)  # 也保留原始格式
    
    # 规范化数据
    print(f"[INFO] 规范化数据...")
    cleaned_rows = []
    invalid_count = 0
    
    for idx, row in df.iterrows():
        keyword = str(row['Keyword']).strip()
        cat_id_raw = str(row['CatID']).strip()
        
        # 跳过空行
        if not keyword or not cat_id_raw:
            continue
        
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
            # 无效的 CatID，保留但标记
            invalid_count += 1
            if invalid_count <= 10:
                print(f"[WARNING] 无效的 CatID: {keyword} -> {cat_id_raw}")
            cleaned_rows.append({
                'Keyword': keyword,
                'CatID': cat_id_upper  # 至少转大写
            })
    
    if invalid_count > 10:
        print(f"[WARNING] 还有 {invalid_count - 10} 个无效的 CatID")
    
    # 创建新的 DataFrame
    new_df = pd.DataFrame(cleaned_rows)
    
    # 保存（带表头）
    print(f"[INFO] 保存标准化后的 CSV...")
    new_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    print(f"[INFO] ✅ 标准化完成！")
    print(f"   原始行数: {len(df)}")
    print(f"   清理后行数: {len(new_df)}")
    print(f"   无效 CatID: {invalid_count}")
    print(f"   文件已保存: {csv_path}")


if __name__ == "__main__":
    try:
        standardize_alias_csv()
    except Exception as e:
        print(f"[ERROR] 标准化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

