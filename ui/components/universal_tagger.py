"""
通用标注器 - 右键菜单
"""

from PySide6.QtWidgets import QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class UniversalTagger(QDialog):
    """通用标注器 - 右键菜单"""
    
    calibrated = Signal(int)  # 校准完成信号，传递校准的项目数
    
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 280)
        
        # 滑块值
        self.reality_value = 50  # Organic (0) <-> Synthetic (100)
        self.tone_value = 50     # Dark (0) <-> Bright (100)
        self.function_value = 50  # One-shot (0) <-> Ambience (100)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(18, 20, 23, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("UNIVERSAL TAGGER")
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2;")
        layout.addWidget(title)
        
        # Reality 滑块
        reality_layout = QVBoxLayout()
        reality_label = QLabel("Reality")
        reality_label.setStyleSheet("color: #E1E4E8; font-size: 11px;")
        reality_layout.addWidget(reality_label)
        
        reality_slider_layout = QHBoxLayout()
        reality_slider_layout.addWidget(QLabel("Organic"))
        self.reality_slider = QSlider(Qt.Orientation.Horizontal)
        self.reality_slider.setRange(0, 100)
        self.reality_slider.setValue(50)
        self.reality_slider.valueChanged.connect(lambda v: setattr(self, 'reality_value', v))
        self.reality_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255, 255, 255, 0.1);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #5E6AD2;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -6px 0;
            }
        """)
        reality_slider_layout.addWidget(self.reality_slider)
        reality_slider_layout.addWidget(QLabel("Synthetic"))
        reality_layout.addLayout(reality_slider_layout)
        layout.addLayout(reality_layout)
        
        # Tone 滑块
        tone_layout = QVBoxLayout()
        tone_label = QLabel("Tone")
        tone_label.setStyleSheet("color: #E1E4E8; font-size: 11px;")
        tone_layout.addWidget(tone_label)
        
        tone_slider_layout = QHBoxLayout()
        tone_slider_layout.addWidget(QLabel("Dark"))
        self.tone_slider = QSlider(Qt.Orientation.Horizontal)
        self.tone_slider.setRange(0, 100)
        self.tone_slider.setValue(50)
        self.tone_slider.valueChanged.connect(lambda v: setattr(self, 'tone_value', v))
        self.tone_slider.setStyleSheet(self.reality_slider.styleSheet())
        tone_slider_layout.addWidget(self.tone_slider)
        tone_slider_layout.addWidget(QLabel("Bright"))
        tone_layout.addLayout(tone_slider_layout)
        layout.addLayout(tone_layout)
        
        # Function 滑块
        function_layout = QVBoxLayout()
        function_label = QLabel("Function")
        function_label.setStyleSheet("color: #E1E4E8; font-size: 11px;")
        function_layout.addWidget(function_label)
        
        function_slider_layout = QHBoxLayout()
        function_slider_layout.addWidget(QLabel("One-shot"))
        self.function_slider = QSlider(Qt.Orientation.Horizontal)
        self.function_slider.setRange(0, 100)
        self.function_slider.setValue(50)
        self.function_slider.valueChanged.connect(lambda v: setattr(self, 'function_value', v))
        self.function_slider.setStyleSheet(self.reality_slider.styleSheet())
        function_slider_layout.addWidget(self.function_slider)
        function_slider_layout.addWidget(QLabel("Ambience"))
        function_layout.addLayout(function_slider_layout)
        layout.addLayout(function_layout)
        
        # Apply 按钮
        apply_btn = QPushButton("APPLY BIAS")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E6AD2;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4A52B8;
            }
            QPushButton:pressed {
                background-color: #3A42A8;
            }
        """)
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
    
    def _on_apply(self):
        """应用校准"""
        # TODO: 实现校准逻辑，更新数据权重
        # 这里应该调用 search_core 或 visualizer 的方法来更新权重
        item_count = 1  # 临时值，实际应该从 data 中获取
        self.calibrated.emit(item_count)
        self.accept()
    
    def show_at_position(self, x: int, y: int):
        """在指定位置显示"""
        self.move(x, y)
        self.show()

