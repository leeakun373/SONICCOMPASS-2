"""
Category 颜色映射器
彻底重构版：以 CatID 为核心
"""

import csv
import os
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QColor
import hashlib


class CategoryColorMapper:
    """Category 颜色映射器 - 以 CatID 为核心"""
    
    # 黄金分割比例常数
    GOLDEN_RATIO = 0.618033988749895
    
    def __init__(self, config_dir="data_config"):
        """
        初始化颜色映射器
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = Path(config_dir)
        self.csv_path = self.config_dir / "ucs_catid_list.csv"
        self.catid_to_color: Dict[str, QColor] = {}  # WPNGun -> Red
        self.short_to_color: Dict[str, QColor] = {}  # WPN -> Red
        
        # 默认 UCS 82 色盘 (作为 CSV 加载失败的兜底)
        self.fallback_colors = {
            'WPN': '#E60000', 'AIR': '#00CC00', 'AMB': '#009900', 'BIO': '#006600',
            'CERM': '#FFFF00', 'DESTR': '#FF9900', 'DSGN': '#666666', 'ELEC': '#0000FF',
            'FIRE': '#FF3300', 'FOLEY': '#808080', 'GLAS': '#CCFFFF', 'ICE': '#00FFFF',
            'LIQUID': '#0099FF', 'MAG': '#9900CC', 'MECH': '#663300', 'METL': '#999999',
            'MUS': '#FF00FF', 'PAPER': '#FFFFCC', 'ROCK': '#663333', 'SCI': '#3333FF',
            'UI': '#FFFF00', 'VEH': '#003366', 'VOX': '#FFCCCC', 'WAT': '#0066FF',
            'WOOD': '#996633', 'AERO': '#00AAFF', 'WEA': '#3399FF', 'FOL': '#CC9900',
            'IMPT': '#FF6600', 'SWSH': '#FF00CC', 'UNCATEGORIZED': '#333333'
        }
        
        self._load_data()
    
    def _load_data(self):
        """加载 CSV 并建立全量索引"""
        if not self.csv_path.exists():
            print(f"[ERROR] Color Mapper: CSV not found at {self.csv_path}")
            return

        try:
            import pandas as pd
            # 尝试读取，兼容编码
            try:
                df = pd.read_csv(self.csv_path, encoding='utf-8')
            except:
                df = pd.read_csv(self.csv_path, encoding='latin1')
            
            # 清洗列名 (去空格)
            df.columns = [c.strip() for c in df.columns]
            
            # 打印一下列名，确保我们要找的 Category 在里面
            # print(f"[DEBUG] CSV Columns: {df.columns.tolist()}")

            for _, row in df.iterrows():
                # 1. 确定颜色
                # 这里暂时还得依靠 CatShort/Code 来从 fallback 字典取色
                # 但建立了索引后，后面查的时候就可以用全名了
                short = str(row.get('CatShort', '')).strip()
                color_hex = self.fallback_colors.get(short, '#808080')
                color = QColor(color_hex)
                
                # 2. 【核心】把大类全名 (第一列 Category) 注册进去
                # 例如: "USER INTERFACE" -> 黄色
                if 'Category' in row:
                    cat_name = str(row['Category']).strip().upper() # 转大写统一
                    self.short_to_color[cat_name] = color
                    
                # 3. 把 CatID 也注册进去 (UIBttn -> 黄色)
                if 'CatID' in row:
                    cat_id = str(row['CatID']).strip()
                    self.catid_to_color[cat_id] = color
                
                # 4. 把 CatShort 也注册进去 (UI -> 黄色)
                if short:
                    self.short_to_color[short] = color

            # 验证唯一主类别数量（应该约82个）
            # 从 short_to_color 中提取所有 Category 列的值（去除 CatShort）
            # 注意：short_to_color 中可能包含 Category 名称和 CatShort，需要区分
            # 简单方法：统计所有长度 > 3 的键（Category 名称通常较长）
            category_names = set()
            for key in self.short_to_color.keys():
                # Category 名称通常较长（如 "USER INTERFACE"），CatShort 通常很短（如 "UI"）
                # 但这不是绝对可靠的，更好的方法是直接从 CSV 的 Category 列提取
                if len(key) > 3 and ' ' in key:  # 包含空格的大概率是 Category 名称
                    category_names.add(key)
            
            # 更准确的方法：重新读取 CSV 的 Category 列
            try:
                df_categories = df['Category'].dropna().unique()
                unique_categories = set()
                for cat in df_categories:
                    cat_clean = str(cat).strip().upper()
                    if cat_clean:
                        unique_categories.add(cat_clean)
                print(f"[INFO] Color Mapper: 已索引 {len(self.catid_to_color)} 个 CatID, {len(self.short_to_color)} 个键")
                print(f"[INFO] Color Mapper: 唯一主类别数量: {len(unique_categories)} 个")
                if len(unique_categories) > 90:
                    print(f"[WARNING] 主类别数量异常 ({len(unique_categories)})，预期约82个")
                    print(f"   前20个主类别: {list(sorted(unique_categories))[:20]}")
                elif len(unique_categories) < 70:
                    print(f"[WARNING] 主类别数量过少 ({len(unique_categories)})，预期约82个")
            except Exception as e2:
                print(f"[WARNING] 无法验证主类别数量: {e2}")
            
        except Exception as e:
            print(f"[ERROR] Color Mapper Load Error: {e}")
            import traceback
            traceback.print_exc()
    
    def get_color(self, key: Optional[str]) -> QColor:
        """
        万能取色：支持 CatID (WPNGun) 和 Code (WPN)，支持 Category-SubCategory 格式
        
        Args:
            key: CatID (如 "WPNGun") 或 Code (如 "WPN") 或 "Category-SubCategory" 格式
            
        Returns:
            QColor 对象
        """
        if not key:
            return QColor('#333333')
        
        # 规范化：去除空白并转大写（使用副本，不修改原始输入）
        normalized_key = str(key).strip().upper()
        
        # 如果严格是 "UNCATEGORIZED" 或空，返回灰色
        if not normalized_key or normalized_key == "UNCATEGORIZED":
            return QColor('#333333')
        
        # 检查是否包含分隔符（Category-SubCategory 格式）
        separator = None
        if '-' in normalized_key:
            separator = '-'
        elif '_' in normalized_key:
            separator = '_'
        
        if separator:
            # 分割为 MainCategory 和 SubCategory
            parts = normalized_key.split(separator, 1)
            main_category = parts[0].strip()
            sub_category = parts[1].strip() if len(parts) > 1 else ""
            
            # 回退链：1) 精确匹配 "WEAPONS-GUN" -> 2) 匹配 SubCategory "GUN" -> 3) 匹配 MainCategory "WEAPONS"
            # 1. 尝试精确匹配完整字符串
            if normalized_key in self.short_to_color:
                return self.short_to_color[normalized_key]
            
            # 2. 尝试匹配 SubCategory
            if sub_category:
                if sub_category in self.short_to_color:
                    return self.short_to_color[sub_category]
                # 尝试截取 SubCategory 前缀
                if len(sub_category) >= 3:
                    prefix = sub_category[:3]
                    if prefix in self.short_to_color:
                        return self.short_to_color[prefix]
            
            # 3. 回退到 MainCategory
            if main_category:
                if main_category in self.short_to_color:
                    return self.short_to_color[main_category]
                # 尝试截取 MainCategory 前缀
                if len(main_category) >= 3:
                    prefix = main_category[:3]
                    if prefix in self.short_to_color:
                        return self.short_to_color[prefix]
        else:
            # 没有分隔符，使用原有逻辑
            # 1. 尝试 CatID 直接匹配（大小写不敏感）
            if normalized_key in self.catid_to_color:
                return self.catid_to_color[normalized_key]
                
            # 2. 尝试 Code 匹配（大小写不敏感）
            if normalized_key in self.short_to_color:
                return self.short_to_color[normalized_key]
                
            # 3. 尝试截取前缀 (WPNGun -> WPN)
            if len(normalized_key) >= 3:
                prefix = normalized_key[:3]
                if prefix in self.short_to_color:
                    return self.short_to_color[prefix]
        
        # 4. Hash 兜底：对字符串进行哈希生成确定性稳定颜色
        # 使用 hashlib 确保跨会话的一致性
        hash_obj = hashlib.md5(normalized_key.encode('utf-8'))
        hash_val = int(hash_obj.hexdigest(), 16)
        return QColor.fromHsv(abs(hash_val) % 360, 200, 230)
    
    # 向后兼容方法
    def get_color_for_catid(self, catid: Optional[str], filename: Optional[str] = None) -> QColor:
        """向后兼容：get_color_for_catid 调用 get_color"""
        return self.get_color(catid)
    
    def get_color_by_category(self, category: Optional[str], subcategory: Optional[str] = None) -> QColor:
        """
        根据 Category 和 SubCategory 获取颜色（大小写不敏感，支持回退机制）
        支持 Category-SubCategory 格式的自动分割
        
        Args:
            category: 主类别（如 "WEAPONS"）或 "Category-SubCategory" 格式
            subcategory: 子类别（如 "GUN"），可选（如果 category 已包含分隔符，此参数会被忽略）
            
        Returns:
            QColor 对象
        """
        if not category:
            return QColor('#333333')
        
        # 规范化：去除空白并转大写（使用副本）
        normalized_cat = str(category).strip().upper()
        normalized_sub = str(subcategory).strip().upper() if subcategory else ""
        
        # 如果严格是 "UNCATEGORIZED" 或空，返回灰色
        if not normalized_cat or normalized_cat == "UNCATEGORIZED":
            return QColor('#333333')
        
        # 检查 category 是否包含分隔符（Category-SubCategory 格式）
        separator = None
        if '-' in normalized_cat:
            separator = '-'
        elif '_' in normalized_cat:
            separator = '_'
        
        if separator:
            # 自动分割 Category-SubCategory 格式
            parts = normalized_cat.split(separator, 1)
            normalized_cat = parts[0].strip()
            if not normalized_sub:  # 如果 subcategory 参数未提供，从 category 中提取
                normalized_sub = parts[1].strip() if len(parts) > 1 else ""
        
        # 1. 如果有子类别，先尝试匹配子类别
        if normalized_sub:
            # 尝试直接匹配子类别
            if normalized_sub in self.short_to_color:
                return self.short_to_color[normalized_sub]
            # 尝试截取前缀
            if len(normalized_sub) >= 3:
                prefix = normalized_sub[:3]
                if prefix in self.short_to_color:
                    return self.short_to_color[prefix]
        
        # 2. 回退到父类别匹配
        if normalized_cat in self.short_to_color:
            return self.short_to_color[normalized_cat]
        
        # 3. 尝试截取父类别前缀
        if len(normalized_cat) >= 3:
            prefix = normalized_cat[:3]
            if prefix in self.short_to_color:
                return self.short_to_color[prefix]
        
        # 4. Hash 兜底：对字符串进行哈希生成确定性稳定颜色
        # 使用完整的 category+subcategory 字符串确保不同组合有不同颜色
        combined_key = f"{normalized_cat}_{normalized_sub}" if normalized_sub else normalized_cat
        hash_obj = hashlib.md5(combined_key.encode('utf-8'))
        hash_val = int(hash_obj.hexdigest(), 16)
        return QColor.fromHsv(abs(hash_val) % 360, 200, 230)
    
    def get_color_for_category(self, category: Optional[str]) -> QColor:
        """向后兼容：get_color_for_category 调用 get_color_by_category"""
        return self.get_color_by_category(category)
    
    def get_category_from_catid(self, catid: Optional[str]) -> Optional[str]:
        """
        向后兼容：从 CatID 获取 Category 名称
        注意：这个方法现在只做简单的前缀匹配，完整信息应该通过 UCSManager 获取
        """
        if not catid:
            return None
        
        # 尝试通过前缀匹配找到对应的 Code，然后查找 fallback_colors
        if len(catid) >= 3:
            prefix = catid[:3].upper()
            if prefix in self.fallback_colors:
                # 这里返回 Code，实际应该通过 UCSManager 获取完整 Category 名称
                return prefix
        
        return None
