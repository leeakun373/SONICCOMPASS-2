"""
检查器面板 - 显示选中项的详情
"""

from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from typing import List, Dict, Optional
from pathlib import Path


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
        
        # 库文件树
        library_tree_title = QLabel("LIBRARY TREE")
        library_tree_title.setStyleSheet("color: #5F636E; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-top: 20px;")
        self.layout.addWidget(library_tree_title)
        
        self.library_tree = QTreeWidget()
        self.library_tree.setHeaderHidden(True)
        self.library_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1C1E24;
                border: 1px solid #2A2D35;
                border-radius: 4px;
                color: #E1E4E8;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background-color: #2A2D35;
            }
        """)
        self.library_tree.setMaximumHeight(200)
        self.layout.addWidget(self.library_tree)
        
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
        
        # 库（Library）- 从filepath提取或使用metadata中的library字段
        library_name = None
        if metadata.get('library'):
            library_name = metadata['library']
        elif metadata.get('filepath'):
            # 从filepath中提取库名（第一个路径段）
            from pathlib import Path
            filepath = metadata['filepath']
            if filepath:
                path_parts = Path(filepath).parts
                if len(path_parts) > 0:
                    # 通常库名是路径的第一或第二个部分
                    library_name = path_parts[0] if path_parts[0] else (path_parts[1] if len(path_parts) > 1 else None)
        
        if library_name:
            library_label = QLabel(f"<b>库:</b> {library_name}")
            library_label.setWordWrap(True)
            library_label.setStyleSheet("color: #8B9FFF;")
            self.layout.addWidget(library_label)
        
        # 文件路径
        if metadata.get('filepath'):
            filepath_label = QLabel(f"<b>文件路径:</b><br><span style='font-family: Consolas, monospace; color: #A0A0A0;'>{metadata['filepath']}</span>")
            filepath_label.setWordWrap(True)
            filepath_label.setOpenExternalLinks(False)
            self.layout.addWidget(filepath_label)
        
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
            desc_label = QLabel(f"<b>描述:</b><br><span style='color: #E1E4E8;'>{metadata['description']}</span>")
            desc_label.setWordWrap(True)
            self.layout.addWidget(desc_label)
        
        # 关键词
        if metadata.get('keywords'):
            keywords_text = metadata['keywords']
            # 如果keywords是列表，转换为字符串
            if isinstance(keywords_text, list):
                keywords_text = ', '.join(str(k) for k in keywords_text if k)
            keywords_label = QLabel(f"<b>关键词:</b><br><span style='color: #C8D1D9;'>{keywords_text}</span>")
            keywords_label.setWordWrap(True)
            self.layout.addWidget(keywords_label)
        
        self.layout.addStretch()
    
    def show_metadata_list(self, metadata_list: List[Dict], hex_key=None):
        """显示六边形内所有数据的列表"""
        self.clear()
        
        title = QLabel("INSPECTOR")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2; text-transform: uppercase;")
        self.layout.addWidget(title)
        
        # 显示六边形信息
        hex_info = QLabel(f"<b>Selected Hex:</b> {len(metadata_list)} items")
        hex_info.setWordWrap(True)
        hex_info.setStyleSheet("color: #8B9FFF; font-size: 14px; margin-bottom: 10px;")
        self.layout.addWidget(hex_info)
        
        if hex_key:
            hex_coord = QLabel(f"<span style='color: #5F636E; font-size: 11px;'>({hex_key[0]}, {hex_key[1]})</span>")
            self.layout.addWidget(hex_coord)
        
        # 显示文件列表
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #2A2D35; border: none;")
        self.layout.addWidget(separator)
        
        # 限制显示数量，避免列表过长
        max_display = 50
        display_list = metadata_list[:max_display]
        
        for i, metadata in enumerate(display_list, 1):
            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #1C1E24; border-radius: 4px; padding: 8px; margin-bottom: 8px;")
            item_layout = QVBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(5)
            
            # 文件名或路径
            filename = metadata.get('filename') or metadata.get('filepath', 'Unknown')
            if filename:
                filename_label = QLabel(f"<b>{i}.</b> {filename}")
                filename_label.setWordWrap(True)
                filename_label.setStyleSheet("color: #E1E4E8; font-size: 12px;")
                item_layout.addWidget(filename_label)
            
            # 分类信息
            if metadata.get('category'):
                cat_label = QLabel(f"<span style='color: #8B9FFF; font-size: 11px;'>{metadata['category']}</span>")
                item_layout.addWidget(cat_label)
            
            self.layout.addWidget(item_frame)
        
        if len(metadata_list) > max_display:
            more_label = QLabel(f"<span style='color: #5F636E; font-size: 11px;'>... and {len(metadata_list) - max_display} more items</span>")
            self.layout.addWidget(more_label)
        
        self.layout.addStretch()
    
    def _build_library_tree(self, library_root: Optional[str], metadata_list: List[Dict]):
        """
        构建库文件树
        
        Args:
            library_root: 库根路径
            metadata_list: 元数据列表
        """
        self.library_tree.clear()
        
        if not library_root or not Path(library_root).exists():
            return
        
        try:
            # 扫描库根目录下的一级子文件夹
            root_path = Path(library_root)
            subdirs = [d for d in root_path.iterdir() if d.is_dir()]
            
            if not subdirs:
                return
            
            # 统计每个文件夹的映射数量
            library_stats = {}
            for subdir in subdirs:
                subdir_str = str(subdir)
                mapped_count = 0
                total_count = 0
                
                # 与 metadata 中的 filepath 进行前缀匹配
                for meta in metadata_list:
                    filepath = meta.get('filepath', '')
                    if filepath and filepath.startswith(subdir_str):
                        total_count += 1
                        # 检查是否有有效的category（非UNCATEGORIZED）
                        cat_id = meta.get('category', '')
                        if cat_id:
                            try:
                                from core.category_color_mapper import CategoryColorMapper
                                mapper = CategoryColorMapper()
                                category = mapper.get_category_from_catid(cat_id)
                                if category and category != "UNCATEGORIZED":
                                    mapped_count += 1
                            except Exception:
                                pass
                
                library_stats[subdir.name] = (mapped_count, total_count)
            
            # 创建树节点
            for subdir_name, (mapped, total) in sorted(library_stats.items()):
                item = QTreeWidgetItem(self.library_tree)
                item.setText(0, f"{subdir_name} ({mapped}/{total})")
                if mapped > 0:
                    item.setForeground(0, QColor("#8B9FFF"))
                else:
                    item.setForeground(0, QColor("#5F636E"))
        
        except Exception as e:
            print(f"[WARNING] 构建库文件树失败: {e}")

