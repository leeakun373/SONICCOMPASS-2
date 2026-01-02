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
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        scale_factor = 1.15
        if event.angleDelta().y() < 0:
            scale_factor = 1.0 / scale_factor
        
        self.scale(scale_factor, scale_factor)
        
        # 通知 LOD 更新 - 使用真实的 transform scale
        zoom_level = self.transform().m11()
        self.zoom_changed.emit(zoom_level)
    
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

