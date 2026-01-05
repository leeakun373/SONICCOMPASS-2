"""
UCS (Universal Category System) 管理器
负责UCS分类系统的核心功能：CatID映射、别名解析等
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


class UCSError(Exception):
    """UCS相关错误"""
    pass


@dataclass
class UCSCategory:
    """UCS分类信息"""
    category: str
    subcategory: str
    cat_id: str
    cat_short: str
    explanations: str
    synonyms: list
    category_zh: str
    subcategory_zh: str
    synonyms_zh: list
    
    @property
    def full_category(self) -> str:
        """获取完整分类名称 (Category-SubCategory)"""
        return f"{self.category}-{self.subcategory}"
    
    @property
    def full_category_zh(self) -> str:
        """获取完整分类名称（中文）"""
        return f"{self.category_zh}-{self.subcategory_zh}"


class UCSManager:
    """UCS管理器"""
    
    def __init__(self, config_dir: str = "data_config"):
        """
        初始化UCS管理器
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = Path(config_dir)
        
        # CatID -> UCSCategory 映射
        self.catid_to_category: Dict[str, UCSCategory] = {}
        
        # FullCategory -> CatID 映射
        self.fullcategory_to_catid: Dict[str, str] = {}
        
        # 别名 -> CatID 映射（小写，用于不区分大小写的查找）
        self.alias_to_catid: Dict[str, str] = {}
        
        # CatID -> 别名列表 映射（用于反向查找）
        self.catid_to_aliases: Dict[str, list] = {}
        
        # 【754 CatID Source of Truth】CatID 查找表
        # 格式: "AIRBlow": {"category": "AIR", "subcategory": "BLOW", "name": "AIR - BLOW"}
        # 使用 CatShort 作为 category（因为 Color Mapper 认这个）
        self.catid_lookup: Dict[str, Dict[str, str]] = {}
    
    def load_all(self) -> None:
        """加载所有UCS相关配置文件"""
        try:
            self.load_catid_list()
            self.load_alias_list()
        except Exception as e:
            raise UCSError(f"加载UCS配置失败: {e}") from e
    
    def load_catid_list(self) -> None:
        """加载UCS CatID列表文件"""
        file_path = self.config_dir / "ucs_catid_list.csv"
        
        if not file_path.exists():
            raise UCSError(f"UCS CatID列表文件不存在: {file_path}")
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 验证必需的列
            required_columns = ["Category", "SubCategory", "CatID", "CatShort"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise UCSError(f"UCS CatID列表文件缺少必需的列: {', '.join(missing_columns)}")
            
            self.catid_to_category = {}
            self.fullcategory_to_catid = {}
            
            for _, row in df.iterrows():
                category = str(row["Category"]).strip()
                subcategory = str(row["SubCategory"]).strip()
                cat_id = str(row["CatID"]).strip()
                cat_short = str(row.get("CatShort", "")).strip()
                explanations = str(row.get("Explanations", "")).strip()
                
                # 解析同义词
                synonyms_str = str(row.get("Synonyms - Comma Separated", "")).strip()
                synonyms = [s.strip() for s in synonyms_str.split(",") if s.strip()]
                
                category_zh = str(row.get("Category_zh", "")).strip()
                subcategory_zh = str(row.get("SubCategory_zh", "")).strip()
                synonyms_zh_str = str(row.get("Synonyms_zh", "")).strip()
                synonyms_zh = [s.strip() for s in synonyms_zh_str.split(",") if s.strip()]
                
                ucs_category = UCSCategory(
                    category=category,
                    subcategory=subcategory,
                    cat_id=cat_id,
                    cat_short=cat_short,
                    explanations=explanations,
                    synonyms=synonyms,
                    category_zh=category_zh,
                    subcategory_zh=subcategory_zh,
                    synonyms_zh=synonyms_zh
                )
                
                # 构建映射
                self.catid_to_category[cat_id] = ucs_category
                full_category = ucs_category.full_category
                self.fullcategory_to_catid[full_category] = cat_id
                
                # 【754 CatID Source of Truth】构建 CatID 查找表
                # 使用 CatShort 作为 category（因为 Color Mapper 认这个）
                self.catid_lookup[cat_id] = {
                    "category": cat_short if cat_short else category,  # 优先使用 CatShort
                    "subcategory": subcategory,
                    "name": f"{category} - {subcategory}"
                }
                
        except pd.errors.EmptyDataError:
            raise UCSError("UCS CatID列表文件为空")
        except Exception as e:
            raise UCSError(f"加载UCS CatID列表失败: {e}") from e
    
    def load_alias_list(self) -> None:
        """加载UCS别名列表文件"""
        file_path = self.config_dir / "ucs_alias.csv"
        
        if not file_path.exists():
            # 别名文件不是必需的，如果不存在则只记录警告
            print(f"警告: UCS别名文件不存在: {file_path}，将跳过别名加载")
            return
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 验证必需的列
            if df.empty:
                print("警告: UCS别名文件为空")
                return
            
            # 假设格式为: alias,catid 或 keyword,catid
            # 检查列名
            columns = df.columns.tolist()
            if len(columns) < 2:
                raise UCSError("UCS别名文件格式错误：需要至少2列")
            
            alias_col = columns[0]
            catid_col = columns[1]
            
            self.alias_to_catid = {}
            self.catid_to_aliases = {}
            
            for _, row in df.iterrows():
                alias = str(row[alias_col]).strip().lower()  # 转换为小写以便不区分大小写查找
                catid = str(row[catid_col]).strip()
                
                if alias and catid:
                    # 别名 -> CatID 映射
                    self.alias_to_catid[alias] = catid
                    
                    # CatID -> 别名列表 映射
                    if catid not in self.catid_to_aliases:
                        self.catid_to_aliases[catid] = []
                    if alias not in self.catid_to_aliases[catid]:
                        self.catid_to_aliases[catid].append(alias)
                        
        except pd.errors.EmptyDataError:
            print("警告: UCS别名文件为空")
        except Exception as e:
            raise UCSError(f"加载UCS别名列表失败: {e}") from e
    
    def _find_catid_by_short_name(self, short_name: str) -> Optional[str]:
        """
        根据简短名称（如"weapon", "sword"）查找对应的CatID
        
        Args:
            short_name: 简短名称
            
        Returns:
            对应的CatID，如果未找到则返回None
        """
        short_name_lower = short_name.strip().lower()
        
        # 首先尝试在CatShort中精确匹配
        for cat_id, category in self.catid_to_category.items():
            if category.cat_short.lower() == short_name_lower:
                return cat_id
        
        # 尝试在完整分类名称中查找（Category或SubCategory）
        for cat_id, category in self.catid_to_category.items():
            if (category.category.lower() == short_name_lower or 
                category.subcategory.lower() == short_name_lower):
                return cat_id
        
        # 尝试在同义词中查找（精确匹配）
        for cat_id, category in self.catid_to_category.items():
            for synonym in category.synonyms:
                if synonym.lower() == short_name_lower:
                    return cat_id
        
        return None
    
    def resolve_alias(self, keyword: str) -> Optional[str]:
        """
        解析别名，返回标准CatID
        
        Args:
            keyword: 输入的关键词或别名（如 "Gun"）
            
        Returns:
            对应的标准CatID（如 "WPN"），如果未找到则返回None
        """
        if not keyword:
            return None
        
        # 转换为小写进行查找
        keyword_lower = keyword.strip().lower()
        
        # 首先在别名映射中查找
        if keyword_lower in self.alias_to_catid:
            alias_result = self.alias_to_catid[keyword_lower]
            # 如果别名映射的值是简短名称（不是CatID格式），需要进一步查找
            if alias_result not in self.catid_to_category:
                # 尝试将别名映射的值作为简短名称查找
                resolved = self._find_catid_by_short_name(alias_result)
                if resolved:
                    return resolved
            else:
                return alias_result
        
        # 如果别名映射中找不到，尝试在CatID本身中查找（精确匹配）
        if keyword in self.catid_to_category:
            return keyword
        
        # 尝试在CatShort中查找（不区分大小写）
        for cat_id, category in self.catid_to_category.items():
            if category.cat_short.lower() == keyword_lower:
                return cat_id
        
        # 尝试在同义词中查找（精确匹配优先）
        for cat_id, category in self.catid_to_category.items():
            # 检查英文同义词（精确匹配）
            for synonym in category.synonyms:
                if synonym.lower() == keyword_lower:
                    return cat_id
            # 检查中文同义词（精确匹配）
            for synonym_zh in category.synonyms_zh:
                if synonym_zh.lower() == keyword_lower:
                    return cat_id
        
        # 最后尝试部分匹配（在同义词中）
        for cat_id, category in self.catid_to_category.items():
            for synonym in category.synonyms:
                if keyword_lower in synonym.lower() or synonym.lower() in keyword_lower:
                    return cat_id
        
        return None
    
    def get_category_code(self, cat_id: str) -> Optional[str]:
        """
        【754 CatID Source of Truth】获取 CatID 对应的 Category Code (CatShort)
        
        Args:
            cat_id: CatID (如 "AIRBlow")
            
        Returns:
            Category Code (CatShort, 如 "AIR")，如果未找到则返回 None
        """
        if cat_id in self.catid_lookup:
            return self.catid_lookup[cat_id].get("category")
        return None
    
    def get_subcategory_by_catid(self, cat_id: str) -> Optional[str]:
        """
        【754 CatID Source of Truth】获取 CatID 对应的 SubCategory
        
        Args:
            cat_id: CatID (如 "AIRBlow")
            
        Returns:
            SubCategory (如 "BLOW")，如果未找到则返回 None
        """
        if cat_id in self.catid_lookup:
            return self.catid_lookup[cat_id].get("subcategory")
        return None
    
    def get_catid_info(self, cat_id: str) -> Optional[Dict[str, str]]:
        """
        纯查表模式：输入 'WEAPArmr' -> 返回全名
        完全以 ucs_catid_list.csv 为准，不进行任何猜测
        """
        if not cat_id:
            return None

        # 1. 直接查 CSV 加载进来的字典
        if hasattr(self, 'catid_to_category') and cat_id in self.catid_to_category:
            cat_obj = self.catid_to_category[cat_id]
            subcategory = cat_obj.subcategory.upper() if cat_obj.subcategory else "UNKNOWN"
            return {
                'category_code': cat_obj.cat_short,      # CSV第4列: "WEAP"
                'category_name': cat_obj.category,        # CSV大类列: "WEAPONS"
                'subcategory_name': subcategory            # CSV子类列: "ARMOR" (转大写)
            }
        
        # 2. 查不到怎么办？千万别瞎猜了，直接返回原值作为兜底
        # 这样至少能在地图上看到 "WEAPArmr" 这个字，而不是错误的 "WEA"
        return {
            'category_code': cat_id,
            'category_name': cat_id,
            'subcategory_name': "UNKNOWN"
        }
    
    def get_category_by_catid(self, cat_id: str) -> Optional[UCSCategory]:
        """
        根据CatID获取分类信息
        
        Args:
            cat_id: CatID
            
        Returns:
            UCSCategory对象，如果未找到则返回None
        """
        return self.catid_to_category.get(cat_id)
    
    def get_catid_by_fullcategory(self, full_category: str) -> Optional[str]:
        """
        根据完整分类名称获取CatID
        
        Args:
            full_category: 完整分类名称，格式为 "Category-SubCategory"
            
        Returns:
            CatID，如果未找到则返回None
        """
        return self.fullcategory_to_catid.get(full_category)
    
    def get_aliases_by_catid(self, cat_id: str) -> list:
        """
        根据CatID获取所有别名
        
        Args:
            cat_id: CatID
            
        Returns:
            别名列表
        """
        return self.catid_to_aliases.get(cat_id, [])
    
    def search_categories(self, query: str, case_sensitive: bool = False) -> list:
        """
        搜索分类（在分类名称、CatID、同义词中搜索）
        
        Args:
            query: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            匹配的UCSCategory列表
        """
        if not query:
            return []
        
        query_processed = query if case_sensitive else query.lower()
        results = []
        
        for cat_id, category in self.catid_to_category.items():
            # 检查CatID
            cat_id_check = cat_id if case_sensitive else cat_id.lower()
            if query_processed in cat_id_check:
                results.append(category)
                continue
            
            # 检查完整分类名称
            full_cat = category.full_category if case_sensitive else category.full_category.lower()
            if query_processed in full_cat:
                results.append(category)
                continue
            
            # 检查同义词
            for synonym in category.synonyms:
                synonym_check = synonym if case_sensitive else synonym.lower()
                if query_processed in synonym_check:
                    results.append(category)
                    break
        
        return results


if __name__ == "__main__":
    # 测试代码
    try:
        manager = UCSManager()
        manager.load_all()
        
        print(f"加载了 {len(manager.catid_to_category)} 个UCS分类")
        print(f"加载了 {len(manager.alias_to_catid)} 个别名映射")
        
        # 测试别名解析
        test_keywords = ["gun", "weapon", "sword", "magic", "fire"]
        print("\n测试别名解析:")
        for keyword in test_keywords:
            cat_id = manager.resolve_alias(keyword)
            if cat_id:
                category = manager.get_category_by_catid(cat_id)
                if category:
                    print(f"  '{keyword}' -> {cat_id} ({category.full_category})")
                else:
                    print(f"  '{keyword}' -> {cat_id}")
            else:
                print(f"  '{keyword}' -> 未找到")
        
        # 测试获取分类信息
        if manager.catid_to_category:
            sample_cat_id = list(manager.catid_to_category.keys())[0]
            sample_category = manager.get_category_by_catid(sample_cat_id)
            if sample_category:
                print(f"\n示例分类:")
                print(f"  CatID: {sample_category.cat_id}")
                print(f"  完整分类: {sample_category.full_category}")
                print(f"  完整分类(中文): {sample_category.full_category_zh}")
                print(f"  说明: {sample_category.explanations[:50]}...")
        
    except UCSError as e:
        print(f"UCS加载错误: {e}")

