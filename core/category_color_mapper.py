"""
Category 颜色映射器
基于 UCS Category 大类分配颜色
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QColor
import hashlib


class CategoryColorMapper:
    """Category 颜色映射器 - 基于 UCS Category 大类"""
    
    # 黄金分割比例常数
    GOLDEN_RATIO = 0.618033988749895
    
    # 固定的饱和度和明度
    FIXED_SATURATION = 0.75
    FIXED_VALUE = 0.90  # 从 0.85 提升到 0.90，保证亮度
    
    def __init__(self, ucs_csv_path: str = "data_config/ucs_catid_list.csv"):
        """
        初始化颜色映射器
        
        Args:
            ucs_csv_path: UCS 分类列表 CSV 文件路径
        """
        self.ucs_csv_path = Path(ucs_csv_path)
        self.catid_to_category: Dict[str, str] = {}
        self.catid_to_subcategory: Dict[str, str] = {}
        self.category_colors: Dict[str, QColor] = {}
        self._load_mapping()
    
    def _load_mapping(self):
        """加载 CatID 到 Category 和 SubCategory 的映射"""
        if not self.ucs_csv_path.exists():
            print(f"[WARNING] UCS CSV 文件不存在: {self.ucs_csv_path}")
            return
        
        try:
            df = pd.read_csv(self.ucs_csv_path, encoding='utf-8')
            # 构建 CatID -> Category 和 SubCategory 映射
            for _, row in df.iterrows():
                catid = str(row.get('CatID', '')).strip()
                category = str(row.get('Category', '')).strip()
                subcategory = str(row.get('SubCategory', '')).strip()
                if catid and category:
                    self.catid_to_category[catid] = category
                    if subcategory:
                        self.catid_to_subcategory[catid] = subcategory
                    # 为每个 Category 分配颜色（使用黄金分割算法）
                    if category not in self.category_colors:
                        self.category_colors[category] = self._generate_golden_ratio_color(category)
        except Exception as e:
            print(f"[ERROR] 加载 UCS 映射失败: {e}")
    
    def get_category_from_catid(self, catid: Optional[str]) -> Optional[str]:
        """
        从 CatID 获取 Category 名称
        
        Args:
            catid: CatID（如 "AMBForst"）
            
        Returns:
            Category 名称（如 "AMBIENCE"），如果未找到则返回 None
        """
        if not catid:
            return None
        
        # 直接查找
        if catid in self.catid_to_category:
            return self.catid_to_category[catid]
        
        # 尝试前3字符匹配（向后兼容）
        prefix = catid[:3].upper() if len(catid) >= 3 else catid.upper()
        # 查找以该前缀开头的 CatID
        for cid, cat in self.catid_to_category.items():
            if cid.startswith(prefix):
                return cat
        
        return None
    
    def get_subcategory_from_catid(self, catid: Optional[str]) -> Optional[str]:
        """
        从 CatID 获取 SubCategory 名称
        
        Args:
            catid: CatID（如 "AMBForst"）
            
        Returns:
            SubCategory 名称（如 "FOREST"），如果未找到则返回 None
        """
        if not catid:
            return None
        
        # 直接查找
        if catid in self.catid_to_subcategory:
            return self.catid_to_subcategory[catid]
        
        # 尝试前3字符匹配（向后兼容）
        prefix = catid[:3].upper() if len(catid) >= 3 else catid.upper()
        # 查找以该前缀开头的 CatID
        for cid, subcat in self.catid_to_subcategory.items():
            if cid.startswith(prefix):
                return subcat
        
        return None
    
    def _generate_golden_ratio_color(self, category: str) -> QColor:
        """
        使用黄金分割算法生成颜色
        
        Args:
            category: Category 名称
            
        Returns:
            QColor 对象
        """
        # 特殊处理 UNCATEGORIZED
        if category == "UNCATEGORIZED":
            return QColor('#333333')  # 深灰色，不抢眼
        
        # 计算哈希值
        hash_value = int(hashlib.md5(category.encode('utf-8')).hexdigest(), 16)
        
        # 使用黄金分割算法计算色相
        # Hue = (hash(category) * 0.618033988749895) % 1.0
        hue = (hash_value * self.GOLDEN_RATIO) % 1.0
        
        # 固定饱和度和明度
        saturation = self.FIXED_SATURATION
        value = self.FIXED_VALUE
        
        # 使用HSV生成颜色（Qt的HSV范围是0-1）
        return QColor.fromHsvF(hue, saturation, value)
    
    def get_color_for_category(self, category: Optional[str]) -> QColor:
        """
        根据 Category 名称获取颜色
        
        Args:
            category: Category 名称（如 "AMBIENCE"）
            
        Returns:
            QColor 对象
        """
        if not category:
            return QColor('#333333')  # 默认深灰色（UNCATEGORIZED）
        
        # 特殊处理 UNCATEGORIZED
        if category == "UNCATEGORIZED":
            return QColor('#333333')
        
        # 查找已分配的颜色
        if category in self.category_colors:
            return self.category_colors[category]
        
        # 如果未找到，使用黄金分割算法生成新颜色
        color = self._generate_golden_ratio_color(category)
        self.category_colors[category] = color
        return color
    
    def get_color_for_catid(self, catid: Optional[str]) -> QColor:
        """
        根据 CatID 获取颜色（通过 Category）
        
        Args:
            catid: CatID（如 "AMBForst"）
            
        Returns:
            QColor 对象
        """
        category = self.get_category_from_catid(catid)
        return self.get_color_for_category(category)

