"""
画布视图 - 支持缩放和平移，LOD 切换
"""

from PySide6.QtWidgets import QGraphicsView, QFrame
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class CanvasView(QGraphicsView):
    """画布视图 - 支持缩放和平移，LOD 切换"""
    
    zoom_changed = Signal(float)
    selection_made = Signal(QRectF)  # 框选完成信号，传递场景坐标矩形
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 【关键】开启 OpenGL 硬件加速视口
        # 这会让显卡接管渲染，从 10 FPS 提升到 60 FPS
        try:
            self.setViewport(QOpenGLWidget())
        except Exception:
            # 如果 OpenGL 不可用，回退到默认视口
            pass
        
        # 【关键】优化渲染参数
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        # 默认：左键拖拽平移，右键框选
        self.setDragMode(self.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(self.ViewportAnchor.AnchorUnderMouse)
        
        # 隐藏滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 设置背景
        self.setBackgroundBrush(QColor('#0B0C0E'))
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # 框选相关
        self._selection_start_pos = None
        self._is_selecting = False
        
        # 启用鼠标跟踪（用于双击事件）
        self.setMouseTracking(True)
    
    def _calculate_min_zoom(self) -> float:
        """计算最小缩放级别（刚好能看到全图）"""
        try:
            scene = self.scene()
            if scene is None:
                return 0.1
            
            scene_rect = scene.itemsBoundingRect()
            if scene_rect.isEmpty() or scene_rect.width() <= 0 or scene_rect.height() <= 0:
                return 0.1
            
            view_rect = self.viewport().rect()
            if view_rect.width() <= 0 or view_rect.height() <= 0:
                return 0.1
            
            scale_x = view_rect.width() / scene_rect.width()
            scale_y = view_rect.height() / scene_rect.height()
            min_scale = min(scale_x, scale_y) * 0.9  # 留 10% 边距
            
            # 确保返回的值在合理范围内
            if min_scale < 0.01 or min_scale > 5.0:
                return 0.1
            
            return min_scale
        except Exception:
            # 任何错误都返回默认值
            return 0.1
    
    def fit_scene_to_view(self):
        """适配场景到视图（初始化时调用）"""
        scene = self.scene()
        if scene is None:
            print("[DEBUG] fit_scene_to_view: scene is None")
            return
        
        # 使用场景的 sceneRect 而不是 itemsBoundingRect，更可靠
        scene_rect = scene.sceneRect()
        print(f"[DEBUG] fit_scene_to_view: sceneRect = {scene_rect}")
        
        if scene_rect.isEmpty():
            # 如果 sceneRect 为空，尝试使用 itemsBoundingRect
            print("[DEBUG] fit_scene_to_view: sceneRect is empty, trying itemsBoundingRect")
            scene_rect = scene.itemsBoundingRect()
            print(f"[DEBUG] fit_scene_to_view: itemsBoundingRect = {scene_rect}")
        
        if not scene_rect.isEmpty() and scene_rect.width() > 0 and scene_rect.height() > 0:
            # 添加 10% padding
            padding_x = scene_rect.width() * 0.1
            padding_y = scene_rect.height() * 0.1
            scene_rect.adjust(-padding_x, -padding_y, padding_x, padding_y)
            print(f"[DEBUG] fit_scene_to_view: adjusted rect = {scene_rect}")
            
            # 重置变换矩阵，然后适配视图
            self.resetTransform()
            viewport_rect = self.viewport().rect()
            print(f"[DEBUG] fit_scene_to_view: viewport size = {viewport_rect.width()}x{viewport_rect.height()}")
            
            self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            
            # 检查适配结果
            transform = self.transform()
            print(f"[DEBUG] fit_scene_to_view: transform matrix = m11={transform.m11()}, m22={transform.m22()}")
            
            # 通知 LOD 更新
            zoom_level = transform.m11()
            if zoom_level > 0:
                self.zoom_changed.emit(zoom_level)
                print(f"[DEBUG] fit_scene_to_view: zoom_level = {zoom_level}")
        else:
            print(f"[WARNING] fit_scene_to_view: scene_rect is invalid! isEmpty={scene_rect.isEmpty()}, width={scene_rect.width()}, height={scene_rect.height()}")
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放（带 min/max 限制）"""
        # 接受事件，防止传递给父组件
        event.accept()
        
        # 获取当前缩放级别
        current_zoom = self.transform().m11()
        if current_zoom <= 0:
            # 如果当前缩放无效，重置到默认值
            current_zoom = 1.0
            self.resetTransform()
        
        scale_factor = 1.15
        if event.angleDelta().y() < 0:
            scale_factor = 1.0 / scale_factor
        
        new_zoom = current_zoom * scale_factor
        
        # 计算动态最小缩放级别
        min_zoom = self._calculate_min_zoom()
        max_zoom = 20.0  # 允许更大的放大
        
        # 只在极端情况下限制缩放
        if new_zoom < min_zoom:
            # 如果新缩放太小，限制到最小值
            if current_zoom > 0:
                target_scale = min_zoom / current_zoom
                if target_scale > 0:
                    self.scale(target_scale, target_scale)
                    self.zoom_changed.emit(self.transform().m11())
        elif new_zoom > max_zoom:
            # 如果新缩放太大，限制到最大值
            if current_zoom > 0:
                target_scale = max_zoom / current_zoom
                if target_scale > 0:
                    self.scale(target_scale, target_scale)
                    self.zoom_changed.emit(self.transform().m11())
        else:
            # 正常缩放（以鼠标位置为中心）
            self.scale(scale_factor, scale_factor)
            zoom_level = self.transform().m11()
            self.zoom_changed.emit(zoom_level)
    
    def reset_view(self):
        """重置视图到初始状态"""
        self.fit_scene_to_view()
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        # 按 R 键重置视图
        if event.key() == Qt.Key.Key_R and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.reset_view()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 左键：拖拽平移
            self.setDragMode(self.DragMode.ScrollHandDrag)
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键：框选
            self.setDragMode(self.DragMode.RubberBandDrag)
            self._selection_start_pos = event.pos()
            self._is_selecting = True
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.RightButton and self._is_selecting:
            # 右键框选完成
            self._is_selecting = False
            selection_rect = self.rubberBandRect()
            if selection_rect.width() > 5 and selection_rect.height() > 5:
                # 转换为场景坐标
                # 使用 mapToScene 将视口坐标转换为场景坐标
                top_left = self.mapToScene(selection_rect.topLeft())
                bottom_right = self.mapToScene(selection_rect.bottomRight())
                scene_rect = QRectF(top_left, bottom_right).normalized()
                
                # 发送框选信号
                self.selection_made.emit(scene_rect)
            
            # 清除框选并恢复拖拽模式
            self.setDragMode(self.DragMode.ScrollHandDrag)
        elif event.button() == Qt.MouseButton.LeftButton:
            # 左键释放后保持拖拽模式
            self.setDragMode(self.DragMode.ScrollHandDrag)
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件：重置视图到初始状态"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_view()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

