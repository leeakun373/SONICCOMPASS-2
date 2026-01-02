"""
Sonic Compass 2.0 主入口文件
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette

from ui import SonicCompassMainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 设置应用调色板
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


if __name__ == "__main__":
    main()

