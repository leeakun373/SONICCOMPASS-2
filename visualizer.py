"""
可视化引擎（向后兼容）
已重构到 ui/visualizer/ 模块，此文件保留用于向后兼容
"""

# 向后兼容：从新模块导入
from ui.visualizer import (
    VisualizerError,
    HexGridItem,
    ScatterItem,
    SonicUniverse
)

__all__ = [
    'VisualizerError',
    'HexGridItem',
    'ScatterItem',
    'SonicUniverse',
]
