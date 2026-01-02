"""
搜索栏 - 胶囊样式，带阴影效果
"""

from PySide6.QtWidgets import QLineEdit, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class SearchBar(QLineEdit):
    """搜索栏 - 胶囊样式，带阴影效果"""
    
    search_requested = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("🔍 搜索音频文件...")
        self.setFixedHeight(45)
        self.setMinimumWidth(400)
        
        # 设置字体
        font = QFont("Segoe UI", 13)
        self.setFont(font)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            query = self.text().strip()
            if query:
                self.search_requested.emit(query)
        super().keyPressEvent(event)

