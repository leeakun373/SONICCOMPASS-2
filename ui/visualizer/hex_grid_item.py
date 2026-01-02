"""
六边形网格项 - 游戏级渲染
"""

import math
from PySide6.QtWidgets import QGraphicsPolygonItem
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPen, QBrush, QPolygonF, QRadialGradient


class HexGridItem(QGraphicsPolygonItem):
    """六边形网格项 - 游戏级渲染"""
    
    def __init__(self, q: int, r: int, size: float, center: QPointF, parent=None):
        """
        初始化六边形项
        
        Args:
            q: 轴向坐标 q
            r: 轴向坐标 r
            size: 六边形大小
            center: 中心点
            parent: 父对象
        """
        super().__init__(parent)
        self.q = q
        self.r = r
        self.size = size
        self.center = center
        self.point_indices = []
        self.dominant_category = None
        self.density = 0
        
        # Hover 状态
        self._is_hovered = False
        
        # 间距：缩小半径 1.5px 以创建网格缝隙
        gap = 1.5
        self.visual_size = size - gap
        
        # 创建六边形多边形（使用缩小后的尺寸）
        hex_poly = self._create_hexagon(center.x(), center.y(), self.visual_size)
        self.setPolygon(hex_poly)
        
        # 默认样式
        self.base_color = QColor('#121417')
        self.base_alpha = 100
        self._update_style()
        self.setZValue(0)
        
        # 启用鼠标跟踪以支持 hover
        self.setAcceptHoverEvents(True)
    
    def _create_hexagon(self, x: float, y: float, size: float) -> QPolygonF:
        """创建六边形"""
        hexagon = QPolygonF()
        for i in range(6):
            angle = math.pi / 3 * i
            hx = x + size * math.cos(angle)
            hy = y + size * math.sin(angle)
            hexagon.append(QPointF(hx, hy))
        return hexagon
    
    def _update_style(self):
        """更新样式（使用径向渐变和玻璃边框）"""
        # 创建径向渐变
        gradient = QRadialGradient(self.center, self.visual_size)
        
        # 中心：60% 透明度
        center_color = QColor(self.base_color)
        center_color.setAlpha(int(self.base_alpha * 0.6))
        gradient.setColorAt(0.0, center_color)
        
        # 边缘：20% 透明度
        edge_color = QColor(self.base_color)
        edge_color.setAlpha(int(self.base_alpha * 0.2))
        gradient.setColorAt(1.0, edge_color)
        
        self.setBrush(QBrush(gradient))
        
        # 边框：玻璃边缘效果
        if self._is_hovered:
            # Hover 状态：白色边框，更亮
            border_color = QColor('#FFFFFF')
            border_width = 2.0
            # 填充变实
            hover_gradient = QRadialGradient(self.center, self.visual_size)
            hover_center = QColor(self.base_color)
            hover_center.setAlpha(min(255, int(self.base_alpha * 1.2)))
            hover_gradient.setColorAt(0.0, hover_center)
            hover_edge = QColor(self.base_color)
            hover_edge.setAlpha(int(self.base_alpha * 0.8))
            hover_gradient.setColorAt(1.0, hover_edge)
            self.setBrush(QBrush(hover_gradient))
        else:
            # 正常状态：稍微亮一点的颜色，1.5px 线宽
            border_color = QColor(self.base_color)
            border_color.setAlpha(min(255, int(self.base_alpha * 1.5)))
            border_width = 1.5
        
        self.setPen(QPen(border_color, border_width))
    
    def update_style(self, color: QColor, alpha: int):
        """更新样式（外部调用）"""
        self.base_color = color
        self.base_alpha = alpha
        self._update_style()
    
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        self._is_hovered = True
        self._update_style()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        self._is_hovered = False
        self._update_style()
        super().hoverLeaveEvent(event)

