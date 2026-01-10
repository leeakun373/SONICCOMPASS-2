"""
Category 颜色映射器
简化版：CatID → 主类别（82个）→ 颜色
"""

import hashlib
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QColor


class CategoryColorMapper:
    """
    Category 颜色映射器 - 简化版
    
    核心逻辑：
    1. 从 CSV 加载 CatID → 主类别（Category）映射
    2. 为 82 个主类别生成唯一颜色
    3. 查询时：CatID → 主类别 → 颜色
    
    这样确保同一主类别下的所有 CatID 使用相同颜色。
    """
    
    def __init__(self, config_dir="data_config"):
        """初始化颜色映射器"""
        self.config_dir = Path(config_dir)
        self.csv_path = self.config_dir / "ucs_catid_list.csv"
        
        # 核心映射表
        self.catid_to_category: Dict[str, str] = {}  # CatID -> 主类别名 (如 "AIRBLOW" -> "AIR")
        self.category_to_color: Dict[str, QColor] = {}  # 主类别名 -> 颜色 (如 "AIR" -> Green)
        
        self._load_data()
    
    def _generate_category_color(self, category: str, index: int, total: int) -> QColor:
        """
        为主类别生成确定性颜色
        
        使用黄金分割角度分布，确保相邻类别颜色差异明显
        """
        # 黄金分割角度（约 137.508°）
        golden_angle = 137.508
        
        # 基于索引计算色相，使用黄金分割确保均匀分布
        hue = (index * golden_angle) % 360
        
        # 固定饱和度和亮度，确保颜色鲜艳
        saturation = 200  # 高饱和度
        value = 220  # 中高亮度
        
        return QColor.fromHsv(int(hue), saturation, value)
    
    def _load_data(self):
        """加载 CSV 并建立映射"""
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
            
            # 清洗列名
            df.columns = [c.strip() for c in df.columns]
            
            # 第一步：收集所有唯一的主类别
            unique_categories = set()
            for _, row in df.iterrows():
                if 'Category' in row:
                    cat = str(row['Category']).strip().upper()
                    if cat:
                        unique_categories.add(cat)
            
            # 第二步：为 82 个主类别分配颜色（按字母顺序，确保确定性）
            sorted_categories = sorted(unique_categories)
            total = len(sorted_categories)
            
            for idx, category in enumerate(sorted_categories):
                self.category_to_color[category] = self._generate_category_color(category, idx, total)
            
            # 第三步：建立 CatID → 主类别 映射
            for _, row in df.iterrows():
                cat_id = str(row.get('CatID', '')).strip().upper()
                category = str(row.get('Category', '')).strip().upper()
                
                if cat_id and category:
                    self.catid_to_category[cat_id] = category
                    
                # 同时把主类别名也作为键（方便直接用主类别查颜色）
                if category:
                    self.catid_to_category[category] = category
            
            print(f"[INFO] Color Mapper: 已加载 {len(self.catid_to_category)} 个 CatID 映射")
            print(f"[INFO] Color Mapper: 已生成 {len(self.category_to_color)} 个主类别颜色")
            
        except Exception as e:
            print(f"[ERROR] Color Mapper Load Error: {e}")
            import traceback
            traceback.print_exc()
    
    def get_color(self, key: Optional[str]) -> QColor:
        """
        获取颜色
        
        流程：key（CatID 或主类别名）→ 主类别 → 颜色
        
        Args:
            key: CatID (如 "AIRBlow") 或主类别名 (如 "AIR")
            
        Returns:
            QColor 对象
        """
        if not key:
            return QColor('#333333')
        
        # 规范化：去除空白并转大写
        normalized_key = str(key).strip().upper()
        
        # UNCATEGORIZED 返回灰色
        if not normalized_key or normalized_key == "UNCATEGORIZED":
            return QColor('#333333')
        
        # 第一步：通过 CatID 查找主类别
        category = self.catid_to_category.get(normalized_key)
        
        # 第二步：如果没找到，尝试前缀匹配（如 "AIRBLOW" 尝试 "AIR"）
        if not category and len(normalized_key) >= 3:
            # 尝试常见的前缀长度（3, 4, 5）
            for prefix_len in [3, 4, 5]:
                if prefix_len <= len(normalized_key):
                    prefix = normalized_key[:prefix_len]
                    if prefix in self.catid_to_category:
                        category = self.catid_to_category[prefix]
                        break
        
        # 第三步：查找主类别的颜色
        if category and category in self.category_to_color:
            return self.category_to_color[category]
        
        # 第四步：如果主类别也没有颜色，使用哈希兜底
        # 确保同一个 key 总是返回相同颜色
        hash_obj = hashlib.md5(normalized_key.encode('utf-8'))
        hash_val = int(hash_obj.hexdigest(), 16)
        return QColor.fromHsv(abs(hash_val) % 360, 200, 220)
    
    # 向后兼容方法
    def get_color_for_catid(self, catid: Optional[str], filename: Optional[str] = None) -> QColor:
        """向后兼容"""
        return self.get_color(catid)
    
    def get_color_by_category(self, category: Optional[str], subcategory: Optional[str] = None) -> QColor:
        """向后兼容"""
        return self.get_color(category)
    
    def get_color_for_category(self, category: Optional[str]) -> QColor:
        """向后兼容"""
        return self.get_color(category)
    
    def get_category_from_catid(self, catid: Optional[str]) -> Optional[str]:
        """从 CatID 获取主类别名"""
        if not catid:
            return None
        normalized = str(catid).strip().upper()
        return self.catid_to_category.get(normalized)
