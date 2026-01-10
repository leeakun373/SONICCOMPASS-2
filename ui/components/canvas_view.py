"""
画布视图 - 支持缩放和平移，LOD 切换
"""

from PySide6.QtWidgets import QGraphicsView, QFrame
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class CanvasView(QGraphicsView):
    """画布视图 - 支持缩放和平移，LOD 切换"""
    
    zoom_changed = Signal(float)
    selection_made = Signal(QRectF)  # 框选完成信号，传递场景坐标矩形
    mouse_moved = Signal(QPointF)  # 鼠标坐标变化信号（类属性）
    
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
        
        # 启用鼠标跟踪（用于双击事件和坐标显示）
        self.setMouseTracking(True)
        
        # 坐标显示相关
        self.mouse_pos = None  # 当前鼠标位置（场景坐标）
        self.show_axes = False  # 是否显示坐标轴
        self.show_range_circle = False  # 是否显示范围圆圈
        self.current_mouse_scene_pos = QPointF()  # 存储鼠标当前场景坐标
        self.range_radius = 100.0  # 范围圆圈的半径（场景坐标单位）
    
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
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于坐标显示"""
        super().mouseMoveEvent(event)
        # 将视图坐标转换为场景坐标
        scene_pos = self.mapToScene(event.pos())
        self.mouse_pos = scene_pos
        self.current_mouse_scene_pos = scene_pos
        # 发送鼠标移动信号（类属性 Signal 可以直接调用 emit）
        self.mouse_moved.emit(scene_pos)
        # 如果需要显示范围圆圈，触发重绘
        if self.show_range_circle:
            self.viewport().update()
    
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
    
    def set_show_axes(self, show: bool):
        """设置是否显示坐标轴"""
        self.show_axes = show
        self.viewport().update()
    
    def set_show_range_circle(self, show: bool):
        """设置是否显示范围圆圈"""
        self.show_range_circle = show
        self.viewport().update()
    
    def set_range_radius(self, radius: float):
        """设置范围圆圈的半径（场景坐标单位）"""
        self.range_radius = radius
        if self.show_range_circle:
            self.viewport().update()
    
    def paintEvent(self, event):
        """重写绘制事件，添加坐标轴和范围圆圈"""
        # 先调用父类的绘制（绘制场景内容）
        super().paintEvent(event)
        
        # 如果需要绘制坐标轴或范围圆圈，在顶层绘制
        if self.show_axes or self.show_range_circle:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 获取视口和场景的矩形
            viewport_rect = self.viewport().rect()
            scene_rect = self.sceneRect() if self.scene() else QRectF()
            
            if self.show_axes:
                # 绘制坐标轴
                self._draw_axes(painter, viewport_rect, scene_rect)
            
            if self.show_range_circle:
                # 绘制范围圆圈
                self._draw_range_circle(painter, viewport_rect)
            
            painter.end()
    
    def _draw_axes(self, painter: QPainter, viewport_rect: QRectF, scene_rect: QRectF):
        """
        绘制坐标轴和网格线（参考 verify_subset.py 的风格）
        显示 3000x3000 的坐标范围，添加网格线和刻度标签
        """
        # 定义坐标范围（固定 3000x3000）
        coord_min = 0.0
        coord_max = 3000.0
        
        # 计算场景中的坐标范围（从场景矩形或使用默认值）
        if scene_rect.isValid() and scene_rect.width() > 0 and scene_rect.height() > 0:
            actual_min_x = min(scene_rect.left(), coord_min)
            actual_max_x = max(scene_rect.right(), coord_max)
            actual_min_y = min(scene_rect.top(), coord_min)
            actual_max_y = max(scene_rect.bottom(), coord_max)
        else:
            actual_min_x = coord_min
            actual_max_x = coord_max
            actual_min_y = coord_min
            actual_max_y = coord_max
        
        # 设置网格步长（每 500 个单位一条网格线）
        grid_step = 500.0
        
        # 绘制网格线（浅色、细线）
        grid_pen = QPen(QColor(60, 60, 60, 60))  # 深灰色，很淡
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        
        # 绘制垂直网格线（X轴方向）
        x = actual_min_x
        while x <= actual_max_x:
            if x >= coord_min and x <= coord_max:  # 只在 0-3000 范围内绘制
                start_scene = QPointF(x, actual_min_y)
                end_scene = QPointF(x, actual_max_y)
                start_view = self.mapFromScene(start_scene)
                end_view = self.mapFromScene(end_scene)
                
                # 只绘制在视口可见范围内的线
                if (start_view.x() >= -10 and start_view.x() <= viewport_rect.width() + 10):
                    painter.drawLine(start_view, end_view)
            x += grid_step
        
        # 绘制水平网格线（Y轴方向）
        y = actual_min_y
        while y <= actual_max_y:
            if y >= coord_min and y <= coord_max:  # 只在 0-3000 范围内绘制
                start_scene = QPointF(actual_min_x, y)
                end_scene = QPointF(actual_max_x, y)
                start_view = self.mapFromScene(start_scene)
                end_view = self.mapFromScene(end_scene)
                
                # 只绘制在视口可见范围内的线
                if (start_view.y() >= -10 and start_view.y() <= viewport_rect.height() + 10):
                    painter.drawLine(start_view, end_view)
            y += grid_step
        
        # 绘制坐标轴（粗线、高对比度）
        axis_pen = QPen(QColor(150, 150, 150, 200))  # 浅灰色，更明显
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)
        
        # 计算原点在视口中的位置
        origin_scene = QPointF(0, 0)
        origin_view = self.mapFromScene(origin_scene)
        
        # 绘制 X 轴（水平线，从 0 到 3000）
        x_axis_start = QPointF(coord_min, 0)
        x_axis_end = QPointF(coord_max, 0)
        x_start_view = self.mapFromScene(x_axis_start)
        x_end_view = self.mapFromScene(x_axis_end)
        
        # 只在视口可见范围内绘制
        if (x_start_view.y() >= -10 and x_start_view.y() <= viewport_rect.height() + 10):
            painter.drawLine(x_start_view, x_end_view)
            
            # 绘制 X 轴刻度标签
            painter.setPen(QPen(QColor(180, 180, 180, 230)))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            
            # 在每个网格点绘制刻度标签
            x = 0
            while x <= coord_max:
                tick_scene = QPointF(x, 0)
                tick_view = self.mapFromScene(tick_scene)
                if tick_view.x() >= 0 and tick_view.x() <= viewport_rect.width():
                    # 绘制刻度标记
                    tick_length = 5
                    painter.drawLine(
                        tick_view.x(), tick_view.y() - tick_length,
                        tick_view.x(), tick_view.y() + tick_length
                    )
                    # 绘制刻度标签
                    label_text = f"{int(x)}"
                    label_rect = painter.fontMetrics().boundingRect(label_text)
                    painter.drawText(
                        tick_view.x() - label_rect.width() // 2,
                        tick_view.y() + tick_length + label_rect.height() + 2,
                        label_text
                    )
                x += grid_step
            
            # 绘制 X 轴标签
            painter.setPen(QPen(QColor(200, 200, 200, 255)))
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(x_end_view.x() + 10, x_end_view.y() - 5, "X (0-3000)")
        
        # 绘制 Y 轴（垂直线，从 0 到 3000）
        y_axis_start = QPointF(0, coord_min)
        y_axis_end = QPointF(0, coord_max)
        y_start_view = self.mapFromScene(y_axis_start)
        y_end_view = self.mapFromScene(y_axis_end)
        
        # 只在视口可见范围内绘制
        if (y_start_view.x() >= -10 and y_start_view.x() <= viewport_rect.width() + 10):
            painter.setPen(axis_pen)
            painter.drawLine(y_start_view, y_end_view)
            
            # 绘制 Y 轴刻度标签
            painter.setPen(QPen(QColor(180, 180, 180, 230)))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            
            # 在每个网格点绘制刻度标签（Y轴是从上到下，所以坐标需要翻转）
            y = 0
            while y <= coord_max:
                tick_scene = QPointF(0, y)
                tick_view = self.mapFromScene(tick_scene)
                if tick_view.y() >= 0 and tick_view.y() <= viewport_rect.height():
                    # 绘制刻度标记
                    tick_length = 5
                    painter.drawLine(
                        tick_view.x() - tick_length, tick_view.y(),
                        tick_view.x() + tick_length, tick_view.y()
                    )
                    # 绘制刻度标签
                    label_text = f"{int(y)}"
                    label_rect = painter.fontMetrics().boundingRect(label_text)
                    painter.drawText(
                        tick_view.x() - tick_length - label_rect.width() - 5,
                        tick_view.y() + label_rect.height() // 2,
                        label_text
                    )
                y += grid_step
            
            # 绘制 Y 轴标签
            painter.setPen(QPen(QColor(200, 200, 200, 255)))
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(y_start_view.x() + 10, y_start_view.y() + 20, "Y (0-3000)")
        
        # 绘制原点标记
        if (origin_view.x() >= -10 and origin_view.x() <= viewport_rect.width() + 10 and
            origin_view.y() >= -10 and origin_view.y() <= viewport_rect.height() + 10):
            painter.setPen(QPen(QColor(255, 255, 255, 255)))
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawEllipse(origin_view, 4, 4)
            
            # 原点标签
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(origin_view.x() + 8, origin_view.y() - 8, "O(0,0)")
    
    def _draw_range_circle(self, painter: QPainter, viewport_rect: QRectF):
        """绘制鼠标位置的范围圆圈"""
        if self.current_mouse_scene_pos.isNull():
            return
        
        # 将鼠标场景坐标转换为视口坐标
        mouse_view = self.mapFromScene(self.current_mouse_scene_pos)
        
        # 计算圆圈在视口中的半径（需要考虑缩放）
        transform = self.transform()
        scale = transform.m11()  # 获取 X 轴缩放因子
        if scale <= 0:
            return
        
        # 场景坐标的半径转换为视口像素
        circle_radius_px = self.range_radius * scale
        
        # 绘制圆圈（半透明填充 + 边框）
        brush = QBrush(QColor(100, 150, 255, 30))  # 浅蓝色，半透明填充
        pen = QPen(QColor(100, 150, 255, 200), 1)  # 蓝色边框
        
        painter.setBrush(brush)
        painter.setPen(pen)
        painter.drawEllipse(mouse_view, circle_radius_px, circle_radius_px)
        
        # 绘制半径标签
        painter.setPen(QPen(QColor(150, 150, 150, 255)))
        label_text = f"R={self.range_radius:.1f}"
        label_pos = QPointF(mouse_view.x() + circle_radius_px + 5, mouse_view.y())
        painter.drawText(label_pos, label_text)

