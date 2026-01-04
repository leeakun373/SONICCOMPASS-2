"""
ui/visualizer/sonic_universe.py
可视化引擎 - 修复版 (Fix: Interaction, Layout, Rendering)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QPolygonF, QPainter, QRadialGradient, QFont, QStaticText
import math
import sys
from pathlib import Path
from collections import Counter

# 导入 Category 颜色映射器
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from core.category_color_mapper import CategoryColorMapper
except ImportError:
    CategoryColorMapper = None

try:
    from core.ucs_manager import UCSManager
except ImportError:
    UCSManager = None

# 尝试导入 KDTree 用于极速查询
try:
    from scipy.spatial import cKDTree
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False


class HexGridLayer(QGraphicsItem):
    """六边形网格层 - 修复版"""
    
    # Category 颜色映射器
    _color_mapper: Optional['CategoryColorMapper'] = None
    
    @classmethod
    def _get_color_mapper(cls) -> Optional['CategoryColorMapper']:
        if cls._color_mapper is None and CategoryColorMapper is not None:
            try:
                cls._color_mapper = CategoryColorMapper()
            except Exception as e:
                print(f"[WARNING] 初始化 CategoryColorMapper 失败: {e}")
        return cls._color_mapper
    
    def __init__(self, size, ucs_manager=None):
        super().__init__()
        self.hex_size = size
        self.ucs_manager = ucs_manager  # UCSManager 实例
        self.grid_data = {}  # (q, r) -> [indices]
        self.metadata = []
        self.coords = None
        self.category_labels = []  # LOD 0 的大类标签
        self.subcategory_labels = {}  # LOD 1 的子类标签: (q, r) -> text
        self.show_category_labels = False  # LOD 0 显示大类标签
        self.show_subcategory_labels = False  # LOD 1 显示子类标签
        self.current_zoom = 1.0
        self.current_lod = 0
        
    def set_data(self, grid_map, metadata, coords):
        self.grid_data = grid_map
        self.metadata = metadata
        self.coords = coords
        self.prepareGeometryChange()
        # 预计算标签
        self._generate_labels(metadata)
        
    def _get_hex_neighbors(self, q, r):
        """获取六边形的6个相邻坐标"""
        # 六边形6个方向的偏移量（轴向坐标）
        directions = [
            (1, 0),   # 右
            (1, -1),  # 右上
            (0, -1),  # 左上
            (-1, 0),  # 左
            (-1, 1),  # 左下
            (0, 1)    # 右下
        ]
        return [(q + dq, r + dr) for dq, dr in directions]
    
    def _find_connected_components(self, category_positions):
        """
        使用BFS找到连通域（岛屿）
        返回: [(category, [(q, r), ...]), ...] 每个连通域及其六边形坐标列表
        """
        visited = set()
        components = []
        
        for category, positions in category_positions.items():
            # 为该类别建立位置集合以便快速查找
            position_set = set(positions)
            
            # 对每个未访问的位置进行BFS
            for start_pos in positions:
                if start_pos in visited:
                    continue
                
                # BFS遍历连通域
                component = []
                queue = [start_pos]
                visited.add(start_pos)
                
                while queue:
                    current_q, current_r = queue.pop(0)
                    component.append((current_q, current_r))
                    
                    # 检查所有邻居
                    for neighbor in self._get_hex_neighbors(current_q, current_r):
                        if neighbor in position_set and neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                if component:
                    components.append((category, component))
        
        return components
    
    def _generate_labels(self, metadata):
        """生成标签：LOD 0 大类标签和 LOD 1 子类标签"""
        # 生成 LOD 0 大类标签（连通域聚类）
        self.category_labels = []
        category_positions = {}  # category -> [(q, r), ...]
        
        # 生成 LOD 1 子类标签（每个六边形中心）
        self.subcategory_labels = {}
        
        mapper = self._get_color_mapper()
        
        for (q, r), indices in self.grid_data.items():
            if not indices:
                continue
            
            # 获取第一个点的分类信息
            first_idx = indices[0]
            if first_idx >= len(metadata):
                continue
                
            meta = metadata[first_idx]
            cat_id = meta.get('category', '')
            
            # LOD 0: 收集大类位置用于连通域聚类
            if mapper:
                category = mapper.get_category_from_catid(cat_id)
                if category:
                    if category not in category_positions:
                        category_positions[category] = []
                    category_positions[category].append((q, r))
            
            # LOD 1: 生成子类标签（强制使用 UCS subcategory）
            center = self._hex_to_pixel(q, r)
            all_subcategories = []
            
            # 收集该六边形内所有点的 subcategory
            for idx in indices:
                if idx >= len(metadata):
                    continue
                item_meta = metadata[idx]
                
                # 优先使用 metadata 中的 subcategory
                subcat = item_meta.get('subcategory', '')
                
                # 如果 subcategory 为空，使用 UCSManager 解析 CatID
                if not subcat:
                    item_cat_id = item_meta.get('category', '')
                    if item_cat_id and self.ucs_manager:
                        ucs_category = self.ucs_manager.get_category_by_catid(item_cat_id)
                        if ucs_category:
                            subcat = ucs_category.subcategory
                
                # 如果仍然为空，尝试从 CategoryColorMapper 获取
                if not subcat and item_cat_id and mapper:
                    # 尝试通过 CategoryColorMapper 获取（作为回退）
                    category = mapper.get_category_from_catid(item_cat_id)
                    if category:
                        subcat = category  # 如果没有 subcategory，使用 category 作为回退
                
                if subcat:
                    all_subcategories.append(str(subcat))
            
            # 使用 Counter 统计最频繁的 SubCategory (Mode)
            if all_subcategories:
                counter = Counter(all_subcategories)
                most_common_subcat = counter.most_common(1)[0][0]
                
                # 获取该六边形主导分类的颜色
                label_color = None
                if mapper:
                    label_color = mapper.get_color_for_catid(cat_id)
                
                self.subcategory_labels[(q, r)] = {
                    'text': most_common_subcat[:15],  # 限制长度
                    'pos': center,
                    'color': label_color
                }
        
        # LOD 0: 使用连通域聚类算法为每个"岛屿"生成标签
        if category_positions:
            components = self._find_connected_components(category_positions)
            
            for category, component_positions in components:
                if len(component_positions) >= 1:
                    # 计算该连通域的几何中心
                    centers = [self._hex_to_pixel(q, r) for q, r in component_positions]
                    centroid_x = sum(c.x() for c in centers) / len(centers)
                    centroid_y = sum(c.y() for c in centers) / len(centers)
                    
                    # 获取该大类的颜色
                    label_color = None
                    if mapper:
                        # 从组件中获取第一个六边形的CatID来确定颜色
                        first_hex = component_positions[0]
                        if first_hex in self.grid_data:
                            first_idx = self.grid_data[first_hex][0]
                            if first_idx < len(metadata):
                                cat_id = metadata[first_idx].get('category', '')
                                label_color = mapper.get_color_for_catid(cat_id)
                    
                    self.category_labels.append({
                        'text': category.upper(),
                        'pos': QPointF(centroid_x, centroid_y),
                        'color': label_color
                    })
    
    def boundingRect(self):
        # 估算一个超大范围即可，视口裁剪由 paint 处理
        return QRectF(-50000, -50000, 100000, 100000)
        
    def paint(self, painter, option, widget):
        # 1. 视口裁剪：只画可见区域
        clip_rect = option.exposedRect
        
        # 简化的绘制逻辑
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制参数 (赛博朋克风)
        gap_ratio = 0.92  # 92% 大小 -> 8% 黑色缝隙
        
        # 根据 LOD 设置绘制样式
        lod = self.current_lod
        
        for (q, r), indices in self.grid_data.items():
            center = self._hex_to_pixel(q, r)
            
            # 改进的裁剪检查：检查六边形是否与裁剪区域相交
            # 考虑六边形的尺寸，而不是只检查中心点
            hex_radius = self.hex_size * 0.92  # 使用 gap_ratio 后的实际尺寸
            hex_rect = QRectF(
                center.x() - hex_radius,
                center.y() - hex_radius,
                hex_radius * 2,
                hex_radius * 2
            )
            if not clip_rect.intersects(hex_rect):
                continue
                
            # 获取颜色（基于第一个点的分类）- 统一使用 CategoryColorMapper
            color = None
            if indices and len(indices) > 0 and self.metadata:
                idx = indices[0]
                if idx < len(self.metadata):
                    cat_id = self.metadata[idx].get('category', '')
                    mapper = self._get_color_mapper()
                    if mapper:
                        color = mapper.get_color_for_catid(cat_id)
                        # 根据 LOD 调整透明度（在_draw_single_hex中会再次设置，这里只是设置基础颜色）
                        # 不在这里设置Alpha，让_draw_single_hex统一处理
            
            # 如果没有映射器或映射失败，使用默认灰色（CategoryColorMapper 也会返回灰色）
            if color is None:
                mapper = self._get_color_mapper()
                if mapper:
                    color = mapper.get_color_for_catid(None)  # None 会返回灰色
                    # 不在这里设置Alpha，让_draw_single_hex统一处理
                else:
                    # 最后的回退（如果没有映射器）
                    color = QColor('#6B7280')  # 灰色
                    # 不在这里设置Alpha，让_draw_single_hex统一处理
                
            # 绘制六边形
            self._draw_single_hex(painter, center, len(indices), gap_ratio, color, lod)

        # 绘制标签：LOD 0 显示大类标签，LOD 1 显示子类标签
        if lod == 0 and self.show_category_labels:
            self._draw_category_labels(painter, clip_rect)
        elif lod == 1 and self.show_subcategory_labels:
            self._draw_subcategory_labels(painter, clip_rect)
            
    def _draw_single_hex(self, painter, center, density, gap_ratio, color, lod):
        size = self.hex_size * gap_ratio
        # 创建六边形路径
        hex_poly = QPolygonF()
        for i in range(6):
            angle = math.pi / 3 * i
            x = center.x() + size * math.cos(angle)
            y = center.y() + size * math.sin(angle)
            hex_poly.append(QPointF(x, y))
        
        # 根据 LOD 设置填充和描边样式（所有颜色都来自 CategoryColorMapper）
        if lod == 0:
            # LOD 0: 填充透明度 60，描边透明度 220
            fill_color = QColor(color)
            fill_color.setAlpha(60)  # 填充 Alpha=60
            border_color = QColor(color)
            border_color.setAlpha(220)  # 描边 Alpha=220
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QBrush(fill_color))
        else:
            # LOD 1: 使用分类颜色，填充色稍微加深
            fill_color = QColor(color)
            # 保持传入的透明度（150），但可以稍微加深
            fill_color.setAlpha(color.alpha())
            border_color = QColor(color)
            border_color.setAlpha(min(255, color.alpha() + 50))
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(QBrush(fill_color))
        
        painter.drawPolygon(hex_poly)

    def _hex_to_pixel(self, q, r):
        size = self.hex_size
        x = size * (3./2 * q)
        y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return QPointF(x, y)
    
    def _draw_category_labels(self, painter, clip_rect):
        """绘制 LOD 0 大类标签（带反向缩放）"""
        # 反向缩放：zoom 越小，文字越大
        # 使用非线性缩放公式，使放大时字体缩小得更快
        base_font_size = self.hex_size * 2.0
        zoom_factor = max(0.3, self.current_zoom)  # 防止除零
        font_size = int(base_font_size / pow(zoom_factor, 0.5))  # 非线性反向缩放
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        for label in self.category_labels:
            if not clip_rect.contains(label['pos']):
                continue
            
            static_text = QStaticText(label['text'])
            text_rect = painter.fontMetrics().boundingRect(label['text'])
            text_x = label['pos'].x() - text_rect.width() / 2
            text_y = label['pos'].y() + text_rect.height() / 2
            
            # 绘制半透明黑色背景框
            bg_rect = QRectF(text_x - 4, text_y - text_rect.height() - 2, 
                            text_rect.width() + 8, text_rect.height() + 4)
            bg_color = QColor(0, 0, 0, 180)
            painter.fillRect(bg_rect, bg_color)
            
            # 绘制文字：使用CategoryColorMapper获取的颜色，如果没有则使用白色
            label_color = label.get('color')
            if label_color:
                text_color = QColor(label_color)
                text_color.setAlpha(255)  # 文字Alpha=255
            else:
                text_color = QColor(255, 255, 255, 255)
            
            painter.setPen(text_color)
            painter.drawStaticText(int(text_x), int(text_y), static_text)
    
    def _draw_subcategory_labels(self, painter, clip_rect):
        """绘制 LOD 1 子类标签（每个六边形中心）"""
        font_size = int(self.hex_size * 0.6)  # 小字号，不遮挡
        font = QFont("Segoe UI", font_size)
        painter.setFont(font)
        
        for (q, r), label_data in self.subcategory_labels.items():
            pos = label_data['pos']
            if not clip_rect.contains(pos):
                continue
            
            text = label_data['text']
            static_text = QStaticText(text)
            text_rect = painter.fontMetrics().boundingRect(text)
            text_x = pos.x() - text_rect.width() / 2
            text_y = pos.y() + text_rect.height() / 2
            
            # 绘制半透明背景以提高可读性
            bg_rect = QRectF(text_x - 2, text_y - text_rect.height(), 
                            text_rect.width() + 4, text_rect.height() + 4)
            bg_color = QColor(0, 0, 0, 150)
            painter.fillRect(bg_rect, bg_color)
            
            # 绘制文字：使用存储的颜色，如果没有则使用白色
            label_color = label_data.get('color')
            if label_color:
                text_color = QColor(label_color)
                text_color.setAlpha(220)
            else:
                text_color = QColor(255, 255, 255, 220)
            painter.setPen(text_color)
            painter.drawStaticText(int(text_x), int(text_y), static_text)
        
    def update_lod(self, zoom):
        """更新 LOD 层级"""
        # 确保 zoom 值有效
        if zoom <= 0:
            zoom = 1.0
        
        self.current_zoom = zoom
        
        if zoom < 0.6:
            # LOD 0: 宏观状态 - 只显示六边形网格和大类标签
            self.current_lod = 0
            self.show_category_labels = True
            self.show_subcategory_labels = False
            self.setOpacity(1.0)
        elif zoom < 1.8:
            # LOD 1: 微观状态 - 显示六边形网格和子类标签
            self.current_lod = 1
            self.show_category_labels = False
            self.show_subcategory_labels = True
            self.setOpacity(1.0)
        else:
            # LOD 2: 细节状态 - 六边形网格淡出
            self.current_lod = 2
            self.show_category_labels = False
            self.show_subcategory_labels = False
            self.setOpacity(0.15)  # 淡出到 15%
        
        self.update()


class DetailScatterLayer(QGraphicsItem):
    """细节散点层 - 修复版"""
    
    def __init__(self):
        super().__init__()
        self.points = None
        self.metadata = []
        self.visible = False
        self.highlighted_indices = set()
        
    def set_data(self, coords, metadata):
        self.points = coords
        self.metadata = metadata
        self.prepareGeometryChange()
    
    def set_highlighted_indices(self, indices):
        self.highlighted_indices = indices
        self.update()
    
    def boundingRect(self):
        return QRectF(-50000, -50000, 100000, 100000)
        
    def paint(self, painter, option, widget):
        if not self.visible or self.points is None:
            return
            
        # 视口裁剪
        clip_rect = option.exposedRect
        x1, y1, x2, y2 = clip_rect.left(), clip_rect.top(), clip_rect.right(), clip_rect.bottom()
        
        # Numpy 裁剪
        mask = (self.points[:,0] >= x1) & (self.points[:,0] <= x2) & \
               (self.points[:,1] >= y1) & (self.points[:,1] <= y2)
        visible_points = self.points[mask]
        visible_indices = np.where(mask)[0]
        
        if len(visible_points) == 0: 
            return
        
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 分离高亮点和普通点
        highlighted_mask = np.isin(visible_indices, list(self.highlighted_indices))
        highlighted_points = visible_points[highlighted_mask]
        normal_points = visible_points[~highlighted_mask]
        
        # 修复方点问题：使用 RoundCap
        if len(normal_points) > 0:
            pen = QPen(QColor(255, 255, 255, 200))
            pen.setWidthF(4.0)  # 点的大小
            pen.setCapStyle(Qt.RoundCap)  # 圆点！
            painter.setPen(pen)
            
            # 批量绘制
            qpoints = [QPointF(p[0], p[1]) for p in normal_points]
            painter.drawPoints(qpoints)
        
        # 绘制高亮点（白色，更大）
        if len(highlighted_points) > 0:
            pen = QPen(QColor(255, 255, 255, 255))
            pen.setWidthF(6.0)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            qpoints = [QPointF(p[0], p[1]) for p in highlighted_points]
            painter.drawPoints(qpoints)
        
    def update_lod(self, zoom):
        # LOD 2: 只有放大到细节状态才显示散点
        self.visible = (zoom >= 1.8)
        self.update()


class SonicUniverse(QGraphicsScene):
    """Sonic Universe 可视化场景 - 修复版"""
    
    def __init__(self, metadata, embeddings, coords_2d=None, hex_size=50.0, search_core=None, ucs_manager=None, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.embeddings = embeddings
        self.hex_size = float(hex_size)
        self.search_core = search_core
        self.ucs_manager = ucs_manager  # UCSManager 实例
        
        # 坐标处理
        self.coords_2d = coords_2d
        if self.coords_2d is None:
            # Fallback for safety
            self.coords_2d = np.random.rand(len(metadata), 2) * 10000
        
        # 归一化坐标
        self._normalize_coordinates()
        
        # 构建空间索引 (用于极速点击检测) - 将在 _build_scene_data 中使用最终显示坐标构建
        self.tree = None
        self.current_display_coords = None  # 最终的显示坐标（经过规整化）

        # 核心数据结构
        self.hex_layer = HexGridLayer(self.hex_size, ucs_manager=self.ucs_manager)
        self.scatter_layer = DetailScatterLayer()
        self.addItem(self.hex_layer)
        self.addItem(self.scatter_layer)
        
        # 确保散点在蜂窝之上
        self.hex_layer.setZValue(0)
        self.scatter_layer.setZValue(10)
        
        # 视图模式
        self.view_mode = 'explorer'
        self.original_coords_2d = self.norm_coords.copy() if hasattr(self, 'norm_coords') else None
        self.gravity_coords_2d = None
        self.scatter_coords_2d = None
        self.axis_config = None
        self.gravity_pillars = []
        self.gravity_weights = None
        self.highlighted_indices = set()
        self.current_zoom = 1.0
        
        # 构建网格
        self._build_scene_data()
    
    def _normalize_coordinates(self):
        """归一化坐标到紧凑画布范围（3000x3000）"""
        if self.coords_2d is None or len(self.coords_2d) == 0:
            return
        
        # 1. 坐标归一化到紧凑场景 (3000x3000) - 减少数据分散，让蜂窝更密集
        min_v = np.min(self.coords_2d, axis=0)
        max_v = np.max(self.coords_2d, axis=0)
        scale = 3000.0 / (np.max(max_v - min_v) + 1e-5)
        self.norm_coords = (self.coords_2d - min_v) * scale
    
    def _constrain_points_to_hex(self, coords):
        """
        散点规整化：将散点约束到六边形内部，使用局部向日葵螺旋布局
        
        规则 A (吸附)：计算每个点所属的六边形，获取该六边形的像素中心
        规则 B (内缩)：将点的位置限制在六边形中心的一定半径内 (hex_size * 0.9)
        规则 C (螺旋布局)：同一六边形内的多个点使用向日葵螺旋排列
        """
        if coords is None or len(coords) == 0:
            return coords
        
        # 黄金角度（度转弧度）
        GOLDEN_ANGLE_RAD = math.radians(137.508)
        
        constrained_coords = np.zeros_like(coords)
        hex_point_map = {}  # (q, r) -> [indices in this hex]
        
        # 步骤 1: 将每个点分配到对应的六边形
        for idx, (x, y) in enumerate(coords):
            q, r = self._pixel_to_hex(x, y)
            if (q, r) not in hex_point_map:
                hex_point_map[(q, r)] = []
            hex_point_map[(q, r)].append(idx)
        
        # 步骤 2: 为每个六边形内的点计算规整化位置（向日葵螺旋布局）
        max_radius = self.hex_size * 0.9  # 内缩到 90% 半径，确保不落在缝隙
        
        for (q, r), point_indices in hex_point_map.items():
            hex_center = self._hex_to_pixel(q, r)
            center_x, center_y = hex_center.x(), hex_center.y()
            
            # 按索引排序保证确定性
            sorted_indices = sorted(point_indices)
            total_points = len(sorted_indices)
            
            if total_points == 1:
                # 如果只有一个点，直接放在中心
                idx = sorted_indices[0]
                constrained_coords[idx] = [center_x, center_y]
            else:
                # 多个点：使用向日葵螺旋布局
                # 计算缩放系数 c，确保最大半径 < hex_size * 0.9
                # 对于最后一个点 i = total_points - 1，r = c * sqrt(i) < max_radius
                # 所以 c = max_radius / sqrt(total_points - 1)
                if total_points > 1:
                    c = max_radius / math.sqrt(total_points - 1)
                else:
                    c = 0.0
                
                for spiral_index, idx in enumerate(sorted_indices):
                    # 螺旋角度：使用黄金角度（137.508°）
                    angle = spiral_index * GOLDEN_ANGLE_RAD
                    
                    # 半径：r = c * sqrt(i)，确保最大半径 < hex_size * 0.9
                    radius = c * math.sqrt(spiral_index)
                    
                    # 计算偏移位置
                    offset_x = radius * math.cos(angle)
                    offset_y = radius * math.sin(angle)
                    
                    constrained_coords[idx] = [
                        center_x + offset_x,
                        center_y + offset_y
                    ]
        
        return constrained_coords
    
    def _build_scene_data(self):
        """完全基于数据生成网格，杜绝空蜂窝"""
        if not hasattr(self, 'norm_coords') or self.norm_coords is None or len(self.norm_coords) == 0:
            return

        # 2. 只有"有数据"的地方才会有蜂窝
        grid_map = {}  # (q, r) -> [indices]
        
        for idx, (x, y) in enumerate(self.norm_coords):
            q, r = self._pixel_to_hex(x, y)
            if (q, r) not in grid_map:
                grid_map[(q, r)] = []
            grid_map[(q, r)].append(idx)
        
        # 3. 规整化散点坐标（防止重叠和落在缝隙中）
        constrained_scatter_coords = self._constrain_points_to_hex(self.norm_coords)
        
        # 存储最终的显示坐标（用于点击检测）
        self.current_display_coords = constrained_scatter_coords
        
        # 4. 使用最终显示坐标构建空间索引（确保点击检测与渲染一致）
        if SCIPY_AVAILABLE and len(constrained_scatter_coords) > 0:
            self.tree = cKDTree(constrained_scatter_coords)
            
        # 5. 传递数据给图层
        self.hex_layer.set_data(grid_map, self.metadata, self.norm_coords)
        self.scatter_layer.set_data(constrained_scatter_coords, self.metadata)
        
        # 6. 自动调整相机范围（基于实际数据坐标）
        if len(self.norm_coords) > 0:
            min_x, min_y = self.norm_coords.min(axis=0)
            max_x, max_y = self.norm_coords.max(axis=0)
            margin = 500.0
            rect = QRectF(
                min_x - margin, min_y - margin,
                max_x - min_x + 2 * margin,
                max_y - min_y + 2 * margin
            )
            self.setSceneRect(rect)
        else:
            # 如果没有数据，使用默认范围
            self.setSceneRect(0, 0, 10000, 10000)
    
    def _pixel_to_hex(self, x, y):
        size = self.hex_size
        q = (2./3 * x) / size
        r = (-1./3 * x + math.sqrt(3)/3 * y) / size
        return self._hex_round(q, r)
    
    def _hex_to_pixel(self, q, r):
        """将六边形坐标转换为像素坐标"""
        size = self.hex_size
        x = size * (3./2 * q)
        y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return QPointF(x, y)

    def _hex_round(self, q, r):
        # 轴向坐标四舍五入算法
        s = -q - r
        rq, rr, rs = round(q), round(r), round(s)
        q_diff, r_diff, s_diff = abs(rq - q), abs(rr - r), abs(rs - s)
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        return int(rq), int(rr)

    # --- 交互核心：手动命中测试 ---
    def find_closest_data(self, scene_pos):
        """
        找到鼠标点击位置最近的数据
        根据LOD级别返回不同结果：
        - LOD < 2: 返回该六边形内的所有数据列表
        - LOD >= 2: 返回单个文件的详细信息
        """
        current_lod = self.current_zoom
        if current_lod < 0.6:
            lod_level = 0
        elif current_lod < 1.8:
            lod_level = 1
        else:
            lod_level = 2
        
        # LOD 门控：LOD < 2 时返回六边形内所有数据
        if lod_level < 2:
            # 根据点击位置找到对应的六边形坐标
            q, r = self._pixel_to_hex(scene_pos.x(), scene_pos.y())
            
            # 检查该六边形是否存在数据
            if hasattr(self, 'hex_layer') and self.hex_layer.grid_data:
                hex_key = (q, r)
                if hex_key in self.hex_layer.grid_data:
                    indices = self.hex_layer.grid_data[hex_key]
                    if indices:
                        # 返回该六边形内所有数据的元数据列表
                        metadata_list = []
                        for idx in indices:
                            if idx < len(self.metadata):
                                metadata_list.append(self.metadata[idx])
                        return {
                            'type': 'hex',
                            'hex_key': hex_key,
                            'indices': indices,
                            'metadata_list': metadata_list,
                            'count': len(metadata_list)
                        }
            return None
        
        # LOD >= 2: 使用KDTree进行精确的最近邻搜索
        if self.tree is None or self.current_display_coords is None:
            return None
        
        try:
            dist, idx = self.tree.query([scene_pos.x(), scene_pos.y()], distance_upper_bound=20)
            
            if dist == float('inf') or idx >= len(self.metadata):
                return None
            
            return {
                'type': 'point',
                'index': int(idx),
                'metadata': self.metadata[int(idx)],
                'pos': self.current_display_coords[int(idx)]
            }
        except Exception as e:
            print(f"[ERROR] find_closest_data 失败: {e}")
            return None
        
    def find_items_in_rect(self, rect):
        """找到框选区域内的所有数据"""
        if not hasattr(self, 'norm_coords') or self.norm_coords is None:
            return []
        
        # 简单的矩形过滤
        x1, y1 = rect.x(), rect.y()
        x2, y2 = x1 + rect.width(), y1 + rect.height()
        
        # 利用 numpy 快速过滤
        mask = (self.norm_coords[:,0] >= x1) & (self.norm_coords[:,0] <= x2) & \
               (self.norm_coords[:,1] >= y1) & (self.norm_coords[:,1] <= y2)
        
        indices = np.where(mask)[0]
        return [self.metadata[int(i)] for i in indices if int(i) < len(self.metadata)]

    def update_lod(self, zoom):
        # 确保 zoom 值有效
        if zoom <= 0:
            zoom = 1.0
        
        self.current_zoom = zoom
        if hasattr(self, 'hex_layer'):
            self.hex_layer.update_lod(zoom)
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.update_lod(zoom)
    
    def highlight_indices(self, indices: List[int]):
        """高亮指定的索引"""
        self.highlighted_indices = set(indices)
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.set_highlighted_indices(self.highlighted_indices)
    
    def set_view_mode(self, mode: str):
        """设置视图模式"""
        self.view_mode = mode
        # 根据模式更新坐标
        if mode == 'explorer' and self.original_coords_2d is not None:
            self.coords_2d = self.original_coords_2d.copy()
            self._rebuild_layers()
        elif mode == 'scatter' and self.scatter_coords_2d is not None:
            self.coords_2d = self.scatter_coords_2d.copy()
            self._rebuild_layers()
        elif mode == 'gravity' and self.gravity_coords_2d is not None:
            self.coords_2d = self.gravity_coords_2d.copy()
            self._rebuild_layers()
    
    def _rebuild_layers(self):
        """重建渲染层（当坐标改变时）"""
        # 重新归一化坐标
        self._normalize_coordinates()
        
        # 重建场景数据（这会更新图层和空间索引）
        self._build_scene_data()
    
    def set_gravity_pillars(self, pillars: List[str], weights: Optional[List[Dict[str, float]]] = None):
        """设置引力桩"""
        self.gravity_pillars = pillars
        self.gravity_weights = weights
        # 计算引力坐标（这里简化实现，实际应该调用 calculate_gravity_forces）
        # 暂时保持原坐标
        if weights is not None and self.original_coords_2d is not None:
            # TODO: 实现引力坐标计算
            self.gravity_coords_2d = self.original_coords_2d.copy()
    
    def set_axis_config(self, config: Dict):
        """设置轴配置（Scatter 模式）"""
        self.axis_config = config
        if config.get('active', False) and self.search_core is not None:
            # TODO: 实现 Scatter 坐标计算
            # 暂时保持原坐标
            if self.original_coords_2d is not None:
                self.scatter_coords_2d = self.original_coords_2d.copy()
    
    def clear_highlights(self):
        """清除高亮"""
        self.highlighted_indices.clear()
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.set_highlighted_indices(set())
    
    def apply_search_gravity(self, indices: List[int], scores: Optional[List[float]] = None):
        """
        应用搜索引力（向日葵螺旋布局）
        将相关节点按相似度分数螺旋排列在中心
        """
        if not indices or self.original_coords_2d is None:
            return
        
        # 设置高亮
        self.highlighted_indices = set(indices)
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.set_highlighted_indices(self.highlighted_indices)
        
        # 初始化 gravity_coords_2d
        if self.gravity_coords_2d is None:
            self.gravity_coords_2d = self.original_coords_2d.copy()
        
        # 准备分数（如果没有提供，使用默认值）
        if scores is None:
            scores = [1.0] * len(indices)
        elif len(scores) != len(indices):
            scores = [1.0] * len(indices)
        
        # 按分数降序排序
        sorted_items = sorted(
            zip(indices, scores), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 计算画布中心
        scene_rect = self.sceneRect()
        center_x = scene_rect.center().x()
        center_y = scene_rect.center().y()
        max_radius = min(scene_rect.width(), scene_rect.height()) * 0.4
        
        # 黄金角度（度转弧度）
        GOLDEN_ANGLE_DEG = 137.508
        GOLDEN_ANGLE_RAD = math.radians(GOLDEN_ANGLE_DEG)
        
        # 更新坐标：向日葵螺旋布局
        for idx, (item_idx, score) in enumerate(sorted_items):
            if item_idx >= len(self.gravity_coords_2d):
                continue
            
            # 计算角度和半径
            angle = idx * GOLDEN_ANGLE_RAD
            radius_factor = 1.0 - score  # 分数越高越靠近中心
            r = radius_factor * max_radius
            
            # 计算新位置
            x = center_x + r * math.cos(angle)
            y = center_y + r * math.sin(angle)
            
            self.gravity_coords_2d[item_idx] = np.array([x, y])
        
        # 非匹配项：淡出（保持原坐标，在渲染时降低透明度）
        # 实际淡出逻辑在 DetailScatterLayer 中处理
        
        # 切换到 gravity 模式
        self.set_view_mode('gravity')
    
    def get_items_in_rect(self, rect: QRectF) -> List[Dict]:
        """
        获取框选矩形区域内的所有文件元数据
        
        Args:
            rect: 场景坐标中的矩形区域
            
        Returns:
            元数据列表
        """
        if self.coords_2d is None or len(self.coords_2d) == 0:
            return []
        
        selected_metadata = []
        selected_indices = set()
        
        # 1. 获取框选区域内的所有点
        for i, (x, y) in enumerate(self.coords_2d):
            if rect.contains(QPointF(x, y)):
                if i < len(self.metadata):
                    selected_indices.add(i)
        
        # 2. 获取框选区域内的所有六边形（通过 hex_layer）
        if hasattr(self, 'hex_layer'):
            # 扩展矩形以确保包含边缘六边形
            margin = self.hex_size * 2
            expanded_rect = QRectF(rect)
            expanded_rect.adjust(-margin, -margin, margin, margin)
            
            # 计算需要检查的六边形范围
            min_q, min_r = self._pixel_to_hex(expanded_rect.left(), expanded_rect.top())
            max_q, max_r = self._pixel_to_hex(expanded_rect.right(), expanded_rect.bottom())
            
            # 扩展范围以确保覆盖
            min_q -= 1
            min_r -= 1
            max_q += 1
            max_r += 1
            
            # 检查每个六边形是否与框选区域相交
            for q in range(min_q, max_q + 1):
                for r in range(min_r, max_r + 1):
                    hex_key = (q, r)
                    if hex_key not in self.hex_layer.grid_data:
                        continue
                    
                    data = self.hex_layer.grid_data[hex_key]
                    center = self._hex_to_pixel(q, r)
                    
                    # 检查六边形中心是否在框选区域内
                    # 或者框选区域是否与六边形相交
                    hex_size = self.hex_size
                    hex_rect = QRectF(
                        center.x() - hex_size,
                        center.y() - hex_size,
                        hex_size * 2,
                        hex_size * 2
                    )
                    
                    if rect.intersects(hex_rect):
                        # 添加该六边形内的所有点
                        for idx in data.get('indices', []):
                            if idx < len(self.metadata):
                                selected_indices.add(idx)
        
        # 3. 收集所有选中项的元数据
        for idx in sorted(selected_indices):
            if idx < len(self.metadata):
                selected_metadata.append(self.metadata[idx])
        
        return selected_metadata
        
  