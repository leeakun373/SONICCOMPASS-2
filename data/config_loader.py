"""
配置加载模块
负责加载所有配置文件（JSON和CSV），并提供数据访问接口
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ConfigError(Exception):
    """配置加载错误"""
    pass


@dataclass
class AxisPole:
    """轴极点定义"""
    en: str
    zh: str


@dataclass
class AxisDefinition:
    """轴定义"""
    id: str
    name: Dict[str, str]  # {"en": "...", "zh": "..."}
    negative_pole: List[AxisPole]
    positive_pole: List[AxisPole]
    recommended_assets: List[str]


@dataclass
class Preset:
    """预设定义"""
    name: str
    filter_keywords: List[str]
    gravity_stakes: List[str]


@dataclass
class PillarConcept:
    """支柱概念"""
    concept: str
    keywords: List[str]


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "data_config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = Path(config_dir)
        self.axis_definitions: List[AxisDefinition] = []
        self.presets: List[Preset] = []
        self.pillars: List[PillarConcept] = []
        
    def load_all(self) -> None:
        """加载所有配置文件"""
        try:
            self.load_axis_definitions()
            self.load_presets()
            self.load_pillars()
        except Exception as e:
            raise ConfigError(f"加载配置失败: {e}") from e
    
    def load_axis_definitions(self) -> None:
        """加载轴定义文件"""
        file_path = self.config_dir / "axis_definitions.json"
        
        if not file_path.exists():
            raise ConfigError(f"轴定义文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.axis_definitions = []
            for axis_data in data.get("axes", []):
                # 解析负极点
                negative_pole = [
                    AxisPole(en=pole.get("en", ""), zh=pole.get("zh", ""))
                    for pole in axis_data.get("negative_pole", [])
                ]
                
                # 解析正极点
                positive_pole = [
                    AxisPole(en=pole.get("en", ""), zh=pole.get("zh", ""))
                    for pole in axis_data.get("positive_pole", [])
                ]
                
                axis = AxisDefinition(
                    id=axis_data.get("id", ""),
                    name=axis_data.get("name", {}),
                    negative_pole=negative_pole,
                    positive_pole=positive_pole,
                    recommended_assets=axis_data.get("recommended_assets", [])
                )
                self.axis_definitions.append(axis)
                
        except json.JSONDecodeError as e:
            raise ConfigError(f"轴定义JSON格式错误: {e}") from e
        except Exception as e:
            raise ConfigError(f"加载轴定义失败: {e}") from e
    
    def load_presets(self) -> None:
        """加载预设文件"""
        file_path = self.config_dir / "presets.json"
        
        if not file_path.exists():
            raise ConfigError(f"预设文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.presets = []
            for preset_data in data.get("presets", []):
                preset = Preset(
                    name=preset_data.get("name", ""),
                    filter_keywords=preset_data.get("filter_keywords", []),
                    gravity_stakes=preset_data.get("gravity_stakes", [])
                )
                self.presets.append(preset)
                
        except json.JSONDecodeError as e:
            raise ConfigError(f"预设JSON格式错误: {e}") from e
        except Exception as e:
            raise ConfigError(f"加载预设失败: {e}") from e
    
    def load_pillars(self) -> None:
        """加载支柱数据文件"""
        file_path = self.config_dir / "pillars_data.csv"
        
        if not file_path.exists():
            raise ConfigError(f"支柱数据文件不存在: {file_path}")
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # 验证必需的列
            if "Concept" not in df.columns or "Keywords" not in df.columns:
                raise ConfigError("支柱数据文件缺少必需的列: Concept 或 Keywords")
            
            self.pillars = []
            for _, row in df.iterrows():
                concept = str(row["Concept"]).strip()
                keywords_str = str(row["Keywords"]).strip()
                
                # 解析关键词（逗号分隔）
                keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
                
                pillar = PillarConcept(
                    concept=concept,
                    keywords=keywords
                )
                self.pillars.append(pillar)
                
        except pd.errors.EmptyDataError:
            raise ConfigError("支柱数据文件为空")
        except Exception as e:
            raise ConfigError(f"加载支柱数据失败: {e}") from e
    
    def get_axis_by_id(self, axis_id: str) -> Optional[AxisDefinition]:
        """根据ID获取轴定义"""
        for axis in self.axis_definitions:
            if axis.id == axis_id:
                return axis
        return None
    
    def get_preset_by_name(self, name: str) -> Optional[Preset]:
        """根据名称获取预设"""
        for preset in self.presets:
            if preset.name == name:
                return preset
        return None
    
    def get_pillar_by_concept(self, concept: str) -> Optional[PillarConcept]:
        """根据概念名称获取支柱"""
        for pillar in self.pillars:
            if pillar.concept.lower() == concept.lower():
                return pillar
        return None
    
    def get_all_keywords_for_pillars(self) -> List[str]:
        """获取所有支柱的关键词列表（用于语义向量生成）"""
        all_keywords = []
        for pillar in self.pillars:
            all_keywords.extend(pillar.keywords)
        # 去重并保持顺序
        return list(dict.fromkeys(all_keywords))
    
    def get_pillars_keywords_dict(self) -> Dict[str, List[str]]:
        """获取支柱概念到关键词的字典映射"""
        return {pillar.concept: pillar.keywords for pillar in self.pillars}


if __name__ == "__main__":
    # 测试代码
    try:
        manager = ConfigManager()
        manager.load_all()
        
        print(f"加载了 {len(manager.axis_definitions)} 个轴定义")
        print(f"加载了 {len(manager.presets)} 个预设")
        print(f"加载了 {len(manager.pillars)} 个支柱概念")
        
        # 测试获取数据
        if manager.axis_definitions:
            axis = manager.axis_definitions[0]
            print(f"\n示例轴: {axis.id} - {axis.name.get('zh', axis.name.get('en', ''))}")
        
        if manager.presets:
            preset = manager.presets[0]
            print(f"\n示例预设: {preset.name}")
        
        if manager.pillars:
            pillar = manager.pillars[0]
            print(f"\n示例支柱: {pillar.concept} - {pillar.keywords[:3]}...")
        
    except ConfigError as e:
        print(f"配置加载错误: {e}")

