"""
检查器面板 - 显示选中项的详情
"""

from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from typing import List, Dict


class InspectorPanel(QScrollArea):
    """检查器面板 - 显示选中项的详情"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.setWidget(content)
        self.clear()
    
    def clear(self):
        """清空面板"""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        title = QLabel("INSPECTOR")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2; text-transform: uppercase;")
        self.layout.addWidget(title)
        
        hint = QLabel("点击画布上的点或六边形查看详情")
        hint.setWordWrap(True)
        self.layout.addWidget(hint)
        self.layout.addStretch()
    
    def show_metadata(self, metadata: dict):
        """显示元数据"""
        self.clear()
        
        title = QLabel("INSPECTOR")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2; text-transform: uppercase;")
        self.layout.addWidget(title)
        
        # 文件名
        if metadata.get('filename'):
            filename_label = QLabel(f"<b>文件名:</b> {metadata['filename']}")
            filename_label.setWordWrap(True)
            self.layout.addWidget(filename_label)
        
        # RecID
        if metadata.get('recID'):
            recid_label = QLabel(f"<b>RecID:</b> {metadata['recID']}")
            self.layout.addWidget(recid_label)
        
        # 分类
        if metadata.get('category'):
            cat_label = QLabel(f"<b>分类:</b> {metadata['category']}")
            self.layout.addWidget(cat_label)
        
        # 描述
        if metadata.get('description'):
            desc_label = QLabel(f"<b>描述:</b><br>{metadata['description']}")
            desc_label.setWordWrap(True)
            self.layout.addWidget(desc_label)
        
        # 关键词
        if metadata.get('keywords'):
            keywords_label = QLabel(f"<b>关键词:</b><br>{metadata['keywords']}")
            keywords_label.setWordWrap(True)
            self.layout.addWidget(keywords_label)
        
        self.layout.addStretch()

