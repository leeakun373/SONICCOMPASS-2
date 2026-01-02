"""
Sonic Compass 主窗口
深色赛博朋克风格的可视化界面
"""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QRectF

from ui.components import CanvasView, SearchBar, InspectorPanel, UniversalTagger
from ui.visualizer import SonicUniverse
from ui.styles import GLOBAL_STYLESHEET
from core import DataProcessor, SearchCore, VectorEngine, UCSManager
from data import SoundminerImporter

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
        
        layout.addStretch()
        
        # 状态信息
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("color: #5F636E; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        return sidebar
    
    def _load_data(self):
        """加载数据"""
        try:
            self.status_label.setText("Loading data...")
            
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
            
            # 加载索引
            metadata, embeddings = self.processor.load_index()
            
            # 加载坐标
            coords_2d = self.processor.load_coordinates()
            if coords_2d is None:
                print("[WARNING] 未找到预计算的坐标，将在初始化时计算")
            
            # 创建搜索核心
            self.search_core = SearchCore(
                vector_engine=vector_engine,
                metadata=metadata,
                embeddings=embeddings
            )
            
            # 创建可视化场景
            self.visualizer = SonicUniverse(
                metadata,
                embeddings,
                coords_2d=coords_2d,
                hex_size=50.0,
                search_core=self.search_core  # 传入 search_core 用于 Scatter 模式
            )
            self.canvas_view.setScene(self.visualizer)
            
            # 设置场景视图
            self.canvas_view.fitInView(
                QRectF(0, 0, 1000, 1000),
                Qt.AspectRatioMode.KeepAspectRatio
            )
            
            # 设置画布交互
            self._setup_canvas_interaction()
            
            self.status_label.setText(f"Loaded {len(metadata)} items")
            importer.close()
            
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"[ERROR] 数据加载失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_canvas_interaction(self):
        """设置画布交互"""
        if not self.visualizer:
            return
        
        # 通过重写场景的鼠标事件来处理点击和右键
        original_mouse_press = self.visualizer.mousePressEvent
        original_context_menu = self.visualizer.contextMenuEvent
        
        def custom_mouse_press(event):
            if event.button() == Qt.MouseButton.LeftButton:
                # 调用原始处理
                original_mouse_press(event)
                
                # 获取点击位置的项
                scene_pos = event.scenePos()
                items = self.visualizer.items(scene_pos)
                if items:
                    item = items[0]
                    data = item.data(0)
                    if data:
                        if data.get('type') == 'point':
                            metadata = data.get('metadata')
                            if metadata:
                                self.inspector.show_metadata(metadata)
                        elif data.get('type') == 'hex':
                            # 显示六边形内第一个点的元数据
                            metadata_list = data.get('metadata', [])
                            if metadata_list:
                                self.inspector.show_metadata(metadata_list[0])
            else:
                original_mouse_press(event)
        
        def custom_context_menu(event):
            """右键菜单事件"""
            scene_pos = event.scenePos()
            items = self.visualizer.items(scene_pos)
            if items:
                item = items[0]
                data = item.data(0)
                if data:
                    # 显示右键菜单
                    view_pos = self.canvas_view.mapFromScene(scene_pos)
                    global_pos = self.canvas_view.mapToGlobal(view_pos)
                    self._show_context_menu(global_pos.x(), global_pos.y(), data)
        
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


