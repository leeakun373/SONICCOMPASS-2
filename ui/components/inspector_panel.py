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
        
        # 存储 importer 实例用于获取原始数据
        self.importer = None
        self.raw_metadata_cache = {}  # recID -> raw_metadata 缓存
        
        self.clear()
    
    def set_importer(self, importer):
        """
        设置数据导入器实例，用于获取原始元数据
        
        Args:
            importer: SoundminerImporter 实例
        """
        self.importer = importer
        self.raw_metadata_cache.clear()  # 清空缓存
    
    def _get_raw_metadata(self, file_data: Dict) -> Optional[Dict]:
        """
        从数据库获取原始元数据
        
        Args:
            file_data: 渲染用的元数据（可能经过处理）
            
        Returns:
            原始元数据字典，如果无法获取则返回 None
        """
        if not self.importer:
            return None
        
        # 获取 recID
        recid = file_data.get('recID') or file_data.get('recid') or file_data.get('id')
        if not recid:
            return None
        
        # 检查缓存
        if recid in self.raw_metadata_cache:
            return self.raw_metadata_cache[recid]
        
        # 从数据库查询原始数据
        try:
            self.importer._connect()
            if not self.importer.table_name:
                self.importer.table_name = self.importer._detect_table_name()
                self.importer.field_mapping = self.importer.FIELD_MAPPINGS.get(self.importer.table_name, {})
            
            cursor = self.importer.conn.cursor()
            recid_field = self.importer.field_mapping.get('recID', 'recID')
            query = f"SELECT * FROM {self.importer.table_name} WHERE {recid_field} = ?"
            cursor.execute(query, (recid,))
            row = cursor.fetchone()
            
            if row:
                # 转换为字典
                raw_meta = dict(row)
                self.raw_metadata_cache[recid] = raw_meta
                return raw_meta
        except Exception as e:
            print(f"[WARNING] 无法从数据库获取原始元数据 (recID={recid}): {e}")
        
        return None
    
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
        """显示元数据（使用原始数据）"""
        self.clear()
        
        title = QLabel("INSPECTOR")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2; text-transform: uppercase;")
        self.layout.addWidget(title)
        
        # 获取原始元数据
        raw_metadata = self._get_raw_metadata(metadata)
        if not raw_metadata:
            # 如果无法获取原始数据，使用传入的 metadata（向后兼容）
            raw_metadata = metadata
            print("[WARNING] 无法获取原始元数据，使用渲染数据")
        
        # 原始元数据部分
        raw_section_title = QLabel("RAW METADATA")
        raw_section_title.setStyleSheet("color: #5F636E; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-top: 20px;")
        self.layout.addWidget(raw_section_title)
        
        # 文件路径
        filepath = raw_metadata.get('filepath') or raw_metadata.get('Filepath') or ""
        if filepath:
            filepath_label = QLabel(f"<b>文件路径:</b><br><span style='font-family: Consolas, monospace; color: #A0A0A0;'>{filepath}</span>")
            filepath_label.setWordWrap(True)
            filepath_label.setOpenExternalLinks(False)
            self.layout.addWidget(filepath_label)
        else:
            empty_label = QLabel("<b>文件路径:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
        # 文件名
        filename = raw_metadata.get('filename') or raw_metadata.get('Filename') or ""
        if filename:
            filename_label = QLabel(f"<b>文件名:</b> {filename}")
            filename_label.setWordWrap(True)
            self.layout.addWidget(filename_label)
        else:
            empty_label = QLabel("<b>文件名:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
        # RecID
        recid = raw_metadata.get('recID') or raw_metadata.get('recid') or raw_metadata.get('id') or ""
        if recid:
            recid_label = QLabel(f"<b>RecID:</b> {recid}")
            self.layout.addWidget(recid_label)
        else:
            empty_label = QLabel("<b>RecID:</b> <span style='color: #FF6B6B;'>[None]</span>")
            self.layout.addWidget(empty_label)
        
        # Category（原始）
        category = raw_metadata.get('category') or raw_metadata.get('Category') or ""
        if category:
            cat_label = QLabel(f"<b>Category:</b> {category}")
            self.layout.addWidget(cat_label)
        else:
            empty_label = QLabel("<b>Category:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
        # SubCategory（如果存在）
        subcategory = raw_metadata.get('subcategory') or raw_metadata.get('SubCategory') or raw_metadata.get('Subcategory') or ""
        if subcategory:
            subcat_label = QLabel(f"<b>SubCategory:</b> {subcategory}")
            self.layout.addWidget(subcat_label)
        elif 'SubCategory' in raw_metadata or 'subcategory' in raw_metadata:
            empty_label = QLabel("<b>SubCategory:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
        # Description（原始）
        description = raw_metadata.get('description') or raw_metadata.get('Description') or ""
        if description:
            desc_label = QLabel(f"<b>Description:</b><br><span style='color: #E1E4E8;'>{description}</span>")
            desc_label.setWordWrap(True)
            self.layout.addWidget(desc_label)
        else:
            empty_label = QLabel("<b>Description:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
        # Keywords（原始）
        keywords = raw_metadata.get('keywords') or raw_metadata.get('Keywords') or ""
        if keywords:
            # 如果keywords是列表，转换为字符串
            if isinstance(keywords, list):
                keywords_text = ', '.join(str(k) for k in keywords if k)
            else:
                keywords_text = str(keywords)
            keywords_label = QLabel(f"<b>Keywords:</b><br><span style='color: #C8D1D9;'>{keywords_text}</span>")
            keywords_label.setWordWrap(True)
            self.layout.addWidget(keywords_label)
        else:
            empty_label = QLabel("<b>Keywords:</b> <span style='color: #FF6B6B;'>[Empty]</span>")
            self.layout.addWidget(empty_label)
        
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
    
    def update_selection(self, metadata_list: List[Dict]):
        """
        更新选择显示（支持单选和多选）
        
        Args:
            metadata_list: 元数据列表，长度为1时显示详情，>1时显示列表
        """
        self.clear()
        
        if len(metadata_list) == 1:
            # 单选：显示波形大图和详细属性
            self.show_metadata(metadata_list[0])
        else:
            # 多选：显示紧凑列表
            self._show_asset_list(metadata_list)
    
    def _show_asset_list(self, metadata_list: List[Dict]):
        """显示资产列表（QListWidget）"""
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        
        title = QLabel("INSPECTOR")
        title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        title.setFont(title_font)
        title.setStyleSheet("color: #5E6AD2; text-transform: uppercase;")
        self.layout.addWidget(title)
        
        # 显示数量信息
        count_label = QLabel(f"<b>Selected:</b> {len(metadata_list)} items")
        count_label.setStyleSheet("color: #8B9FFF; font-size: 14px; margin-bottom: 10px;")
        self.layout.addWidget(count_label)
        
        # 创建列表控件
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1C1E24;
                border: 1px solid #2A2D35;
                border-radius: 4px;
                color: #E1E4E8;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2A2D35;
            }
            QListWidget::item:hover {
                background-color: #2A2D35;
            }
            QListWidget::item:selected {
                background-color: #5E6AD2;
                color: white;
            }
        """)
        
        # 添加列表项
        for i, meta in enumerate(metadata_list):
            filename = meta.get('filename') or meta.get('filepath', 'Unknown')
            subcategory = meta.get('subcategory', 'N/A')
            
            # 创建列表项文本
            item_text = f"{i+1}. {filename}"
            if subcategory and subcategory != 'N/A':
                item_text += f" [{subcategory}]"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, meta)  # 存储metadata
            list_widget.addItem(item)
        
        # 连接点击事件：点击列表项进入单选详情模式
        list_widget.itemClicked.connect(lambda item: self.show_metadata(item.data(Qt.ItemDataRole.UserRole)))
        
        self.layout.addWidget(list_widget)
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

