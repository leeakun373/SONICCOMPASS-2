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

# 导入 Category 颜色映射器
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from core.category_color_mapper import CategoryColorMapper
except ImportError:
    CategoryColorMapper = None

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
    
    def __init__(self, size):
        super().__init__()
        self.hex_size = size
        self.grid_data = {}  # (q, r) -> [indices]
        self.metadata = []
        self.coords = None
        self.labels = []
        self.show_labels = True
        self.current_zoom = 1.0
        
    def set_data(self, grid_map, metadata, coords):
        self.grid_data = grid_map
        self.metadata = metadata
        self.coords = coords
        self.prepareGeometryChange()
        # 预计算标签
        self._generate_labels(metadata)
        
    def _generate_labels(self, metadata):
        """生成标签（简单的去重）"""
        self.labels = []
        category_positions = {}  # category -> [(q, r), ...]
        
        for (q, r), indices in self.grid_data.items():
            if not indices:
                continue
            # 获取第一个点的分类
            first_idx = indices[0]
            if first_idx < len(metadata):
                cat_id = metadata[first_idx].get('category', '')
                mapper = self._get_color_mapper()
                if mapper:
                    category = mapper.get_category_from_catid(cat_id)
                    if category:
                        if category not in category_positions:
                            category_positions[category] = []
                        category_positions[category].append((q, r))
        
        # 为每个分类计算质心位置
        for category, positions in category_positions.items():
            if len(positions) > 3:  # 只显示较大的聚类
                centers = [self._hex_to_pixel(q, r) for q, r in positions]
                centroid_x = sum(c.x() for c in centers) / len(centers)
                centroid_y = sum(c.y() for c in centers) / len(centers)
                self.labels.append({
                    'text': category.upper(),
                    'pos': QPointF(centroid_x, centroid_y)
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
        
        for (q, r), indices in self.grid_data.items():
            center = self._hex_to_pixel(q, r)
            
            # 粗略裁剪检查
            if not clip_rect.contains(center):
                continue
                
            # 获取颜色（基于第一个点的分类）
            color = QColor(100, 200, 255, 150)  # 默认颜色
            if indices and len(indices) > 0 and self.metadata:
                idx = indices[0]
                if idx < len(self.metadata):
                    cat_id = self.metadata[idx].get('category', '')
                    mapper = self._get_color_mapper()
                    if mapper:
                        color = mapper.get_color_for_catid(cat_id)
                        color.setAlpha(150)
                
            # 绘制六边形
            self._draw_single_hex(painter, center, len(indices), gap_ratio, color)

        # 绘制标签 (LOD 0)
        if self.show_labels:
            self._draw_labels(painter, clip_rect)
            
    def _draw_single_hex(self, painter, center, density, gap_ratio, color):
        size = self.hex_size * gap_ratio
        # 创建六边形路径
        hex_poly = QPolygonF()
        for i in range(6):
            angle = math.pi / 3 * i
            x = center.x() + size * math.cos(angle)
            y = center.y() + size * math.sin(angle)
            hex_poly.append(QPointF(x, y))
        
        # 重点：颜色要透，边框要亮
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(QBrush(QColor(20, 30, 40, min(100 + density*10, 240))))
        painter.drawPolygon(hex_poly)

    def _hex_to_pixel(self, q, r):
        size = self.hex_size
        x = size * (3./2 * q)
        y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return QPointF(x, y)
    
    def _draw_labels(self, painter, clip_rect):
        """绘制标签"""
        font_size = int(self.hex_size * 2.0)  # 巨大的水印
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        for label in self.labels:
            if not clip_rect.contains(label['pos']):
                continue
            
            static_text = QStaticText(label['text'])
            text_rect = painter.fontMetrics().boundingRect(label['text'])
            text_x = label['pos'].x() - text_rect.width() / 2
            text_y = label['pos'].y() + text_rect.height() / 2
            
            # 绘制阴影
            shadow_color = QColor(0, 0, 0, 180)
            painter.setPen(shadow_color)
            painter.drawStaticText(int(text_x + 2), int(text_y + 2), static_text)
            
            # 绘制白色文字
            text_color = QColor(255, 255, 255, 255)
            painter.setPen(text_color)
            painter.drawStaticText(int(text_x), int(text_y), static_text)
        
    def update_lod(self, zoom):
        # LOD 逻辑
        if zoom < 0.2: 
            self.show_labels = True
            self.setOpacity(1.0)
        elif zoom > 2.0:
            self.show_labels = False
            self.setOpacity(0.2)  # 放大后变淡
        self.current_zoom = zoom
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
        # 只有放大了才显示点
        self.visible = (zoom > 0.8)
        self.update()


class SonicUniverse(QGraphicsScene):
    """Sonic Universe 可视化场景 - 修复版"""
    
    def __init__(self, metadata, embeddings, coords_2d=None, hex_size=50.0, search_core=None, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.embeddings = embeddings
        self.hex_size = float(hex_size)
        self.search_core = search_core
        
        # 坐标处理
        self.coords_2d = coords_2d
        if self.coords_2d is None:
            # Fallback for safety
            self.coords_2d = np.random.rand(len(metadata), 2) * 10000
        
        # 构建空间索引 (用于极速点击检测)
        self.tree = None
        if SCIPY_AVAILABLE and len(self.coords_2d) > 0:
            # 先归一化坐标，然后构建树
            self._normalize_coordinates()
            self.tree = cKDTree(self.norm_coords)
        else:
            self._normalize_coordinates()

        # 核心数据结构
        self.hex_layer = HexGridLayer(self.hex_size)
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
        """归一化坐标到大型画布范围（10000x10000）"""
        if self.coords_2d is None or len(self.coords_2d) == 0:
            return
        
        # 1. 坐标归一化到大场景 (10000x10000)
        min_v = np.min(self.coords_2d, axis=0)
        max_v = np.max(self.coords_2d, axis=0)
        scale = 10000.0 / (np.max(max_v - min_v) + 1e-5)
        self.norm_coords = (self.coords_2d - min_v) * scale
    
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
            
        # 3. 传递数据给图层
        self.hex_layer.set_data(grid_map, self.metadata, self.norm_coords)
        self.scatter_layer.set_data(self.norm_coords, self.metadata)
        
        # 4. 自动调整相机范围
        rect = self.itemsBoundingRect()
        rect.adjust(-500, -500, 500, 500)  # Padding
        self.setSceneRect(rect)
    
    def _pixel_to_hex(self, x, y):
        size = self.hex_size
        q = (2./3 * x) / size
        r = (-1./3 * x + math.sqrt(3)/3 * y) / size
        return self._hex_round(q, r)

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
        """找到鼠标点击位置最近的数据"""
        if self.tree is None or not hasattr(self, 'norm_coords'):
            return None
        
        # 查询最近邻，距离阈值设为 20px (太远点不到)
        try:
            dist, idx = self.tree.query([scene_pos.x(), scene_pos.y()], distance_upper_bound=20)
            
            if dist == float('inf') or idx >= len(self.metadata):
                return None
            
            return {
                'index': int(idx),
                'metadata': self.metadata[int(idx)],
                'pos': self.norm_coords[int(idx)]
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
        # 清除旧层
        if hasattr(self, 'hex_layer'):
            self.removeItem(self.hex_layer)
        if hasattr(self, 'scatter_layer'):
            self.removeItem(self.scatter_layer)
        
        # 重建层
        self._build_layers()
    
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
            min_q, min_r = self.hex_layer._pixel_to_hex(expanded_rect.left(), expanded_rect.top())
            max_q, max_r = self.hex_layer._pixel_to_hex(expanded_rect.right(), expanded_rect.bottom())
            
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
                    center = self.hex_layer._hex_to_pixel(q, r)
                    
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
        
  