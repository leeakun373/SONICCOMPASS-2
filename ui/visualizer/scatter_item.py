"""
散点项 - 带光晕效果
"""

from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath, QRadialGradient


class ScatterItem(QGraphicsItem):
    """散点项 - 带光晕效果"""
    
    def __init__(self, x: float, y: float, color: QColor, size: float = 3.0, parent=None):
        """
        初始化散点项
        
        Args:
            x, y: 位置坐标
            color: 颜色
            size: 中心实心圆半径
            parent: 父对象
        """
        super().__init__(parent)
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.glow_size = size * 3  # 光晕半径是中心圆的3倍
        
        # 设置边界矩形（用于碰撞检测）
        self.setPos(x, y)
        self.bounding_rect = QRectF(
            -self.glow_size, -self.glow_size,
            self.glow_size * 2, self.glow_size * 2
        )
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        return self.bounding_rect
    
    def shape(self) -> QPainterPath:
        """返回形状（用于碰撞检测）"""
        path = QPainterPath()
        path.addEllipse(-self.size, -self.size, self.size * 2, self.size * 2)
        return path
    
    def paint(self, painter: QPainter, option, widget=None):
        """绘制点（中心实心圆 + 外围光晕）"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制光晕（外围大圆，低透明度）
        glow_color = QColor(self.color)
        glow_color.setAlpha(30)  # 低透明度光晕
        
        glow_gradient = QRadialGradient(0, 0, self.glow_size)
        glow_gradient.setColorAt(0.0, QColor(self.color.red(), self.color.green(), self.color.blue(), 50))
        glow_gradient.setColorAt(0.5, QColor(self.color.red(), self.color.green(), self.color.blue(), 20))
        glow_gradient.setColorAt(1.0, QColor(self.color.red(), self.color.green(), self.color.blue(), 0))
        
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            -self.glow_size, -self.glow_size,
            self.glow_size * 2, self.glow_size * 2
        )
        
        # 绘制中心实心圆
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            -self.size, -self.size,
            self.size * 2, self.size * 2
        )

