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
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # 清洗列名空格
                reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
                
                for row in reader:
                    # 获取关键字段
                    cat_id = row.get('CatID', '').strip()     # WPNGun
                    cat_short = row.get('CatShort', '').strip() # WPN
                    
                    # 确定颜色 (使用 CatShort 映射到固定色盘)
                    # 如果 CSV 里有 Color 列更好，没有的话根据 Short 查 fallback
                    color_hex = self.fallback_colors.get(cat_short, '#808080')
                    
                    if cat_id:
                        self.catid_to_color[cat_id] = QColor(color_hex)
                    if cat_short:
                        self.short_to_color[cat_short] = QColor(color_hex)
                        
            print(f"[INFO] Color Mapper: Loaded {len(self.catid_to_color)} CatIDs, {len(self.short_to_color)} Codes")
            
        except Exception as e:
            print(f"[ERROR] Color Mapper Load Error: {e}")
            import traceback
            traceback.print_exc()
    
    def get_color(self, key: Optional[str]) -> QColor:
        """
        万能取色：支持 CatID (WPNGun) 和 Code (WPN)
        
        Args:
            key: CatID (如 "WPNGun") 或 Code (如 "WPN")
            
        Returns:
            QColor 对象
        """
        if not key:
            return QColor('#333333')
            
        # 1. 尝试 CatID 直接匹配
        if key in self.catid_to_color:
            return self.catid_to_color[key]
            
        # 2. 尝试 Code 匹配
        if key in self.short_to_color:
            return self.short_to_color[key]
            
        # 3. 尝试截取前缀 (WPNGun -> WPN)
        if len(key) >= 3:
            prefix = key[:3].upper()
            if prefix in self.short_to_color:
                return self.short_to_color[prefix]
        
        # 4. Hash 兜底 (避免全红，至少能区分不同)
        hash_val = hash(key)
        return QColor.fromHsv(abs(hash_val) % 360, 200, 230)
    
    # 向后兼容方法
    def get_color_for_catid(self, catid: Optional[str], filename: Optional[str] = None) -> QColor:
        """向后兼容：get_color_for_catid 调用 get_color"""
        return self.get_color(catid)
    
    def get_color_for_category(self, category: Optional[str]) -> QColor:
        """向后兼容：get_color_for_category 调用 get_color"""
        return self.get_color(category)
    
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
