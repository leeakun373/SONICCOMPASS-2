"""
Sonic Compass 2.0 主入口文件（向后兼容）
已重构到 ui/ 模块，此文件保留用于向后兼容
"""

# 向后兼容：重定向到新的模块结构
from ui import SonicCompassMainWindow

# 导出主要类以保持向后兼容
__all__ = ['SonicCompassMainWindow']

# 如果直接运行此文件，启动应用
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QColor, QPalette
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#0B0C0E'))
    palette.setColor(QPalette.ColorRole.WindowText, QColor('#E1E4E8'))
    palette.setColor(QPalette.ColorRole.Base, QColor('#121417'))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#1C1E24'))
    palette.setColor(QPalette.ColorRole.Text, QColor('#E1E4E8'))
    palette.setColor(QPalette.ColorRole.Button, QColor('#1C1E24'))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor('#E1E4E8'))
    palette.setColor(QPalette.ColorRole.Highlight, QColor('#5E6AD2'))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor('#FFFFFF'))
    app.setPalette(palette)
    
    window = SonicCompassMainWindow()
    window.show()
    
    sys.exit(app.exec())
