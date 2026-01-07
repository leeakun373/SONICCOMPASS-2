"""
生成 rules.json 文件
从 ucs_catid_list.csv 读取真实数据，生成关键词到 CatID 的映射规则
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


def generate_rules_json():
    """
    从 ucs_catid_list.csv 生成 rules.json
    
    流程：
    1. 读取 data_config/ucs_catid_list.csv
    2. 验证所有 CatID 存在
    3. 根据关键词映射到真实的 CatID
    4. 生成 data_config/rules.json
    """
    config_dir = Path(__file__).parent.parent / "data_config"
    csv_path = config_dir / "ucs_catid_list.csv"
    output_path = config_dir / "rules.json"
    
    if not csv_path.exists():
        print(f"[ERROR] CSV 文件不存在: {csv_path}")
        sys.exit(1)
    
    print(f"[INFO] 读取 CSV 文件: {csv_path}")
    
    # 读取 CSV
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except:
        df = pd.read_csv(csv_path, encoding='latin1')
    
    # 清洗列名
    df.columns = [c.strip() for c in df.columns]
    
    # 验证必需的列
    required_columns = ["Category", "SubCategory", "CatID", "CatShort"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"[ERROR] CSV 缺少必需的列: {', '.join(missing_columns)}")
        sys.exit(1)
    
    # 构建 CatID 查找表（验证所有 CatID 存在）
    valid_catids = set()
    catid_to_info = {}
    
    for _, row in df.iterrows():
        cat_id = str(row.get('CatID', '')).strip()
        category = str(row.get('Category', '')).strip()
        subcategory = str(row.get('SubCategory', '')).strip()
        cat_short = str(row.get('CatShort', '')).strip()
        
        if cat_id:
            valid_catids.add(cat_id)
            catid_to_info[cat_id] = {
                'category': category,
                'subcategory': subcategory,
                'cat_short': cat_short
            }
    
    print(f"[INFO] 找到 {len(valid_catids)} 个有效的 CatID")
    
    # 定义关键词到 CatID 的映射规则
    # 基于 CSV 中的真实数据
    rules = {
        # WEAPONS 系列
        'WEAPON': 'WEAPMisc',
        'SWORD': 'WEAPSwrd',
        'BLADE': 'WEAPSwrd',
        'KNIFE': 'WEAPKnif',
        'BOW': 'WEAPBow',
        'ARROW': 'WEAPArro',
        'AXE': 'WEAPAxe',
        'ARMOR': 'WEAPArmr',
        'WHIP': 'WEAPWhip',
        'POLEARM': 'WEAPPole',
        'SIEGE': 'WEAPSiege',
        'BLUNT': 'WEAPBlnt',
        
        # GUNS 系列
        'GUN': 'GUNMisc',
        'FIREARM': 'GUNMisc',
        'PISTOL': 'GUNPis',
        'RIFLE': 'GUNRif',
        'SHOTGUN': 'GUNShotg',
        'AUTOMATIC': 'GUNAuto',
        'MACHINE': 'GUNAuto',
        
        # EXPLOSIONS 系列
        'EXPLOSION': 'EXPLMisc',
        'BLAST': 'EXPLMisc',
        'BOMB': 'EXPLReal',
        
        # MAGIC 系列
        'MAGIC': 'MAGSpel',
        'SPELL': 'MAGSpel',
        'ELEMENT': 'MAGElem',
        'ELEMENTAL': 'MAGElem',
        'SORCERY': 'MAGSpel',
        'SUPERNATURAL': 'MAGMisc',
        
        # ICE 系列
        'ICE': 'ICEMisc',
        'FROZEN': 'ICEMisc',
        'BREAK': 'ICEBrk',
        'CRASH': 'ICECrsh',
        
        # WATER 系列
        'WATER': 'WATRMisc',
        'LIQUID': 'WATRMisc',
        'SPLASH': 'WATRMisc',
        'OCEAN': 'WATRWave',
        'BUBBLE': 'WATRMisc',
        
        # LASERS 系列
        'LASER': 'LASRMisc',
        'LASER GUN': 'LASRGun',
        'BLASTER': 'LASRGun',
        
        # SCIFI 系列
        'SCIFI': 'SCIMisc',
        'SCI-FI': 'SCIMisc',
        'ROBOT': 'SCIMisc',
        'FUTURISTIC': 'SCIMisc',
        'CYBER': 'SCIMisc',
        
        # FIRE 系列
        'FIRE': 'FIREMisc',
        'BURNING': 'FIREBurn',
        'FLAME': 'FIREBurn',
        
        # WEATHER 系列
        'RAIN': 'RAIN',  # CatID 就是 RAIN
        'THUNDER': 'THUN',
        'STORM': 'STORM',
        
        # AMBIENCE 系列
        'WIND': 'WINDTurb',  # 使用 TURBULENT 作为默认
        'AMBIENCE': 'AMBForst',
        'ATMOSPHERE': 'AMBForst',
        'FOREST': 'AMBForst',
        'NATURE': 'AMBForst',
        
        # FOLEY 系列
        'FOOTSTEP': 'FOLYFeet',
        'WALK': 'FOLYFeet',
        'CLOTH': 'FOLYClth',
        'MOVEMENT': 'FOLYFeet',
        
        # UI 系列
        'UI': 'UIMisc',
        'BUTTON': 'UIMisc',
        'CLICK': 'UIClick',
        'INTERFACE': 'UIMisc',
        'MENU': 'UIMisc',
        
        # AIRCRAFT 系列
        'AIRCRAFT': 'AEROJet',
        'PLANE': 'AEROJet',
        'JET': 'AEROJet',
        'HELICOPTER': 'AEROHeli',
        
        # METAL 系列
        'METAL': 'METLImpt',
        'METALLIC': 'METLImpt',
        
        # WOOD 系列
        'WOOD': 'WOODImpt',
        'WOODEN': 'WOODImpt',
        
        # GLASS 系列
        'GLASS': 'GLASImpt',
        
        # VEHICLES 系列
        'VEHICLE': 'VEHMisc',
        'CAR': 'VEHCar',
        'ENGINE': 'VEHMisc',
        
        # VOICE 系列
        'VOICE': 'VOXScrm',
        'VOCAL': 'VOXScrm',
        'SHOUT': 'VOXScrm',
        
        # SWOOSHES 系列
        'WHOOSH': 'WHSH',
        'SWISH': 'SWSH',
    }
    
    # 验证所有 CatID 都存在
    invalid_catids = []
    for keyword, cat_id in rules.items():
        if cat_id not in valid_catids:
            invalid_catids.append((keyword, cat_id))
    
    if invalid_catids:
        print(f"[WARNING] 发现 {len(invalid_catids)} 个无效的 CatID:")
        for keyword, cat_id in invalid_catids:
            print(f"  {keyword} -> {cat_id} (不存在)")
        print("\n[INFO] 将从规则中移除无效的 CatID")
        # 移除无效的规则
        for keyword, cat_id in invalid_catids:
            del rules[keyword]
    
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

