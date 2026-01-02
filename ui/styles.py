"""
全局样式定义
"""

GLOBAL_STYLESHEET = """
/* 全局样式 */
QMainWindow {
    background-color: #0B0C0E;
    color: #E1E4E8;
}

QWidget {
    background-color: #0B0C0E;
    color: #E1E4E8;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}

/* 侧边栏 */
QFrame#sidebar {
    background-color: #121417;
    border-right: 1px solid #1C1E24;
}

QLabel#logo {
    color: #5E6AD2;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 2px;
}

QLabel#section_title {
    color: #5F636E;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* 按钮样式 */
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    color: #5F636E;
    padding: 10px 20px;
    font-size: 12px;
    font-weight: 500;
    min-height: 36px;
}

QPushButton:hover {
    background-color: rgba(94, 106, 210, 0.1);
    color: #5E6AD2;
}

QPushButton:checked {
    background-color: transparent;
    border-left: 3px solid #5E6AD2;
    color: #5E6AD2;
}

QPushButton:pressed {
    background-color: rgba(94, 106, 210, 0.2);
}

/* 搜索栏 - 胶囊样式 */
QLineEdit#search_bar {
    background-color: rgba(20, 20, 30, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding-left: 15px;
    padding-right: 15px;
    color: #FFFFFF;
    font-size: 14px;
    selection-background-color: #5E6AD2;
}

QLineEdit#search_bar:focus {
    border-color: rgba(94, 106, 210, 0.6);
    background-color: rgba(20, 20, 30, 0.95);
}

QLineEdit#search_bar::placeholder {
    color: #5F636E;
}

/* 检查器面板 - 磨砂玻璃效果 */
QScrollArea#inspector {
    background-color: rgba(18, 20, 23, 0.95);
    border-left: 1px solid rgba(28, 30, 36, 0.5);
}

QLabel {
    color: #E1E4E8;
}

QLabel b {
    color: #5E6AD2;
    font-weight: bold;
}

/* 状态标签 */
QLabel#status {
    color: #5F636E;
    font-size: 11px;
    padding: 10px 20px;
}
"""

