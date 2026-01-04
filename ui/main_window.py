"""
Sonic Compass 主窗口
深色赛博朋克风格的可视化界面
"""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QFrame, QProgressBar,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import QThread, Signal as QtSignal, Signal
from PySide6.QtCore import Qt, QRectF

from ui.components import CanvasView, SearchBar, InspectorPanel, UniversalTagger
from ui.visualizer import SonicUniverse
from ui.styles import GLOBAL_STYLESHEET
from core import DataProcessor, SearchCore, VectorEngine, UCSManager
from data import SoundminerImporter, ConfigManager


class UMAPRecalcThread(QThread):
    """UMAP重新计算线程 - 仅重新计算坐标，使用现有向量缓存"""
    
    progress_signal = Signal(int, str)  # 进度(%), 描述
    finished_signal = Signal()  # 仅通知完成
    error_signal = Signal(str)  # 错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_data = None  # 存储计算结果，主线程读取
    
    def run(self):
        """执行UMAP重新计算流程"""
        try:
            self.progress_signal.emit(5, "Checking cache...")
            
            # 初始化组件
            from core import UCSManager
            ucs_manager = UCSManager()
            ucs_manager.load_all()
            
            from data import SoundminerImporter
            importer = SoundminerImporter(
                db_path="./test_assets/Sonic.sqlite",
                ucs_manager=ucs_manager
            )
            
            vector_engine = VectorEngine(model_path="./models/bge-m3")
            
            # 创建处理器
            processor = DataProcessor(
                importer=importer,
                vector_engine=vector_engine,
                cache_dir="./cache"
            )
            
            # 检查缓存是否存在
            if not processor._cache_exists():
                raise ValueError("向量缓存不存在，请先运行完整重建")
            
            # 加载现有向量和元数据（不重新计算）
            self.progress_signal.emit(10, "Loading existing vectors...")
            metadata, embeddings = processor.load_index()
            
            # 提取 Category 并编码
            self.progress_signal.emit(30, "Encoding categories...")
            try:
                from core.category_color_mapper import CategoryColorMapper
                mapper = CategoryColorMapper()
            except Exception:
                mapper = None
            
            categories = []
            for meta in metadata:
                cat_id = meta.get('category', '')
                if mapper:
                    category = mapper.get_category_from_catid(cat_id)
                    if not category:
                        category = "UNCATEGORIZED"
                else:
                    category = "UNCATEGORIZED"
                categories.append(category)
            
            # 使用 LabelEncoder 编码
            from sklearn.preprocessing import LabelEncoder
            label_encoder = LabelEncoder()
            targets = label_encoder.fit_transform(categories)
            
            # Supervised UMAP (使用新参数)
            self.progress_signal.emit(50, "Computing UMAP coordinates...")
            import umap
            import numpy as np
            
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=30,  # 从15改为30，增强全局结构
                min_dist=0.01,   # 从0.1改为0.01，允许紧密堆积
                spread=1.0,
                metric='cosine',
                target_weight=0.7,
                target_metric='categorical',
                random_state=42,
                n_jobs=1
            )
            coords_2d = reducer.fit_transform(embeddings, y=targets)
            
            # 坐标归一化到 0-3000
            min_coords = coords_2d.min(axis=0)
            max_coords = coords_2d.max(axis=0)
            scale = 3000.0 / (np.max(max_coords - min_coords) + 1e-5)
            coords_2d = (coords_2d - min_coords) * scale
            
            # 存储结果
            self.result_data = {
                'metadata': metadata,
                'coords_2d': coords_2d,
                'embeddings': embeddings,
                'processor': processor
            }
            
            self.progress_signal.emit(100, "Complete")
            self.finished_signal.emit()
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
            self.error_signal.emit(error_msg)


class AtlasBuilderThread(QThread):
    """Atlas构建线程 - 将rebuild流程完全异步化"""
    
    progress_signal = Signal(int, str)  # 进度(%), 描述
    finished_signal = Signal()  # 仅通知完成，不传递数据（避免内存拷贝）
    error_signal = Signal(str)  # 错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_data = None  # 存储构建结果，主线程读取
    
    def run(self):
        """执行构建流程"""
        try:
            self.progress_signal.emit(5, "Initializing components...")
            
            # 初始化组件
            from core import UCSManager
            ucs_manager = UCSManager()
            ucs_manager.load_all()
            
            from data import SoundminerImporter
            importer = SoundminerImporter(
                db_path="./test_assets/Sonic.sqlite",
                ucs_manager=ucs_manager
            )
            
            vector_engine = VectorEngine(model_path="./models/bge-m3")
            
            # 创建处理器
            processor = DataProcessor(
                importer=importer,
                vector_engine=vector_engine,
                cache_dir="./cache"
            )
            
            # 连接进度信号（转发到主线程）
            # 注意：processor.progress_signal在子线程中，需要手动转发
            # 由于Signal/Slot的线程安全机制，这里直接连接即可
            if hasattr(processor, 'progress_signal'):
                def forward_progress(value, desc):
                    # 将processor的进度映射到rebuild的总体进度
                    # build_index占70%，UMAP占30%
                    if value <= 80:
                        mapped_value = int(5 + (value / 80) * 65)  # 5-70
                    else:
                        mapped_value = int(70 + ((value - 80) / 20) * 30)  # 70-100
                    self.progress_signal.emit(mapped_value, desc)
                
                # 使用Qt.QueuedConnection确保线程安全
                processor.progress_signal.connect(forward_progress, Qt.ConnectionType.QueuedConnection)
            
            # 构建索引（向量化）
            self.progress_signal.emit(10, "Building index...")
            metadata, embeddings = processor.build_index(
                limit=None,
                force_rebuild=True
            )
            
            # 计算 Supervised UMAP 坐标
            self.progress_signal.emit(70, "Computing UMAP coordinates...")
            
            import umap
            from sklearn.preprocessing import LabelEncoder
            import numpy as np
            
            # 提取 Category 并编码
            try:
                from core.category_color_mapper import CategoryColorMapper
                mapper = CategoryColorMapper()
            except Exception:
                mapper = None
            
            categories = []
            for meta in metadata:
                cat_id = meta.get('category', '')
                if mapper:
                    category = mapper.get_category_from_catid(cat_id)
                    if not category:
                        category = "UNCATEGORIZED"
                else:
                    category = "UNCATEGORIZED"
                categories.append(category)
            
            # 使用 LabelEncoder 编码
            label_encoder = LabelEncoder()
            targets = label_encoder.fit_transform(categories)
            
            # Supervised UMAP (更新参数)
            reducer = umap.UMAP(
                n_components=2,
                n_neighbors=30,  # 从15改为30，增强全局结构
                min_dist=0.01,   # 从0.1改为0.01，允许紧密堆积
                spread=1.0,
                metric='cosine',
                target_weight=0.7,
                target_metric='categorical',
                random_state=42,
                n_jobs=1
            )
            coords_2d = reducer.fit_transform(embeddings, y=targets)
            
            # 坐标归一化到 0-3000
            min_coords = coords_2d.min(axis=0)
            max_coords = coords_2d.max(axis=0)
            scale = 3000.0 / (np.max(max_coords - min_coords) + 1e-5)
            coords_2d = (coords_2d - min_coords) * scale
            
            # 存储结果
            self.result_data = {
                'metadata': metadata,
                'coords_2d': coords_2d,
                'embeddings': embeddings,
                'processor': processor
            }
            
            self.progress_signal.emit(100, "Complete")
            # 只发射完成信号，不传递数据
            self.finished_signal.emit()
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            traceback.print_exc()
            self.error_signal.emit(error_msg)


class SonicCompassMainWindow(QMainWindow):
    """Sonic Compass 主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sonic Compass 2.0")
        self.setMinimumSize(1600, 1000)
        
        # 核心组件
        self.processor: Optional[DataProcessor] = None
        self.search_core: Optional[SearchCore] = None
        self.visualizer: Optional[SonicUniverse] = None
        
        # 右键菜单
        self.context_menu: Optional[UniversalTagger] = None
        
        # 配置管理器
        self.config_manager = ConfigManager()
        try:
            self.config_manager.load_all()
        except Exception as e:
            print(f"[WARNING] 加载配置失败: {e}")
        
        # 动态轴配置
        self.axis_config = {
            'active': False,
            'x': '',
            'y': ''
        }
        
        # 应用全局样式
        self._apply_global_styles()
        
        # 初始化UI
        self._setup_ui()
        
        # 加载数据
        self._load_data()
    
    def _apply_global_styles(self):
        """应用全局样式表"""
        self.setStyleSheet(GLOBAL_STYLESHEET)
    
    def _setup_ui(self):
        """设置UI布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧边栏
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 中央画布区域
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        
        # 搜索栏容器（悬浮）
        search_container = QWidget()
        search_container.setFixedHeight(60)
        search_container_layout = QVBoxLayout(search_container)
        search_container_layout.setContentsMargins(0, 10, 0, 0)
        search_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        self.search_bar = SearchBar()
        self.search_bar.setObjectName("search_bar")
        self.search_bar.search_requested.connect(self._on_search)
        search_container_layout.addWidget(self.search_bar)
        
        canvas_layout.addWidget(search_container)
        
        # 画布
        self.canvas_view = CanvasView()
        self.canvas_view.zoom_changed.connect(self._on_zoom_changed)
        self.canvas_view.selection_made.connect(self._on_selection_made)
        canvas_layout.addWidget(self.canvas_view)
        
        main_layout.addWidget(canvas_container, stretch=1)
        
        # 右侧检查器面板
        self.inspector = InspectorPanel()
        self.inspector.setObjectName("inspector")
        self.inspector.setFixedWidth(300)
        main_layout.addWidget(self.inspector)
    
    def _create_sidebar(self) -> QWidget:
        """创建左侧边栏 - 扩展版（288px宽度，包含动态轴重排）"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(288)  # 根据设计文档：w-72 = 288px
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Logo
        logo = QLabel("SONIC\nCOMPASS")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("""
            QLabel {
                color: #5E6AD2;
                font-size: 20px;
                font-weight: bold;
                letter-spacing: 2px;
            }
        """)
        layout.addWidget(logo)
        
        layout.addSpacing(10)
        
        # 视图模式标题
        mode_title = QLabel("VIEW MODE")
        mode_title.setObjectName("section_title")
        mode_title.setStyleSheet("""
            QLabel {
                color: #5F636E;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(mode_title)
        
        # 视图模式切换按钮容器
        mode_container = QWidget()
        mode_layout = QVBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(10)
        
        # Explorer 按钮
        self.explorer_btn = QPushButton("🔍 Explorer")
        self.explorer_btn.setCheckable(True)
        self.explorer_btn.setChecked(True)
        self.explorer_btn.clicked.connect(lambda: self._switch_mode('explorer'))
        mode_layout.addWidget(self.explorer_btn)
        
        # Gravity 按钮
        self.gravity_btn = QPushButton("⚡ Gravity")
        self.gravity_btn.setCheckable(True)
        self.gravity_btn.clicked.connect(lambda: self._switch_mode('gravity'))
        mode_layout.addWidget(self.gravity_btn)
        
        layout.addWidget(mode_container)
        
        layout.addSpacing(20)
        
        # 动态轴重排模块
        axes_title = QLabel("DYNAMIC AXES")
        axes_title.setObjectName("section_title")
        axes_title.setStyleSheet(mode_title.styleSheet())
        layout.addWidget(axes_title)
        
        # Auto 按钮
        auto_btn = QPushButton("✨ Auto Suggest")
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(94, 106, 210, 0.2);
                color: #5E6AD2;
                border: 1px solid rgba(94, 106, 210, 0.3);
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(94, 106, 210, 0.3);
            }
        """)
        auto_btn.clicked.connect(self._on_auto_suggest)
        layout.addWidget(auto_btn)
        
        # X/Y 轴输入框容器
        axes_container = QWidget()
        axes_layout = QVBoxLayout(axes_container)
        axes_layout.setContentsMargins(0, 10, 0, 0)
        axes_layout.setSpacing(10)
        
        # X 轴
        x_label = QLabel("X-AXIS")
        x_label.setStyleSheet("color: #5F636E; font-size: 10px;")
        axes_layout.addWidget(x_label)
        self.x_axis_input = QLineEdit()
        self.x_axis_input.setPlaceholderText("e.g., Organic")
        self.x_axis_input.setStyleSheet("""
            QLineEdit {
                background-color: #1C1E24;
                border: 1px solid #2A2D35;
                border-radius: 4px;
                padding: 6px;
                color: #E1E4E8;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #5E6AD2;
            }
        """)
        axes_layout.addWidget(self.x_axis_input)
        
        # Y 轴
        y_label = QLabel("Y-AXIS")
        y_label.setStyleSheet("color: #5F636E; font-size: 10px;")
        axes_layout.addWidget(y_label)
        self.y_axis_input = QLineEdit()
        self.y_axis_input.setPlaceholderText("e.g., Synthetic")
        self.y_axis_input.setStyleSheet(self.x_axis_input.styleSheet())
        axes_layout.addWidget(self.y_axis_input)
        
        # Toggle 开关
        self.axes_toggle = QCheckBox("Activate Scatter Mode")
        self.axes_toggle.setStyleSheet("""
            QCheckBox {
                color: #E1E4E8;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #5E6AD2;
                border-radius: 3px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #5E6AD2;
            }
        """)
        self.axes_toggle.toggled.connect(self._on_axes_toggle)
        axes_layout.addWidget(self.axes_toggle)
        
        layout.addWidget(axes_container)
        
        layout.addSpacing(20)
        
        # 库路径设置
        library_title = QLabel("LIBRARY")
        library_title.setObjectName("section_title")
        library_title.setStyleSheet(mode_title.styleSheet())
        layout.addWidget(library_title)
        
        library_btn = QPushButton("📁 Set Library Path")
        library_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(94, 106, 210, 0.2);
                color: #5E6AD2;
                border: 1px solid rgba(94, 106, 210, 0.3);
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(94, 106, 210, 0.3);
            }
        """)
        library_btn.clicked.connect(self._setup_library_path)
        layout.addWidget(library_btn)
        
        layout.addSpacing(10)
        
        # Rebuild Atlas 按钮（完整重建）
        self.rebuild_btn = QPushButton("🔄 Rebuild Atlas (Full)")
        self.rebuild_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 107, 107, 0.2);
                color: #FF6B6B;
                border: 1px solid rgba(255, 107, 107, 0.3);
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 107, 0.3);
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.2);
                color: #666;
            }
        """)
        self.rebuild_btn.clicked.connect(self._rebuild_atlas)
        layout.addWidget(self.rebuild_btn)
        
        # Recalculate UMAP 按钮（仅重新计算坐标）
        self.recalc_umap_btn = QPushButton("🔄 Recalc UMAP Only")
        self.recalc_umap_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(94, 106, 210, 0.2);
                color: #5E6AD2;
                border: 1px solid rgba(94, 106, 210, 0.3);
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(94, 106, 210, 0.3);
            }
            QPushButton:disabled {
                background-color: rgba(100, 100, 100, 0.2);
                color: #666;
            }
        """)
        self.recalc_umap_btn.clicked.connect(self._recalculate_umap_only)
        layout.addWidget(self.recalc_umap_btn)
        
        layout.addStretch()
        
        # 状态信息
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("color: #5F636E; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # 进度条和进度标签
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2A2D35;
                border-radius: 4px;
                text-align: center;
                background-color: #1A1C23;
            }
            QProgressBar::chunk {
                background-color: #5E6AD2;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #5F636E; font-size: 10px;")
        layout.addWidget(self.progress_label)
        
        return sidebar
    
    def _load_data(self):
        """加载数据"""
        try:
            self.status_label.setText("Loading data...")
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_label.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Initializing...")
            
            # 初始化组件
            ucs_manager = UCSManager()
            ucs_manager.load_all()
            
            importer = SoundminerImporter(
                db_path="./test_assets/Sonic.sqlite",
                ucs_manager=ucs_manager
            )
            
            vector_engine = VectorEngine(model_path="./models/bge-m3")
            
            # 创建处理器
            self.processor = DataProcessor(
                importer=importer,
                vector_engine=vector_engine,
                cache_dir="./cache"
            )
            
            # 连接进度信号
            if hasattr(self.processor, 'progress_signal'):
                self.processor.progress_signal.connect(self._on_progress_updated)
            
            # 加载索引
            metadata, embeddings = self.processor.load_index()
            
            # 加载坐标
            coords_2d = self.processor.load_coordinates()
            if coords_2d is None:
                print("[WARNING] 未找到预计算的坐标，将在初始化时计算")
            else:
                print(f"[DEBUG] 加载坐标: shape={coords_2d.shape}, range=[{coords_2d.min(axis=0)}, {coords_2d.max(axis=0)}]")
            
            # 创建搜索核心
            self.search_core = SearchCore(
                vector_engine=vector_engine,
                metadata=metadata,
                embeddings=embeddings
            )
            
            # 创建可视化场景
            print(f"[DEBUG] 创建可视化场景: metadata={len(metadata)}, embeddings={embeddings.shape}, coords_2d={coords_2d.shape if coords_2d is not None else None}")
            self.visualizer = SonicUniverse(
                metadata,
                embeddings,
                coords_2d=coords_2d,
                hex_size=50.0,
                search_core=self.search_core,  # 传入 search_core 用于 Scatter 模式
                ucs_manager=ucs_manager  # 传入 ucs_manager 用于标签生成
            )
            self.canvas_view.setScene(self.visualizer)
            
            # 检查场景矩形
            scene_rect = self.visualizer.sceneRect()
            print(f"[DEBUG] 场景矩形: {scene_rect}")
            if hasattr(self.visualizer, 'norm_coords') and self.visualizer.norm_coords is not None:
                print(f"[DEBUG] norm_coords: shape={self.visualizer.norm_coords.shape}, range=[{self.visualizer.norm_coords.min(axis=0)}, {self.visualizer.norm_coords.max(axis=0)}]")
            
            # 使用 fit_scene_to_view 方法适配视图（包含 10% padding）
            # 这个方法内部会处理场景矩形和视图适配
            scene_rect_before = self.visualizer.sceneRect()
            print(f"[DEBUG] 适配前场景矩形: {scene_rect_before}")
            print(f"[DEBUG] 视图大小: {self.canvas_view.width()}x{self.canvas_view.height()}")
            
            self.canvas_view.fit_scene_to_view()
            
            # 再次检查场景矩形（适配后）
            scene_rect_after = self.visualizer.sceneRect()
            print(f"[DEBUG] 适配后场景矩形: {scene_rect_after}")
            print(f"[DEBUG] 视图变换矩阵: {self.canvas_view.transform()}")
            
            # 检查图层边界框
            if hasattr(self.visualizer, 'hex_layer'):
                hex_bbox = self.visualizer.hex_layer.boundingRect()
                print(f"[DEBUG] HexLayer boundingRect: {hex_bbox}")
            if hasattr(self.visualizer, 'scatter_layer'):
                scatter_bbox = self.visualizer.scatter_layer.boundingRect()
                print(f"[DEBUG] ScatterLayer boundingRect: {scatter_bbox}")
            
            # 强制更新视图（确保场景可见）
            self.canvas_view.update()
            self.canvas_view.viewport().update()
            
            # 设置画布交互
            self._setup_canvas_interaction()
            
            # 构建库文件树
            if self.config_manager.library_root:
                self.inspector._build_library_tree(self.config_manager.library_root, metadata)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            
            self.status_label.setText(f"Loaded {len(metadata)} items")
            importer.close()
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
    
    def _on_progress_updated(self, progress: int, description: str):
        """进度更新槽函数"""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(description)
    
    def _setup_library_path(self):
        """设置库路径"""
        current_path = self.config_manager.library_root or ""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Library Root Directory",
            current_path
        )
        
        if directory:
            self.config_manager.library_root = directory
            try:
                self.config_manager.save_user_config()
                self.status_label.setText(f"Library path set: {directory}")
                # 更新 Inspector 面板的库文件树
                if hasattr(self.inspector, '_build_library_tree') and self.processor:
                    metadata, _ = self.processor.load_index()
                    self.inspector._build_library_tree(self.config_manager.library_root, metadata)
            except Exception as e:
                self.status_label.setText(f"Error saving library path: {str(e)}")
    
    def _rebuild_atlas(self):
        """重建星图（完整流程：向量化+UMAP）"""
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "Rebuild Atlas",
            "重建星图将重新计算所有向量和UMAP坐标，这可能需要较长时间。\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Initializing rebuild...")
        self.status_label.setText("Rebuilding atlas...")
        
        # 禁用按钮
        if hasattr(self, 'rebuild_btn'):
            self.rebuild_btn.setEnabled(False)
        if hasattr(self, 'recalc_umap_btn'):
            self.recalc_umap_btn.setEnabled(False)
        
        # 创建并启动线程
        self.atlas_builder_thread = AtlasBuilderThread()
        self.atlas_builder_thread.progress_signal.connect(self._on_progress_updated)
        self.atlas_builder_thread.finished_signal.connect(self._on_atlas_built)
        self.atlas_builder_thread.error_signal.connect(self._on_atlas_error)
        self.atlas_builder_thread.start()
    
    def _on_atlas_built(self):
        """处理构建完成"""
        try:
            # 从线程读取结果
            result_data = self.atlas_builder_thread.result_data
            if result_data is None:
                raise ValueError("构建结果为空")
            
            # 保存坐标
            if 'processor' in result_data:
                result_data['processor'].save_coordinates(result_data['coords_2d'])
            
            # 重新加载数据
            self.status_label.setText("Reloading data...")
            self._load_data()
            
            # 显示完成对话框
            QMessageBox.information(
                self,
                "Rebuild Complete",
                f"星图重建完成！\n\n处理了 {len(result_data['metadata'])} 条记录。"
            )
        except Exception as e:
            self._on_atlas_error(str(e))
        finally:
            # 恢复UI状态
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            if hasattr(self, 'rebuild_btn'):
                self.rebuild_btn.setEnabled(True)
            if hasattr(self, 'recalc_umap_btn'):
                self.recalc_umap_btn.setEnabled(True)
            self.status_label.setText("Ready")
    
    def _on_atlas_error(self, error_msg: str):
        """处理构建错误"""
        self.status_label.setText(f"Rebuild error: {error_msg}")
        QMessageBox.critical(
            self,
            "Rebuild Error",
            f"重建失败：\n{error_msg}"
        )
        import traceback
        traceback.print_exc()
        
        # 恢复UI状态
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        if hasattr(self, 'rebuild_btn'):
            self.rebuild_btn.setEnabled(True)
        if hasattr(self, 'recalc_umap_btn'):
            self.recalc_umap_btn.setEnabled(True)
        self.status_label.setText("Ready")
    
    def _recalculate_umap_only(self):
        """仅重新计算UMAP坐标（使用现有向量缓存）"""
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "Recalculate UMAP",
            "仅重新计算UMAP坐标（使用现有向量缓存）。\n\n这通常用于调整UMAP参数后快速更新坐标。\n\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Initializing UMAP recalculation...")
        self.status_label.setText("Recalculating UMAP...")
        
        # 禁用按钮
        if hasattr(self, 'rebuild_btn'):
            self.rebuild_btn.setEnabled(False)
        if hasattr(self, 'recalc_umap_btn'):
            self.recalc_umap_btn.setEnabled(False)
        
        # 创建并启动线程
        self.umap_recalc_thread = UMAPRecalcThread()
        self.umap_recalc_thread.progress_signal.connect(self._on_progress_updated)
        self.umap_recalc_thread.finished_signal.connect(self._on_umap_recalc_complete)
        self.umap_recalc_thread.error_signal.connect(self._on_atlas_error)
        self.umap_recalc_thread.start()
    
    def _on_umap_recalc_complete(self):
        """处理UMAP重新计算完成"""
        try:
            # 从线程读取结果
            result_data = self.umap_recalc_thread.result_data
            if result_data is None:
                raise ValueError("计算结果为空")
            
            # 保存坐标
            if 'processor' in result_data:
                result_data['processor'].save_coordinates(result_data['coords_2d'])
            
            # 重新加载数据
            self.status_label.setText("Reloading data...")
            self._load_data()
            
            # 显示完成对话框
            QMessageBox.information(
                self,
                "UMAP Recalculation Complete",
                f"UMAP坐标重新计算完成！\n\n处理了 {len(result_data['metadata'])} 条记录。"
            )
        except Exception as e:
            self._on_atlas_error(str(e))
        finally:
            # 恢复UI状态
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            if hasattr(self, 'rebuild_btn'):
                self.rebuild_btn.setEnabled(True)
            if hasattr(self, 'recalc_umap_btn'):
                self.recalc_umap_btn.setEnabled(True)
            self.status_label.setText("Ready")
    
    def _setup_canvas_interaction(self):
        """修复后的画布交互逻辑"""
        if not self.visualizer:
            return
        
        # 连接assets_selected信号到InspectorPanel
        if hasattr(self.visualizer, 'assets_selected'):
            self.visualizer.assets_selected.connect(self.inspector.update_selection)
        
        original_mouse_press = self.visualizer.mousePressEvent
        
        def custom_mouse_press(event):
            original_mouse_press(event)
            
            # 1. 获取鼠标在场景中的绝对坐标
            scene_pos = event.scenePos()
            
            # 2. 调用引擎的手动命中测试
            hit_data = self.visualizer.find_closest_data(scene_pos)
            
            if hit_data:
                # 3. 根据返回类型显示不同内容
                if hit_data.get('type') == 'hex':
                    # LOD < 2: 显示六边形内所有数据
                    self.inspector.show_metadata_list(
                        hit_data['metadata_list'],
                        hex_key=hit_data['hex_key']
                    )
                    # 高亮该六边形内的所有点
                    self.visualizer.highlight_indices(hit_data['indices'])
                elif hit_data.get('type') == 'point':
                    # LOD >= 2: 显示单个文件详情
                    self.inspector.show_metadata(hit_data['metadata'])
                    # 高亮该点
                    self.visualizer.highlight_indices([hit_data['index']])
            else:
                self.visualizer.clear_highlights()
        
        def custom_context_menu(event):
            """右键菜单事件"""
            scene_pos = event.scenePos()
            hit_data = self.visualizer.find_closest_data(scene_pos)
            if hit_data and hit_data.get('type') == 'point':
                # 只在LOD >= 2时显示右键菜单（单个文件）
                view_pos = self.canvas_view.mapFromScene(scene_pos)
                global_pos = self.canvas_view.mapToGlobal(view_pos)
                self._show_context_menu(global_pos.x(), global_pos.y(), {
                    'type': 'point',
                    'metadata': hit_data['metadata']
                })
        
        self.visualizer.mousePressEvent = custom_mouse_press
        self.visualizer.contextMenuEvent = custom_context_menu
    
    def _switch_mode(self, mode: str):
        """切换视图模式"""
        if not self.visualizer or not self.search_core:
            return
        
        if mode == 'explorer':
            self.explorer_btn.setChecked(True)
            self.gravity_btn.setChecked(False)
            # 切换到 Explorer 模式
            self.visualizer.set_view_mode('explorer')
            self.status_label.setText("● Explorer Mode")
        else:
            self.explorer_btn.setChecked(False)
            self.gravity_btn.setChecked(True)
            # 切换到 Gravity 模式
            self._activate_gravity_mode()
    
    def _activate_gravity_mode(self):
        """激活引力视图模式"""
        if not self.visualizer or not self.search_core:
            return
        
        try:
            self.status_label.setText("● Calculating gravity forces...")
            
            # 选择默认引力桩（从 pillars_data.csv 中选择几个代表性的）
            default_pillars = [
                "Fire, burning, ash, lava, destruction",
                "Ice, cold, frozen, crystal, winter",
                "Electric, spark, lightning, energy, buzz",
                "Organic, nature, forest, wood, magic",
                "Sci-Fi, space, alien, futuristic, tech",
                "Dark, horror, ghost, spectral, eerie"
            ]
            
            # 计算引力权重
            gravity_weights = self.search_core.calculate_gravity_forces(default_pillars)
            
            # 设置引力桩和权重
            pillar_names = [f"Pillar {i+1}" for i in range(len(default_pillars))]
            self.visualizer.set_gravity_pillars(pillar_names, gravity_weights)
            
            # 切换到引力视图
            self.visualizer.set_view_mode('gravity')
            
            self.status_label.setText("● Gravity Mode Active")
            
        except Exception as e:
            self.status_label.setText(f"● Error: {str(e)}")
            print(f"[ERROR] 引力视图激活失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_context_menu(self, x: int, y: int, data: dict):
        """显示右键菜单"""
        if self.context_menu:
            self.context_menu.close()
        
        self.context_menu = UniversalTagger(self, data)
        self.context_menu.calibrated.connect(self._on_calibrated)
        self.context_menu.show_at_position(x, y)
    
    def _on_calibrated(self, item_count: int):
        """校准完成回调"""
        # 显示 Toast 提示（简化版：更新状态栏）
        self.status_label.setText(f"● Calibrated {item_count} items")
        # TODO: 实现 Toast 通知
    
    def _on_auto_suggest(self):
        """Auto Suggest 按钮点击"""
        # AI 推荐反义词对
        suggestions = [
            ("Organic", "Synthetic"),
            ("Dark", "Bright"),
            ("One-shot", "Ambience"),
            ("Close", "Far"),
            ("Wet", "Dry"),
            ("Soft", "Hard")
        ]
        
        import random
        x_axis, y_axis = random.choice(suggestions)
        self.x_axis_input.setText(x_axis)
        self.y_axis_input.setText(y_axis)
    
    def _on_axes_toggle(self, checked: bool):
        """动态轴开关切换"""
        self.axis_config['active'] = checked
        self.axis_config['x'] = self.x_axis_input.text()
        self.axis_config['y'] = self.y_axis_input.text()
        
        if checked:
            # 激活 Scatter 模式
            if self.visualizer:
                self.visualizer.set_view_mode('scatter')
                self.visualizer.set_axis_config(self.axis_config)
            self.status_label.setText("● Scatter Mode Active")
        else:
            # 返回 Explorer 模式
            if self.visualizer:
                self.visualizer.set_view_mode('explorer')
            self.status_label.setText("● Explorer Mode")
    
    def _on_zoom_changed(self, zoom_level: float):
        """缩放级别改变"""
        if self.visualizer:
            self.visualizer.update_lod(zoom_level)
    
    def _on_selection_made(self, selection_rect: QRectF):
        """框选完成 - 显示框选区域内的所有文件"""
        if not self.visualizer:
            return
        
        # 获取框选区域内的所有文件
        selected_metadata = self.visualizer.get_items_in_rect(selection_rect)
        
        if selected_metadata:
            # 显示在检查器面板
            self.inspector.show_metadata_list(selected_metadata)
        else:
            # 如果没有选中任何项，清空面板
            self.inspector.clear()
    
    def _on_search(self, query: str):
        """搜索处理 - 搜索时自动切换到 Gravity 模式"""
        if not self.search_core or not self.visualizer:
            return
        
        try:
            if not query.strip():
                # 清空搜索，返回 Explorer 模式
                self.visualizer.clear_highlights()
                self.visualizer.set_view_mode('explorer')
                self.explorer_btn.setChecked(True)
                self.gravity_btn.setChecked(False)
                self.status_label.setText("● Explorer Mode")
                return
            
            self.status_label.setText(f"Searching: {query}...")
            
            # 执行搜索
            results = self.search_core.search_by_text(query, top_k=50)
            
            if results:
                # 获取结果索引和相关性分数
                result_indices = []
                result_scores = {}
                for metadata, score in results:
                    # 找到对应的索引
                    for i, meta in enumerate(self.search_core.metadata):
                        if meta.get('recID') == metadata.get('recID'):
                            result_indices.append(i)
                            result_scores[i] = score
                            break
                
                # 切换到 Gravity 模式并应用螺旋排列
                self.gravity_btn.setChecked(True)
                self.explorer_btn.setChecked(False)
                self.visualizer.apply_search_gravity(result_indices, result_scores)
                
                self.status_label.setText(f"● Found {len(results)} results (Gravity Mode)")
            else:
                self.status_label.setText("No results found")
                self.visualizer.clear_highlights()
                
        except Exception as e:
            self.status_label.setText(f"Search error: {str(e)}")
            print(f"[ERROR] 搜索失败: {e}")


