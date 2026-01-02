"""
Sonic Universe 可视化场景
基于绘制的批处理渲染架构 - 高性能版本
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsItem, QGraphicsTextItem,
    QStyleOptionGraphicsItem, QWidget
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF
from PySide6.QtGui import (
    QColor, QPen, QBrush, QPolygonF, QRadialGradient, 
    QPainter, QStaticText, QFont
)
import hashlib
import math
import sys
from pathlib import Path

# 导入 Category 颜色映射器
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from core.category_color_mapper import CategoryColorMapper
except ImportError:
    CategoryColorMapper = None

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False


class HexGridLayer(QGraphicsItem):
    """
    六边形网格层 - 单层绘制整个网格
    使用视口裁剪优化性能
    """
    
    # Category 颜色映射器（基于 UCS Category 大类）
    _color_mapper: Optional['CategoryColorMapper'] = None
    
    @classmethod
    def _get_color_mapper(cls) -> Optional['CategoryColorMapper']:
        """获取颜色映射器（单例模式）"""
        if cls._color_mapper is None and CategoryColorMapper is not None:
            try:
                cls._color_mapper = CategoryColorMapper()
            except Exception as e:
                print(f"[WARNING] 初始化 CategoryColorMapper 失败: {e}")
        return cls._color_mapper
    
    def __init__(
        self,
        metadata: List[Dict],
        coords_2d: np.ndarray,
        hex_size: float = 50.0,
        parent=None
    ):
        super().__init__(parent)
        self.metadata = metadata
        self.coords_2d = coords_2d
        self.hex_size = hex_size
        
        # 当前缩放级别（用于调整透明度）
        self.current_scale = 1.0
        
        # 计算网格数据（预计算）
        self.grid_data: Dict[Tuple[int, int], Dict] = {}
        self._build_grid_data()
        
        # 计算边界矩形
        self._compute_bounding_rect()
        
        # 设置标志
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemHasNoContents, False)
    
    def set_scale(self, scale: float):
        """设置当前缩放级别"""
        self.current_scale = scale
        self.update()
    
    def _build_grid_data(self):
        """构建网格数据（预计算）"""
        self.grid_data.clear()
        
        # 量化：将每个点吸附到最近的六边形中心
        for i, (x, y) in enumerate(self.coords_2d):
            q, r = self._pixel_to_hex(x, y)
            hex_key = (q, r)
            
            if hex_key not in self.grid_data:
                self.grid_data[hex_key] = {
                    'q': q,
                    'r': r,
                    'indices': [],
                    'categories': {},
                    'subcategories': {}
                }
            
            self.grid_data[hex_key]['indices'].append(i)
            
            # 统计分类（基于 Category 大类）和子分类
            cat_id = self.metadata[i].get('category', '')
            if cat_id:
                mapper = self._get_color_mapper()
                if mapper:
                    category_name = mapper.get_category_from_catid(cat_id)
                    if category_name:
                        self.grid_data[hex_key]['categories'][category_name] = \
                            self.grid_data[hex_key]['categories'].get(category_name, 0) + 1
                    subcategory_name = mapper.get_subcategory_from_catid(cat_id)
                    if subcategory_name:
                        self.grid_data[hex_key]['subcategories'][subcategory_name] = \
                            self.grid_data[hex_key]['subcategories'].get(subcategory_name, 0) + 1
                else:
                    # Fallback: 使用 CatID 前3字符
                    cat_key = cat_id[:3].upper() if len(cat_id) >= 3 else cat_id.upper()
                    self.grid_data[hex_key]['categories'][cat_key] = \
                        self.grid_data[hex_key]['categories'].get(cat_key, 0) + 1
        
        # 计算主导分类、子分类和密度
        for hex_key, data in self.grid_data.items():
            if data['categories']:
                data['dominant_cat'] = max(data['categories'], key=data['categories'].get)
            else:
                data['dominant_cat'] = None
            
            if data['subcategories']:
                data['dominant_subcat'] = max(data['subcategories'], key=data['subcategories'].get)
            else:
                data['dominant_subcat'] = None
            
            data['density'] = min(len(data['indices']) / 10.0, 1.0)
    
    def _pixel_to_hex(self, x: float, y: float) -> Tuple[int, int]:
        """将像素坐标转换为六边形轴向坐标"""
        q = (2.0/3 * x) / self.hex_size
        r = (-1.0/3 * x + math.sqrt(3)/3 * y) / self.hex_size
        return self._hex_round(q, r)
    
    def _hex_round(self, q: float, r: float) -> Tuple[int, int]:
        """将浮点轴向坐标四舍五入到最近的整数坐标"""
        s = -q - r
        q_r = round(q)
        r_r = round(r)
        s_r = round(s)
        
        q_diff = abs(q_r - q)
        r_diff = abs(r_r - r)
        s_diff = abs(s_r - s)
        
        if q_diff > r_diff and q_diff > s_diff:
            q_r = -r_r - s_r
        elif r_diff > s_diff:
            r_r = -q_r - s_r
        
        return (int(q_r), int(r_r))
    
    def _hex_to_pixel(self, q: int, r: int) -> QPointF:
        """将六边形轴向坐标转换为像素坐标"""
        size = self.hex_size * 0.866  # sqrt(3)/2
        x = size * (3.0/2 * q)
        y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return QPointF(x, y)
    
    def _create_hexagon_polygon(self, center: QPointF, visual_size: float) -> QPolygonF:
        """创建六边形多边形（带间距）"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            x = center.x() + visual_size * math.cos(angle)
            y = center.y() + visual_size * math.sin(angle)
            points.append(QPointF(x, y))
        return QPolygonF(points)
    
    def _get_color_for_category(self, cat_id: Optional[str]) -> QColor:
        """根据分类获取颜色（基于 Category 大类）"""
        if not cat_id:
            return QColor('#6B7280')
        
        # 使用 CategoryColorMapper 获取颜色
        mapper = self._get_color_mapper()
        if mapper:
            return mapper.get_color_for_catid(cat_id)
        
        # Fallback: 如果映射器不可用，使用旧的哈希方法
        hash_value = int(hashlib.md5(cat_id.encode()).hexdigest(), 16)
        # 使用 20 色色板
        fallback_palette = [
            QColor('#EF4444'), QColor('#06B6D4'), QColor('#10B981'),
            QColor('#F59E0B'), QColor('#8B5CF6'), QColor('#D946EF'),
            QColor('#00F5FF'), QColor('#FF00FF'), QColor('#00FF00'),
            QColor('#FFFF00'), QColor('#FF4500'), QColor('#00CED1'),
            QColor('#FF1493'), QColor('#7FFF00'), QColor('#FFD700'),
            QColor('#FF69B4'), QColor('#1E90FF'), QColor('#32CD32'),
            QColor('#FF6347'), QColor('#9370DB'),
        ]
        color_index = hash_value % len(fallback_palette)
        return fallback_palette[color_index]
    
    def _compute_bounding_rect(self):
        """计算边界矩形"""
        if len(self.coords_2d) == 0:
            self._bounding_rect = QRectF(0, 0, 10000, 10000)
            return
        
        min_x, min_y = self.coords_2d.min(axis=0)
        max_x, max_y = self.coords_2d.max(axis=0)
        
        # 扩展边界以包含所有六边形
        margin = self.hex_size * 2
        self._bounding_rect = QRectF(
            min_x - margin, min_y - margin,
            max_x - min_x + 2 * margin,
            max_y - min_y + 2 * margin
        )
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        return self._bounding_rect
    
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None
    ):
        """绘制六边形网格（三级 LOD 系统）"""
        # 获取视口矩形（在场景坐标中）
        view_rect = option.exposedRect
        
        # 扩展视口以包含边缘六边形
        margin = self.hex_size * 2
        view_rect.adjust(-margin, -margin, margin, margin)
        
        # 计算需要绘制的六边形范围
        min_q, min_r = self._pixel_to_hex(view_rect.left(), view_rect.top())
        max_q, max_r = self._pixel_to_hex(view_rect.right(), view_rect.bottom())
        
        # 扩展范围以确保覆盖
        min_q -= 1
        min_r -= 1
        max_q += 1
        max_r += 1
        
        # 视觉大小（内缩 92%，留下 8% 黑色缝隙）
        INSET_RATIO = 0.92
        visual_size = self.hex_size * INSET_RATIO
        
        # 三级 LOD 系统
        zoom = self.current_scale
        
        if zoom < 0.8:
            # LOD 0: The Continents - 只显示六边形，100% 不透明度，大标签显示主分类
            self._draw_hexagons_lod0(painter, view_rect, min_q, min_r, max_q, max_r, visual_size)
            self._draw_category_labels(painter, view_rect)
        elif zoom < 1.8:
            # LOD 1: The Regions - 只显示六边形，80% 不透明度，中等标签显示子分类
            self._draw_hexagons_lod1(painter, view_rect, min_q, min_r, max_q, max_r, visual_size)
            self._draw_subcategory_labels(painter, view_rect)
        else:
            # LOD 2: The Details - 六边形淡出轮廓（10% 不透明度）
            self._draw_hexagons_lod2(painter, view_rect, min_q, min_r, max_q, max_r, visual_size)
    
    def _draw_hexagons_lod0(self, painter, view_rect, min_q, min_r, max_q, max_r, visual_size):
        """LOD 0: 绘制六边形，100% 不透明度"""
        for q in range(min_q, max_q + 1):
            for r in range(min_r, max_r + 1):
                hex_key = (q, r)
                if hex_key not in self.grid_data:
                    continue
                
                data = self.grid_data[hex_key]
                center = self._hex_to_pixel(q, r)
                
                if not view_rect.contains(center):
                    continue
                
                self._draw_single_hexagon(painter, data, center, visual_size, alpha=255)
    
    def _draw_hexagons_lod1(self, painter, view_rect, min_q, min_r, max_q, max_r, visual_size):
        """LOD 1: 绘制六边形，80% 不透明度"""
        for q in range(min_q, max_q + 1):
            for r in range(min_r, max_r + 1):
                hex_key = (q, r)
                if hex_key not in self.grid_data:
                    continue
                
                data = self.grid_data[hex_key]
                center = self._hex_to_pixel(q, r)
                
                if not view_rect.contains(center):
                    continue
                
                # 80% 不透明度
                base_alpha = int(100 + (155 * data['density']))
                alpha = int(base_alpha * 0.8)
                self._draw_single_hexagon(painter, data, center, visual_size, alpha=alpha)
    
    def _draw_hexagons_lod2(self, painter, view_rect, min_q, min_r, max_q, max_r, visual_size):
        """LOD 2: 绘制六边形淡出轮廓，10% 不透明度"""
        for q in range(min_q, max_q + 1):
            for r in range(min_r, max_r + 1):
                hex_key = (q, r)
                if hex_key not in self.grid_data:
                    continue
                
                data = self.grid_data[hex_key]
                center = self._hex_to_pixel(q, r)
                
                if not view_rect.contains(center):
                    continue
                
                # 10% 不透明度（淡出轮廓）
                base_alpha = int(100 + (155 * data['density']))
                alpha = int(base_alpha * 0.1)
                self._draw_single_hexagon(painter, data, center, visual_size, alpha=alpha, outline_only=True)
    
    def _draw_single_hexagon(self, painter, data, center, visual_size, alpha, outline_only=False):
        """绘制单个六边形（视觉优化：硬朗边框、径向渐变）"""
        color = self._get_color_for_category(data['dominant_cat'])
        color.setAlpha(alpha)
        
        # 创建六边形多边形
        hex_poly = self._create_hexagon_polygon(center, visual_size)
        
        if not outline_only:
            # 绘制径向渐变填充
            gradient = QRadialGradient(center, visual_size)
            center_color = QColor(color)
            center_color.setAlpha(int(alpha * 0.4))  # 中心 40% 不透明度
            edge_color = QColor(color)
            edge_color.setAlpha(int(alpha * 0.1))  # 边缘 10% 不透明度
            gradient.setColorAt(0.0, center_color)
            gradient.setColorAt(1.0, edge_color)
            painter.setBrush(QBrush(gradient))
        else:
            # LOD 2: 只绘制轮廓，不填充
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # 绘制边框（硬朗风格：比填充色亮 50%，恒定 1.5px，硬角）
        border_color = QColor(color)
        border_color = border_color.lighter(150)  # 比填充色亮 50%
        border_color.setAlpha(min(255, alpha + 50))
        
        pen = QPen(border_color, 1.5)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)  # 硬角
        painter.setPen(pen)
        
        painter.drawPolygon(hex_poly)
    
    def _get_hex_neighbors(self, q: int, r: int) -> List[Tuple[int, int]]:
        """获取六边形的6个邻居"""
        return [
            (q + 1, r),      # 右
            (q + 1, r - 1),  # 右上
            (q, r - 1),      # 左上
            (q - 1, r),      # 左
            (q - 1, r + 1),  # 左下
            (q, r + 1),      # 右下
        ]
    
    def _compute_category_clusters(self, view_rect: QRectF) -> Dict[str, List[QPointF]]:
        """
        计算主分类聚类（连通域分析）
        返回: {category_name: [centroid1, centroid2, ...]}
        """
        # 1. 获取可见六边形
        visible_hexes = []
        min_q, min_r = self._pixel_to_hex(view_rect.left(), view_rect.top())
        max_q, max_r = self._pixel_to_hex(view_rect.right(), view_rect.bottom())
        
        for q in range(min_q - 1, max_q + 2):
            for r in range(min_r - 1, max_r + 2):
                hex_key = (q, r)
                if hex_key in self.grid_data:
                    data = self.grid_data[hex_key]
                    center = self._hex_to_pixel(q, r)
                    if view_rect.contains(center) and data.get('dominant_cat'):
                        visible_hexes.append((hex_key, data['dominant_cat']))
        
        # 2. 按主分类分组
        category_groups: Dict[str, List[Tuple[int, int]]] = {}
        for hex_key, category in visible_hexes:
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(hex_key)
        
        # 3. 对每个主分类执行 BFS 连通域分析
        clusters: Dict[str, List[QPointF]] = {}
        
        for category, hexes in category_groups.items():
            visited = set()
            for start_hex in hexes:
                if start_hex in visited:
                    continue
                
                # BFS 找到连通群组
                cluster = []
                queue = [start_hex]
                visited.add(start_hex)
                
                while queue:
                    current = queue.pop(0)
                    cluster.append(current)
                    
                    # 检查6个邻居
                    q, r = current
                    for neighbor in self._get_hex_neighbors(q, r):
                        if neighbor in hexes and neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                # 计算质心
                if cluster:
                    centroid_x = sum(self._hex_to_pixel(q, r).x() for q, r in cluster) / len(cluster)
                    centroid_y = sum(self._hex_to_pixel(q, r).y() for q, r in cluster) / len(cluster)
                    
                    if category not in clusters:
                        clusters[category] = []
                    clusters[category].append(QPointF(centroid_x, centroid_y))
        
        return clusters
    
    def _draw_category_labels(self, painter: QPainter, view_rect: QRectF):
        """绘制主分类标签（LOD 0：大标签）"""
        clusters = self._compute_category_clusters(view_rect)
        
        # 设置字体
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        painter.setFont(font)
        
        for category, centroids in clusters.items():
            for centroid in centroids:
                # 检查是否在视口内
                if not view_rect.contains(centroid):
                    continue
                
                # 使用 QStaticText 提高性能
                static_text = QStaticText(category.upper())
                static_text.setTextFormat(Qt.TextFormat.PlainText)
                
                # 计算文本位置（居中）
                text_rect = painter.fontMetrics().boundingRect(category.upper())
                text_x = centroid.x() - text_rect.width() / 2
                text_y = centroid.y() + text_rect.height() / 2
                
                # 绘制阴影（提高可读性）
                shadow_color = QColor(0, 0, 0, 180)
                painter.setPen(shadow_color)
                painter.drawStaticText(
                    int(text_x + 2), int(text_y + 2), static_text
                )
                
                # 绘制白色文字
                text_color = QColor(255, 255, 255, 255)
                painter.setPen(text_color)
                painter.drawStaticText(int(text_x), int(text_y), static_text)
    
    def _draw_subcategory_labels(self, painter: QPainter, view_rect: QRectF):
        """绘制子分类标签（LOD 1：中等标签，避免重叠）"""
        # 获取可见六边形
        min_q, min_r = self._pixel_to_hex(view_rect.left(), view_rect.top())
        max_q, max_r = self._pixel_to_hex(view_rect.right(), view_rect.bottom())
        
        # 设置字体
        font = QFont("Segoe UI", 12, QFont.Weight.Normal)
        painter.setFont(font)
        
        # 距离阈值（避免标签重叠）
        min_distance = 80.0
        placed_labels = []  # [(x, y), ...]
        
        for q in range(min_q, max_q + 1):
            for r in range(min_r, max_r + 1):
                hex_key = (q, r)
                if hex_key not in self.grid_data:
                    continue
                
                data = self.grid_data[hex_key]
                if not data.get('dominant_subcat'):
                    continue
                
                center = self._hex_to_pixel(q, r)
                if not view_rect.contains(center):
                    continue
                
                # 检查是否与已放置的标签太近
                too_close = False
                for placed_x, placed_y in placed_labels:
                    distance = math.sqrt(
                        (center.x() - placed_x) ** 2 + (center.y() - placed_y) ** 2
                    )
                    if distance < min_distance:
                        too_close = True
                        break
                
                if too_close:
                    continue
                
                # 绘制标签
                subcat = data['dominant_subcat']
                static_text = QStaticText(subcat.upper())
                static_text.setTextFormat(Qt.TextFormat.PlainText)
                
                text_rect = painter.fontMetrics().boundingRect(subcat.upper())
                text_x = center.x() - text_rect.width() / 2
                text_y = center.y() + text_rect.height() / 2
                
                # 绘制阴影
                shadow_color = QColor(0, 0, 0, 150)
                painter.setPen(shadow_color)
                painter.drawStaticText(
                    int(text_x + 1), int(text_y + 1), static_text
                )
                
                # 绘制文字
                text_color = QColor(255, 255, 255, 220)
                painter.setPen(text_color)
                painter.drawStaticText(int(text_x), int(text_y), static_text)
                
                # 记录已放置的标签位置
                placed_labels.append((center.x(), center.y()))


class DetailScatterLayer(QGraphicsItem):
    """
    细节散点层 - 单层绘制所有音频点
    基于 LOD 显示/隐藏，使用批量渲染优化性能
    """
    
    # Category 颜色映射器（基于 UCS Category 大类）
    _color_mapper: Optional['CategoryColorMapper'] = None
    
    @classmethod
    def _get_color_mapper(cls) -> Optional['CategoryColorMapper']:
        """获取颜色映射器（单例模式）"""
        if cls._color_mapper is None and CategoryColorMapper is not None:
            try:
                cls._color_mapper = CategoryColorMapper()
            except Exception as e:
                print(f"[WARNING] 初始化 CategoryColorMapper 失败: {e}")
        return cls._color_mapper
    
    def __init__(
        self,
        metadata: List[Dict],
        coords_2d: np.ndarray,
        hex_size: float = 50.0,
        parent=None
    ):
        super().__init__(parent)
        self.metadata = metadata
        self.coords_2d = coords_2d
        self.hex_size = hex_size
        
        # LOD 控制（三级 LOD 系统）
        self.lod_threshold = 1.8  # LOD 2 阈值（Zoom >= 1.8 时显示点）
        self.current_scale = 1.0
        
        # 高亮索引
        self.highlighted_indices: set = set()
        
        # 批量渲染缓存
        self.cached_points: QPolygonF = QPolygonF()
        self.cached_highlighted_points: QPolygonF = QPolygonF()
        self.cached_normal_points_by_color: Dict[int, QPolygonF] = {}  # 按颜色分组
        self.cached_view_rect: Optional[QRectF] = None
        self.cached_scale: float = 0.0
        self.cached_highlighted: set = set()
        
        # 预计算颜色映射（避免在 paint 中重复计算）
        self._color_cache: Dict[int, QColor] = {}
        self._build_color_cache()
        
        # 计算边界矩形
        self._compute_bounding_rect()
        
        # 设置标志
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemHasNoContents, False)
    
    def _build_color_cache(self):
        """预计算所有点的颜色"""
        self._color_cache.clear()
        for i, item in enumerate(self.metadata):
            cat_id = item.get('category', '')
            self._color_cache[i] = self._get_color_for_category(cat_id)
    
    def _get_color_for_category(self, cat_id: Optional[str]) -> QColor:
        """根据分类获取颜色（基于 Category 大类）"""
        if not cat_id:
            return QColor('#6B7280')
        
        # 使用 CategoryColorMapper 获取颜色
        mapper = self._get_color_mapper()
        if mapper:
            return mapper.get_color_for_catid(cat_id)
        
        # Fallback: 如果映射器不可用，使用旧的哈希方法
        hash_value = int(hashlib.md5(cat_id.encode()).hexdigest(), 16)
        # 使用 20 色色板
        fallback_palette = [
            QColor('#EF4444'), QColor('#06B6D4'), QColor('#10B981'),
            QColor('#F59E0B'), QColor('#8B5CF6'), QColor('#D946EF'),
            QColor('#00F5FF'), QColor('#FF00FF'), QColor('#00FF00'),
            QColor('#FFFF00'), QColor('#FF4500'), QColor('#00CED1'),
            QColor('#FF1493'), QColor('#7FFF00'), QColor('#FFD700'),
            QColor('#FF69B4'), QColor('#1E90FF'), QColor('#32CD32'),
            QColor('#FF6347'), QColor('#9370DB'),
        ]
        color_index = hash_value % len(fallback_palette)
        return fallback_palette[color_index]
    
    def _compute_bounding_rect(self):
        """计算边界矩形"""
        if len(self.coords_2d) == 0:
            self._bounding_rect = QRectF(0, 0, 10000, 10000)
            return
        
        min_x, min_y = self.coords_2d.min(axis=0)
        max_x, max_y = self.coords_2d.max(axis=0)
        
        margin = 10
        self._bounding_rect = QRectF(
            min_x - margin, min_y - margin,
            max_x - min_x + 2 * margin,
            max_y - min_y + 2 * margin
        )
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        return self._bounding_rect
    
    def set_scale(self, scale: float):
        """设置当前缩放级别"""
        if self.current_scale != scale:
            self.current_scale = scale
            # 清除缓存以强制重新计算
            self.cached_scale = 0.0
            self.update()
    
    def set_highlighted_indices(self, indices: set):
        """设置高亮索引"""
        if self.highlighted_indices != indices:
            self.highlighted_indices = indices
            # 清除缓存以强制重新计算
            self.cached_highlighted = set()
            self.update()
    
    def update_cache(self, view_rect: QRectF):
        """更新缓存：使用 numpy 进行视口裁剪和批量点计算"""
        # 检查缓存是否有效
        if (self.cached_view_rect is not None and
            self.cached_view_rect.contains(view_rect) and
            self.cached_scale == self.current_scale and
            self.cached_highlighted == self.highlighted_indices):
            return  # 缓存有效，无需更新
        
        # 更新缓存标记
        self.cached_view_rect = view_rect
        self.cached_scale = self.current_scale
        self.cached_highlighted = self.highlighted_indices.copy()
        
        # 扩展视口以确保边缘点也被包含
        margin = 10
        expanded_rect = QRectF(view_rect)
        expanded_rect.adjust(-margin, -margin, margin, margin)
        
        # 使用 numpy 布尔索引快速筛选视口内的点
        if len(self.coords_2d) == 0:
            self.cached_points = QPolygonF()
            self.cached_highlighted_points = QPolygonF()
            self.cached_normal_points = QPolygonF()
            return
        
        # 快速筛选：找出在视口内的点
        in_viewport = (
            (self.coords_2d[:, 0] >= expanded_rect.left()) &
            (self.coords_2d[:, 0] <= expanded_rect.right()) &
            (self.coords_2d[:, 1] >= expanded_rect.top()) &
            (self.coords_2d[:, 1] <= expanded_rect.bottom())
        )
        visible_indices = np.where(in_viewport)[0]
        
        if len(visible_indices) == 0:
            self.cached_points = QPolygonF()
            self.cached_highlighted_points = QPolygonF()
            self.cached_normal_points = QPolygonF()
            return
        
        # 分离高亮点和普通点
        highlighted_mask = np.isin(visible_indices, list(self.highlighted_indices))
        highlighted_indices = visible_indices[highlighted_mask]
        normal_indices = visible_indices[~highlighted_mask]
        
        # 批量创建高亮点 QPointF 列表
        if len(highlighted_indices) > 0:
            highlighted_coords = self.coords_2d[highlighted_indices]
            self.cached_highlighted_points = QPolygonF([
                QPointF(x, y) for x, y in highlighted_coords
            ])
        else:
            self.cached_highlighted_points = QPolygonF()
        
        # 按颜色分组普通点（用于批量绘制不同颜色的点）
        self.cached_normal_points_by_color.clear()
        if len(normal_indices) > 0:
            normal_coords = self.coords_2d[normal_indices]
            # 按颜色分组（使用颜色 RGB 值作为键）
            for idx, (x, y) in zip(normal_indices, normal_coords):
                color = self._color_cache.get(idx, QColor('#6B7280'))
                color_key = color.rgb()
                if color_key not in self.cached_normal_points_by_color:
                    self.cached_normal_points_by_color[color_key] = QPolygonF()
                self.cached_normal_points_by_color[color_key].append(QPointF(x, y))
        
        # 合并所有点（用于某些绘制操作）
        self.cached_points = QPolygonF(self.cached_highlighted_points)
        for color_points in self.cached_normal_points_by_color.values():
            for point in color_points:
                self.cached_points.append(point)
    
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None
    ):
        """绘制散点（LOD 2：Zoom >= 1.8 时显示）"""
        # LOD 2 控制：只有在 zoom >= 1.8 时才显示点
        if self.current_scale < self.lod_threshold:
            return  # LOD 0/1：不绘制点
        
        # 获取视口矩形
        view_rect = option.exposedRect
        
        # 更新缓存（如果需要）
        self.update_cache(view_rect)
        
        # 如果缓存为空，直接返回
        if len(self.cached_points) == 0:
            return
        
        # 计算点的透明度（基于缩放级别，淡入效果）
        fade_start = self.lod_threshold
        fade_end = self.lod_threshold * 2
        if self.current_scale < fade_end:
            fade_alpha = int(255 * (self.current_scale - fade_start) / (fade_end - fade_start))
            fade_alpha = max(0, min(255, fade_alpha))
        else:
            fade_alpha = 255
        
        # 批量绘制：使用 drawPoints 按颜色分组（无循环）
        # 虽然需要多次 drawPoints 调用，但每组都是批量绘制，性能仍然很好
        
        # 计算普通点的透明度（如果有高亮，则淡出）
        normal_alpha = fade_alpha
        if self.highlighted_indices:
            # Gravity 模式：非匹配项淡出到 10% 透明度
            normal_alpha = int(fade_alpha * 0.1)  # 非匹配项几乎透明
        
        # 按颜色分组批量绘制普通点
        for color_key, points in self.cached_normal_points_by_color.items():
            if len(points) == 0:
                continue
            
            # 获取颜色并设置透明度
            color = QColor()
            color.setRgb(color_key)
            color.setAlpha(normal_alpha)
            
            # 批量绘制该颜色的所有点
            painter.setPen(QPen(color, 2.0))
            painter.drawPoints(points)
        
        # 绘制高亮点（白色，更大，完全不透明）
        if len(self.cached_highlighted_points) > 0:
            painter.setPen(QPen(QColor(255, 255, 255, 255), 3.0))
            painter.drawPoints(self.cached_highlighted_points)
        
        # 注意：光晕效果需要额外的绘制调用，为了性能暂时省略
        # 如果需要光晕，可以在 paint 方法中添加额外的批量绘制调用
        # 但会增加绘制时间，建议在性能测试后再决定是否添加


class SonicUniverse(QGraphicsScene):
    """
    Sonic Universe 可视化场景
    使用基于绘制的批处理渲染架构
    """
    
    def __init__(
        self,
        metadata: List[Dict],
        embeddings: np.ndarray,
        coords_2d: Optional[np.ndarray] = None,
        hex_size: float = 50.0,
        search_core: Optional[object] = None,
        parent=None
    ):
        super().__init__(parent)
        self.metadata = metadata
        self.embeddings = embeddings
        self.hex_size = hex_size
        self.search_core = search_core
        
        # 2D 投影坐标
        if coords_2d is not None:
            self.coords_2d = coords_2d.copy()
        else:
            self.coords_2d: Optional[np.ndarray] = None
        
        # 归一化坐标到大型画布范围（支持深度缩放）
        if self.coords_2d is not None:
            self._normalize_coordinates()
        
        # 保存原始坐标
        self.original_coords_2d: Optional[np.ndarray] = None
        if self.coords_2d is not None:
            self.original_coords_2d = self.coords_2d.copy()
        
        # 视图模式
        self.view_mode = 'explorer'  # 'explorer', 'gravity', 或 'scatter'
        
        # Scatter 模式相关
        self.axis_config: Optional[Dict] = None
        self.scatter_coords_2d: Optional[np.ndarray] = None
        
        # 引力视图相关
        self.gravity_pillars: List[str] = []
        self.gravity_weights: Optional[List[Dict[str, float]]] = None
        self.gravity_coords_2d: Optional[np.ndarray] = None
        self.pillar_items: List[QGraphicsItem] = []
        
        # 当前缩放级别
        self.current_zoom = 1.0
        
        # 高亮索引
        self.highlighted_indices: set = set()
        
        # 初始化
        if self.coords_2d is None:
            self._compute_2d_projection()
        if self.coords_2d is not None:
            self.original_coords_2d = self.coords_2d.copy()
        
        self._setup_scene()
        self._build_layers()
    
    def _normalize_coordinates(self):
        """归一化坐标到大型画布范围（10000x10000）"""
        if self.coords_2d is None or len(self.coords_2d) == 0:
            return
        
        # 获取当前坐标范围
        min_x, min_y = self.coords_2d.min(axis=0)
        max_x, max_y = self.coords_2d.max(axis=0)
        
        # 计算当前范围
        range_x = max_x - min_x
        range_y = max_y - min_y
        
        # 避免除零
        if range_x == 0:
            range_x = 1.0
        if range_y == 0:
            range_y = 1.0
        
        # 目标范围：10000x10000，保留边距
        target_size = 10000.0
        margin = 100.0  # 边距
        target_range = target_size - 2 * margin
        
        # 归一化：保持宽高比，缩放到目标范围
        scale_x = target_range / range_x
        scale_y = target_range / range_y
        scale = min(scale_x, scale_y)  # 使用较小的缩放比例以保持宽高比
        
        # 应用缩放和平移
        self.coords_2d = (self.coords_2d - np.array([min_x, min_y])) * scale + margin
    
    def _compute_2d_projection(self):
        """计算 2D 投影（如果坐标不存在）"""
        if not UMAP_AVAILABLE:
            raise RuntimeError("UMAP is required for 2D projection")
        
        # 使用 UMAP 进行降维
        reducer = umap.UMAP(n_components=2, random_state=42)
        self.coords_2d = reducer.fit_transform(self.embeddings)
        self._normalize_coordinates()
    
    def _setup_scene(self):
        """设置场景"""
        # 设置场景范围
        if self.coords_2d is not None and len(self.coords_2d) > 0:
            min_x, min_y = self.coords_2d.min(axis=0)
            max_x, max_y = self.coords_2d.max(axis=0)
            margin = 500.0
            self.setSceneRect(
                min_x - margin, min_y - margin,
                max_x - min_x + 2 * margin,
                max_y - min_y + 2 * margin
            )
        else:
            self.setSceneRect(0, 0, 10000, 10000)
    
    def _build_layers(self):
        """构建渲染层"""
        if self.coords_2d is None or len(self.coords_2d) == 0:
            return
        
        # 创建六边形网格层（背景层，Z值=0）
        self.hex_layer = HexGridLayer(
            self.metadata,
            self.coords_2d,
            self.hex_size,
            parent=None
        )
        self.hex_layer.setZValue(0)
        self.addItem(self.hex_layer)
        
        # 创建散点层（前景层，Z值=1）
        self.scatter_layer = DetailScatterLayer(
            self.metadata,
            self.coords_2d,
            self.hex_size,
            parent=None
        )
        self.scatter_layer.setZValue(1)
        self.addItem(self.scatter_layer)
    
    def update_lod(self, zoom_level: float):
        """更新 LOD（Level of Detail）- 使用真实的 transform scale"""
        self.current_zoom = zoom_level
        
        # 更新散点层的缩放级别
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.set_scale(zoom_level)
        
        # 更新六边形层的缩放级别（用于 LOD 判断和透明度调整）
        if hasattr(self, 'hex_layer'):
            self.hex_layer.set_scale(zoom_level)
    
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
        
  