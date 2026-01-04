"""
ui/visualizer/sonic_universe.py
可视化引擎 - 修复版 (Fix: Interaction, Layout, Rendering)
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPolygonF, QPainter, QRadialGradient, QFont, QStaticText, QPainterPath
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
    """六边形网格层 - 修复版 (Strict Grid & Clean UI)"""
    
    _color_mapper = None
    
    @classmethod
    def _get_color_mapper(cls):
        if cls._color_mapper is None and CategoryColorMapper is not None:
            try:
                cls._color_mapper = CategoryColorMapper()
            except Exception as e:
                print(f"[WARNING] 初始化 CategoryColorMapper 失败: {e}")
        return cls._color_mapper
    
    def __init__(self, size, ucs_manager=None):
        super().__init__()
        self.hex_size = size
        self.ucs_manager = ucs_manager
        self.grid_data = {}  
        self.metadata = []
        self.coords = None
        self.category_labels = []
        self.subcategory_labels = {}
        self.show_category_labels = False
        self.show_subcategory_labels = False
        self.current_zoom = 1.0
        self.current_lod = 0
        
    def set_data(self, grid_map, metadata, coords):
        import sys
        print(f"[DEBUG] HexGridLayer.set_data: start, grid_map={len(grid_map)}", flush=True)
        sys.stdout.flush()
        
        self.grid_data = grid_map
        self.metadata = metadata
        self.coords = coords
        self.prepareGeometryChange()
        
        # 【临时修复】注释掉标签生成，先让画面显示出来
        # print(f"[DEBUG] HexGridLayer.set_data: 开始生成标签，网格数量={len(grid_map)}", flush=True)
        # sys.stdout.flush()
        # self._generate_labels(metadata)
        # print(f"[DEBUG] HexGridLayer.set_data: 标签生成完成", flush=True)
        # sys.stdout.flush()
        
        # 临时：只初始化空标签，不生成
        self.category_labels = []
        self.subcategory_labels = {}
        
        print(f"[DEBUG] HexGridLayer.set_data: done", flush=True)
        sys.stdout.flush()
        
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
        # 重新实现以确保坐标一致性
        self.category_labels = []
        self.subcategory_labels = {}
        category_positions = {}
        mapper = self._get_color_mapper()
        
        total_hexes = len(self.grid_data)
        processed = 0
        
        for (q, r), indices in self.grid_data.items():
            if not indices: continue
            processed += 1
            if processed % 1000 == 0:
                print(f"[DEBUG] _generate_labels: 已处理 {processed}/{total_hexes} 个六边形...", flush=True)
            
            # Phase 3.5: 使用 Mode (最频繁) Category 和 SubCategory
            categories = []
            subcategories = []
            for idx in indices:
                if idx < len(metadata):
                    cat = metadata[idx].get('category', 'UNCATEGORIZED')
                    subcat = metadata[idx].get('subcategory', '')
                    if cat:
                        categories.append(cat)
                    if subcat:
                        subcategories.append(subcat)
            
            # 计算 Mode Category（用于 LOD 0 和 LOD 1）
            mode_category_str = None
            if categories:
                from collections import Counter
                category_counter = Counter(categories)
                mode_category_str = category_counter.most_common(1)[0][0]
            
            # LOD 0 聚类准备（Phase 3.5: 使用 Mode Category）
            if mode_category_str and mapper:
                # 确保是有效的 UCS Category（通过 mapper 验证）
                category = mapper.get_category_from_catid(mode_category_str) or "UNCATEGORIZED"
                if category not in category_positions: category_positions[category] = []
                category_positions[category].append((q, r))
            
            # LOD 1 标签（Phase 3.5: 使用 Mode SubCategory）
            center = self._hex_to_pixel(q, r)
            if subcategories:
                from collections import Counter
                subcat_counter = Counter(subcategories)
                mode_subcat = subcat_counter.most_common(1)[0][0]
                
                # 获取颜色（使用 Mode Category）
                color = mapper.get_color_for_catid(mode_category_str) if (mapper and mode_category_str) else QColor(200,200,200)
                self.subcategory_labels[(q, r)] = {'text': mode_subcat, 'pos': center, 'color': color}
            elif mode_category_str and mapper:
                # 如果没有 SubCategory，尝试从 UCS 映射获取
                subcat = mapper.get_subcategory_from_catid(mode_category_str) or ''
                if subcat:
                    color = mapper.get_color_for_catid(mode_category_str) if mapper else QColor(200,200,200)
                    self.subcategory_labels[(q, r)] = {'text': subcat, 'pos': center, 'color': color}

        # 生成大类标签
        print(f"[DEBUG] _generate_labels: 开始查找连通域，类别数量={len(category_positions)}", flush=True)
        if category_positions:
            components = self._find_connected_components(category_positions)
            print(f"[DEBUG] _generate_labels: 连通域查找完成，共 {len(components)} 个连通域", flush=True)
            # 过滤小岛屿
            large_components = [c for c in components if len(c[1]) >= 3] # 降低阈值到3
            print(f"[DEBUG] _generate_labels: 过滤后剩余 {len(large_components)} 个大岛屿", flush=True)
            
            for category, coords in large_components:
                # 计算几何中心
                avg_q = sum(c[0] for c in coords) / len(coords)
                avg_r = sum(c[1] for c in coords) / len(coords)
                center = self._hex_to_pixel(avg_q, avg_r)
                
                # 获取颜色
                color = QColor(255, 255, 255)
                if mapper:
                    # 尝试从该组中找个代表颜色
                    sample_hex = coords[0]
                    if sample_hex in self.grid_data:
                        idx = self.grid_data[sample_hex][0]
                        cid = metadata[idx].get('category', '')
                        c = mapper.get_color_for_catid(cid)
                        if c: color = c
                
                self.category_labels.append({
                    'text': category,
                    'pos': center,
                    'color': color,
                    'area': len(coords)
                })
    
    def _get_color_safe(self, key_str):
        """
        万能取色器：修复全红问题的终极方案
        【核心修复】如果查不到 UCS 颜色，就根据名字算出一个固定但独特的颜色
        这样 "Water" 和 "Fire" 即使查不到表，也会一个是蓝色一个是紫色，绝不会都是红色
        """
        # 0. 防御性编程
        if not key_str:
            return QColor('#333333')

        # 1. 尝试通过 Mapper 获取官方颜色
        mapper = self._get_color_mapper()
        if mapper:
            # 尝试直接 ID (e.g. "WPN")
            c = mapper.get_color_for_catid(key_str)
            if c: 
                return c
            
            # 尝试全名反查 (如果 mapper 支持)
            try:
                c = mapper.get_color_for_category(key_str)
                if c: 
                    return c
            except:
                pass

        # 2. 【核心修复】如果上面都失败了，绝对不要返回默认值！
        # 使用字符串的 Hash 值生成一个"伪随机但固定"的颜色
        # 这样能保证同一个分类永远是同一个颜色，且不同分类颜色不同
        
        # 使用简单的位运算模拟固定 hash（比 Python 内置 hash 更稳定）
        hash_val = 0
        for char in key_str:
            hash_val = (hash_val << 5) - hash_val + ord(char)
        
        # 映射到 HSV 空间生成高饱和度颜色
        # Hue: 0-359 (色相)
        h = abs(hash_val) % 360
        # Saturation: 150-250 (饱和度，保证鲜艳)
        s = 200 
        # Value: 200-255 (亮度，保证可见)
        v = 230
        
        return QColor.fromHsv(h, s, v)
    
    def boundingRect(self):
        # 给定一个超大范围，确保不被错误裁剪
        return QRectF(-100000, -100000, 200000, 200000)

    def paint(self, painter, option, widget):
        """修复的核心绘制逻辑"""
        clip_rect = option.exposedRect
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 严格网格参数（Phase 3.5：保留 2px 物理间隙）
        gap_ratio = 0.95  # 确保 2px 物理间隙，形成"地砖"分离感
        lod = self.current_lod
        
        mapper = self._get_color_mapper()
        
        # 1. 绘制六边形 (Strict Grid Mode)
        for (q, r), indices in self.grid_data.items():
            if not indices:
                continue
            
            # 【关键修复】不再使用数据重心，而是使用严格的网格中心
            center = self._hex_to_pixel(q, r)
            
            # 视锥剔除
            hex_size = self.hex_size
            if not clip_rect.intersects(QRectF(center.x() - hex_size, center.y() - hex_size, hex_size*2, hex_size*2)):
                continue
                
            # Phase 3.5: 颜色逻辑 - 使用 Mode (最频繁) Category
            color = QColor('#333333') # 默认深灰
            if len(indices) > 0:
                # 获取众数分类 (Mode Category)
                categories = []
                for idx in indices:
                    if idx < len(self.metadata):
                        cat = self.metadata[idx].get('category', 'UNCATEGORIZED')
                        if cat: 
                            categories.append(cat)
                
                if categories:
                    from collections import Counter
                    mode_category = Counter(categories).most_common(1)[0][0]
                    # 【关键修改】使用万能取色器
                    color = self._get_color_safe(mode_category)
            
            # 绘制单个六边形
            self._draw_single_hex(painter, center, len(indices), gap_ratio, color, lod)

        # 2. 绘制标签
        if lod == 0 and self.show_category_labels:
            self._draw_category_labels(painter, clip_rect)
        elif lod == 1 and self.show_subcategory_labels:
            self._draw_subcategory_labels(painter, clip_rect)
            
    def _draw_single_hex(self, painter, center, density, gap_ratio, color, lod):
        """
        Phase 3.5 修复：蜂窝地形风格
        - LOD 0/1: 独立六边形，填充 20% 透明度，描边 100% 透明度，1px 宽度
        - 保留 2px 物理间隙（gap_ratio = 0.95）
        """
        # 保留间隙：使用 0.95 缩放，确保 2px 物理间隙
        size = self.hex_size * gap_ratio
        
        hex_poly = QPolygonF()
        for i in range(6):
            angle = math.pi / 3 * i
            x = center.x() + size * math.cos(angle)
            y = center.y() + size * math.sin(angle)
            hex_poly.append(QPointF(x, y))
        
        fill_color = QColor(color)
        stroke_color = QColor(color)
        
        if lod == 0 or lod == 1:
            # LOD 0/1: 蜂窝地形风格（晶莹剔透的六边形）
            # 填充：UCS 颜色，透明度 20% (alpha ≈ 50)
            fill_color.setAlpha(50)  # 20% 透明度
            # 描边：UCS 颜色，透明度 100%，宽度 1px
            stroke_color.setAlpha(255)  # 100% 不透明
            painter.setPen(QPen(stroke_color, 1.0))
            painter.setBrush(QBrush(fill_color))
        else:
            # LOD 2: 极淡背景，细边框
            fill_color.setAlpha(20)  # 更淡
            stroke_color.setAlpha(60)
            painter.setPen(QPen(stroke_color, 0.5))
            painter.setBrush(QBrush(fill_color))
        
        painter.drawPolygon(hex_poly)

    def _hex_to_pixel(self, q, r):
        size = self.hex_size
        x = size * (3./2 * q)
        y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return QPointF(x, y)
    
    def _collision_culling(self, candidate_labels):
        """
        碰撞剔除：按面积从大到小排序，依次放置标签，如果重叠则丢弃
        
        Args:
            candidate_labels: 候选标签列表，每个元素包含 'text', 'pos', 'color', 'area'
            
        Returns:
            过滤后的标签列表
        """
        if not candidate_labels:
            return []
        
        # 按面积从大到小排序（已经在外部排序，这里确保）
        candidate_labels.sort(key=lambda x: x.get('area', 0), reverse=True)
        
        placed_labels = []
        placed_rects = []  # 存储已放置标签的 BoundingBox
        
        for label in candidate_labels:
            text = label['text']
            pos = label['pos']
            
            # 估算标签的 BoundingBox（基于文本长度和字号）
            # 使用 hex_size * 0.8 作为基础字号
            base_font_size = self.hex_size * 0.8
            zoom_factor = max(0.3, self.current_zoom)
            font_size = int(base_font_size / pow(zoom_factor, 0.5))
            
            # 估算文本宽度和高度（粗略估算：每个字符宽度约为 font_size * 0.6）
            text_width = len(text) * font_size * 0.6
            text_height = font_size * 1.2
            
            # 添加边距
            margin = 10
            label_rect = QRectF(
                pos.x() - text_width / 2 - margin,
                pos.y() - text_height / 2 - margin,
                text_width + margin * 2,
                text_height + margin * 2
            )
            
            # 检查是否与已放置的标签重叠
            overlaps = False
            for placed_rect in placed_rects:
                if label_rect.intersects(placed_rect):
                    overlaps = True
                    break
            
            # 如果不重叠，添加到已放置列表
            if not overlaps:
                placed_labels.append(label)
                placed_rects.append(label_rect)
        
        return placed_labels
    
    def _draw_category_labels(self, painter, clip_rect):
        """修复：移除黑色背景框，使用发光/阴影文字"""
        # 字体大小随缩放反向调整
        base_size = self.hex_size * 1.2
        zoom = max(0.1, self.current_zoom)
        font_size = int(base_size / math.sqrt(zoom))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        
        for label in self.category_labels:
            if not clip_rect.contains(label['pos']):
                continue
                
            text = label['text']
            pos = label['pos']
            
            # 计算位置
            fm = painter.fontMetrics()
            w = fm.horizontalAdvance(text)
            h = fm.height()
            x = pos.x() - w / 2
            y = pos.y() + h / 3  # 视觉垂直居中调整
            
            # 1. 绘制阴影/描边 (替代黑色方块)
            painter.setPen(QColor(0, 0, 0, 200))
            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (0,2)]:
                 painter.drawText(int(x+dx), int(y+dy), text)
            
            # 2. 绘制主体文字
            color = label.get('color', QColor(255, 255, 255))
            # 强制文字为亮白色或原色高亮版
            main_color = QColor(color)
            main_color.setAlpha(255)
            # 如果原色太暗，强制提亮
            if main_color.value() < 150:
                main_color = QColor(255, 255, 255)
                
            painter.setPen(main_color)
            painter.drawText(int(x), int(y), text)
    
    def _greedy_grid_culling(self, label_items):
        """
        Greedy Grid 避让算法：将屏幕划分为虚拟网格，按优先级放置标签
        
        Args:
            label_items: 标签项列表，每个元素包含 (q, r), label_data, 数据量
            
        Returns:
            过滤后的标签项列表
        """
        if not label_items:
            return []
        
        # 按数据量从大到小排序（优先级）
        label_items.sort(key=lambda x: x[2], reverse=True)
        
        # 虚拟网格大小（可根据屏幕分辨率调整）
        grid_width = 100
        grid_height = 50
        
        # 使用字典存储已占用的网格位置（O(1)查找）
        occupied_grids = set()
        
        filtered_items = []
        
        for (q, r), label_data, data_count in label_items:
            pos = label_data['pos']
            
            # 计算标签占据的网格位置
            grid_x = int(pos.x() / grid_width)
            grid_y = int(pos.y() / grid_height)
            
            # 估算标签占据的网格范围（考虑文本大小）
            font_size = int(self.hex_size * 0.6)
            text_width = len(label_data['text']) * font_size * 0.6
            text_height = font_size * 1.2
            margin = 5
            
            grid_span_x = max(1, int((text_width + margin * 2) / grid_width) + 1)
            grid_span_y = max(1, int((text_height + margin * 2) / grid_height) + 1)
            
            # 检查该标签占据的所有网格是否已被占用
            overlaps = False
            for dx in range(grid_span_x):
                for dy in range(grid_span_y):
                    grid_key = (grid_x + dx, grid_y + dy)
                    if grid_key in occupied_grids:
                        overlaps = True
                        break
                if overlaps:
                    break
            
            # 如果不重叠，添加到已占用网格并保留标签
            if not overlaps:
                for dx in range(grid_span_x):
                    for dy in range(grid_span_y):
                        occupied_grids.add((grid_x + dx, grid_y + dy))
                filtered_items.append(((q, r), label_data))
        
        return filtered_items
    
    def _draw_subcategory_labels(self, painter, clip_rect):
        """修复：SubCategory 标签使用正确的分类颜色（解决 LOD 1 全白问题）"""
        base_size = self.hex_size * 0.5
        font = QFont("Segoe UI", int(base_size), QFont.Weight.DemiBold)
        painter.setFont(font)
        
        for (q, r), label_data in self.subcategory_labels.items():
            pos = label_data['pos']
            if not clip_rect.contains(pos):
                continue
            
            text = label_data['text']
            # 获取该标签原本分配的颜色 (在 _generate_labels 里已经计算并存入 label_data['color'] 了)
            base_color = label_data.get('color', QColor(200, 200, 200))
            
            # 绘制文字阴影
            painter.setPen(QColor(0,0,0,180))
            painter.drawText(pos.x() - painter.fontMetrics().horizontalAdvance(text)/2 + 1, 
                           pos.y() + painter.fontMetrics().height()/3 + 1, text)
            
            # 【关键修改】使用分类颜色，并稍微提亮以保证在黑底上的可读性
            text_color = QColor(base_color)
            text_color = text_color.lighter(150) # 提亮 50%
            text_color.setAlpha(220)
            
            painter.setPen(text_color)
            painter.drawText(pos.x() - painter.fontMetrics().horizontalAdvance(text)/2, 
                           pos.y() + painter.fontMetrics().height()/3, text)
        
    def update_lod(self, zoom):
        self.current_zoom = zoom
        if zoom < 0.8: # 调整阈值
            self.current_lod = 0
            self.show_category_labels = True
            self.show_subcategory_labels = False
        elif zoom < 2.5:
            self.current_lod = 1
            self.show_category_labels = False
            self.show_subcategory_labels = True
        else:
            self.current_lod = 2
            self.show_category_labels = False
            self.show_subcategory_labels = True # LOD2 也保留子类标签作为上下文
        self.update()


class DetailScatterLayer(QGraphicsItem):
    """细节散点层 - Phase 3.5 修复版（动态对数密度采样）"""
    
    def __init__(self):
        super().__init__()
        self.points = None # (N, 2) numpy array
        self.colors = None # (N, 3) or (N, 4)
        self.visible = False
        self.hex_size = 50
        self.hex_grid_data = None  # 存储 hex_grid_data 用于动态采样
        
    def set_data(self, coords, metadata, hex_grid_data=None):
        """
        Phase 3.5: 存储原始数据，在 paint 时进行动态对数密度采样
        """
        self.points = coords
        self.metadata = metadata
        self.hex_grid_data = hex_grid_data  # 保存用于动态采样
        
        # 预计算颜色 (提升渲染性能)
        self.colors = []
        try:
            mapper = CategoryColorMapper()
        except:
            mapper = None
            
        # 批量生成颜色列表
        for meta in metadata:
            if mapper:
                c = mapper.get_color_for_catid(meta.get('category', ''))
                # 存为 RGBA tuple
                self.colors.append((c.red(), c.green(), c.blue(), 180))
            else:
                self.colors.append((200, 200, 200, 150))
    
    def _calculate_visible_points(self, total_count):
        """
        Phase 3.5: 动态对数密度采样
        公式: num_visible = clamp(int(log2(total_count) * factor), min_points, max_points)
        
        Args:
            total_count: 该六边形内的总数据量
            
        Returns:
            应该显示的点数量
        """
        if total_count <= 0:
            return 0
        
        # 参数设置
        factor = 2.0  # 对数缩放因子
        min_points = 3  # 最小显示点数
        max_points = 20  # 最大显示点数
        
        # 对数密度采样
        import math
        num_visible = int(math.log2(total_count + 1) * factor)
        
        # 限制范围
        num_visible = max(min_points, min(num_visible, max_points))
        
        # 如果数据量很小，显示所有点
        if total_count < min_points:
            num_visible = total_count
        
        return num_visible
                
    def set_hex_size(self, size):
        self.hex_size = size
        
    def boundingRect(self):
        return QRectF(-100000, -100000, 200000, 200000)
        
    def paint(self, painter, option, widget):
        """
        Phase 3.5: 动态对数密度采样渲染
        - 根据每个六边形的数据量动态决定显示点数
        - 300条数据显示明显多于5条数据
        """
        if not self.visible or self.points is None or self.hex_grid_data is None:
            return
            
        clip_rect = option.exposedRect
        x1, y1 = clip_rect.left(), clip_rect.top()
        x2, y2 = clip_rect.right(), clip_rect.bottom()
        
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        
        if len(self.points) == 0:
            return
        
        # Phase 3.5: 按六边形进行动态密度采样
        rendered_count = 0
        max_total_points = 5000  # 全局限制，防止卡死
        
        for (q, r), indices in self.hex_grid_data.items():
            if not indices:
                continue
            
            # 计算该六边形的中心（用于检查是否在视口内）
            def hex_to_pixel(q, r):
                size = self.hex_size
                x = size * (3./2 * q)
                y = size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
                return (x, y)
            
            center_x, center_y = hex_to_pixel(q, r)
            
            # 视锥剔除：检查六边形是否在视口内
            hex_radius = self.hex_size
            if (center_x + hex_radius < x1 or center_x - hex_radius > x2 or
                center_y + hex_radius < y1 or center_y - hex_radius > y2):
                continue
            
            # 动态对数密度采样
            total_count = len(indices)
            num_visible = self._calculate_visible_points(total_count)
            
            # 限制全局渲染数量
            if rendered_count + num_visible > max_total_points:
                num_visible = max_total_points - rendered_count
                if num_visible <= 0:
                    break
            
            # 选择要显示的点（确定性选取：前 N 个）
            selected_indices = indices[:num_visible]
            
            # 如果数据量 > 20，使用网格抖动分布（Poisson Disk Sampling 简化版）
            if total_count > 20:
                # 在六边形内部生成均匀分布的点
                for i, idx in enumerate(selected_indices):
                    if idx >= len(self.points):
                        continue
                    
                    # 网格抖动：在六边形内部生成伪随机位置
                    angle = (i * 137.508) % (2 * math.pi)  # 黄金角度
                    radius_factor = math.sqrt(i / num_visible) * 0.7  # 均匀分布
                    offset_x = center_x + hex_radius * radius_factor * math.cos(angle)
                    offset_y = center_y + hex_radius * radius_factor * math.sin(angle)
                    
                    # 确保在视口内
                    if x1 <= offset_x <= x2 and y1 <= offset_y <= y2:
                        r, g, b, a = self.colors[idx]
                        painter.setBrush(QColor(r, g, b, a))
                        painter.drawEllipse(QPointF(offset_x, offset_y), 2, 2)
                        rendered_count += 1
            else:
                # 数据量 <= 20：使用真实位置
                for idx in selected_indices:
                    if idx >= len(self.points):
                        continue
                    
                    x, y = self.points[idx]
                    
                    # 视口裁剪
                    if x1 <= x <= x2 and y1 <= y <= y2:
                        r, g, b, a = self.colors[idx]
                        painter.setBrush(QColor(r, g, b, a))
                        painter.drawEllipse(QPointF(x, y), 2, 2)
                        rendered_count += 1
            
            if rendered_count >= max_total_points:
                break

    def update_lod(self, zoom):
        # LOD 2 (Zoom >= 2.5) 才显示
        should_be_visible = (zoom >= 2.5)
        if self.visible != should_be_visible:
            self.visible = should_be_visible
            self.update()
            
    def set_highlighted_indices(self, indices):
        pass # 暂时简化


class SonicUniverse(QGraphicsScene):
    """Sonic Universe 可视化场景 - 修复版"""
    
    # 信号定义
    assets_selected = Signal(list)  # 传递metadata列表
    
    def __init__(self, metadata, embeddings, coords_2d=None, hex_size=50.0, search_core=None, ucs_manager=None, parent=None):
        super().__init__(parent)
        
        # 设置场景背景色（深色背景）
        self.setBackgroundBrush(QColor('#0B0C0E'))
        
        self.metadata = metadata
        self.embeddings = embeddings
        self.hex_size = float(hex_size)
        self.search_core = search_core
        self.ucs_manager = ucs_manager  # UCSManager 实例
        
        # 坐标处理
        self.coords_2d = coords_2d
        if self.coords_2d is None:
            print("[WARNING] coords_2d 为 None，使用随机坐标作为后备")
            # Fallback for safety
            self.coords_2d = np.random.rand(len(metadata), 2) * 10000
        else:
            print(f"[DEBUG] SonicUniverse 初始化: coords_2d shape={self.coords_2d.shape}, range=[{self.coords_2d.min(axis=0)}, {self.coords_2d.max(axis=0)}]")
        
        # 归一化坐标
        self._normalize_coordinates()
        if hasattr(self, 'norm_coords') and self.norm_coords is not None:
            print(f"[DEBUG] 归一化后: norm_coords shape={self.norm_coords.shape}, range=[{self.norm_coords.min(axis=0)}, {self.norm_coords.max(axis=0)}]")
        
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
        print("[DEBUG] 开始调用 _build_scene_data...")
        if hasattr(self, 'norm_coords') and self.norm_coords is not None:
            self._build_scene_data(self.norm_coords)
        else:
            print("[WARNING] norm_coords 尚未初始化，跳过 _build_scene_data")
        print(f"[DEBUG] _build_scene_data 完成，场景矩形: {self.sceneRect()}")
    
    def set_data(self, metadata, coords, embeddings=None):
        """设置数据 (Fix: Layout Order)"""
        # 1. 基础检查
        if coords is None or len(coords) == 0:
            print("[WARNING] SonicUniverse.set_data: coords is empty!")
            return

        self.metadata = metadata
        self.raw_coords = coords
        self.embeddings = embeddings
        
        # 2. 计算归一化坐标 (必须在构建场景前完成!)
        min_vals = np.min(coords, axis=0)
        max_vals = np.max(coords, axis=0)
        range_val = np.max(max_vals - min_vals)
        if range_val < 1e-5: 
            range_val = 1.0  # 防止除零
        
        scale = 3000.0 / range_val
        self.norm_coords = (coords - min_vals) * scale
        
        print(f"[DEBUG] set_data: 归一化完成, shape={self.norm_coords.shape}")

        # 3. 构建场景 (传入刚刚算好的 norm_coords)
        self._build_scene_data(self.norm_coords)
        
        # 4. 适配视图
        if hasattr(self, 'norm_coords') and self.norm_coords is not None and len(self.norm_coords) > 0:
            min_coords = self.norm_coords.min(axis=0)
            max_coords = self.norm_coords.max(axis=0)
            margin = 500.0
            rect = QRectF(
                float(min_coords[0]) - margin,
                float(min_coords[1]) - margin,
                float(max_coords[0] - min_coords[0]) + 2 * margin,
                float(max_coords[1] - min_coords[1]) + 2 * margin
            )
            self.setSceneRect(rect)
        
        # 强制重绘
        self.update()
    
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
    
    def _build_scene_data(self, norm_coords=None):
        """构建场景数据"""
        import sys
        print("[DEBUG] build: start", flush=True)
        sys.stdout.flush()
        
        # 如果没传参数，使用 self.norm_coords 作为 fallback
        if norm_coords is None:
            norm_coords = getattr(self, 'norm_coords', None)
            if norm_coords is None:
                print("[ERROR] _build_scene_data: norm_coords is None and self.norm_coords is also None!", flush=True)
                return
        
        # 强校验传入参数
        if len(norm_coords) == 0:
            print("[ERROR] _build_scene_data: Received empty coords!", flush=True)
            return

        print(f"[DEBUG] build: Building hex grid for {len(norm_coords)} items...", flush=True)
        sys.stdout.flush()
        
        # 清理旧数据
        print("[DEBUG] build: 清理旧数据...", flush=True)
        sys.stdout.flush()
        if hasattr(self, 'hex_layer'):
            self.hex_layer.grid_data.clear()
        if hasattr(self, 'scatter_layer'):
            self.scatter_layer.points = None
        
        # 构建网格索引
        print("[DEBUG] build: 构建网格索引...", flush=True)
        sys.stdout.flush()
        grid_map = {}
        for idx, (x, y) in enumerate(norm_coords):
            q, r = self._pixel_to_hex(x, y)
            if (q, r) not in grid_map:
                grid_map[(q, r)] = []
            grid_map[(q, r)].append(idx)
            # 每处理 5000 条输出一次进度
            if (idx + 1) % 5000 == 0:
                print(f"[DEBUG] build: 已处理 {idx + 1}/{len(norm_coords)} 个点...", flush=True)
                sys.stdout.flush()
        
        print(f"[DEBUG] build: grid_map={len(grid_map)}", flush=True)
        sys.stdout.flush()
            
        # 存储原始坐标（用于点击检测）
        self.current_display_coords = norm_coords
        self.norm_coords = norm_coords
        
        # 使用原始坐标构建空间索引（用于点击检测）
        print("[DEBUG] build: 构建 KDTree 空间索引...", flush=True)
        sys.stdout.flush()
        if SCIPY_AVAILABLE and len(norm_coords) > 0:
            self.tree = cKDTree(norm_coords)
            print("[DEBUG] build: KDTree 构建完成", flush=True)
            sys.stdout.flush()
            
        # 将数据传递给图层
        print("[DEBUG] build: before hex_layer.set_data", flush=True)
        sys.stdout.flush()
        if hasattr(self, 'hex_layer'):
            try:
                self.hex_layer.set_data(grid_map, self.metadata, norm_coords)
                print("[DEBUG] build: after hex_layer.set_data", flush=True)
                sys.stdout.flush()
            except Exception as e:
                print(f"[ERROR] build: hex_layer.set_data 失败: {e}", flush=True)
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
        
        print("[DEBUG] build: before scatter_layer.set_data", flush=True)
        sys.stdout.flush()
        if hasattr(self, 'scatter_layer'):
            try:
                self.scatter_layer.set_hex_size(self.hex_size)
                self.scatter_layer.set_data(norm_coords, self.metadata, grid_map)
                print("[DEBUG] build: after scatter_layer.set_data", flush=True)
                sys.stdout.flush()
            except Exception as e:
                print(f"[ERROR] build: scatter_layer.set_data 失败: {e}", flush=True)
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
        
        # 设置场景矩形（基于实际坐标）
        print("[DEBUG] build: 设置场景矩形...", flush=True)
        sys.stdout.flush()
        if len(norm_coords) > 0:
            min_coords = norm_coords.min(axis=0)
            max_coords = norm_coords.max(axis=0)
            margin = 500.0
            rect = QRectF(
                float(min_coords[0]) - margin,
                float(min_coords[1]) - margin,
                float(max_coords[0] - min_coords[0]) + 2 * margin,
                float(max_coords[1] - min_coords[1]) + 2 * margin
            )
            self.setSceneRect(rect)
            print(f"[DEBUG] build: 场景矩形设置完成: {rect}", flush=True)
            sys.stdout.flush()
        else:
            print("[WARNING] norm_coords 为空，使用默认场景矩形", flush=True)
            sys.stdout.flush()
            self.setSceneRect(0, 0, 3500, 3500)
        
        print("[DEBUG] build: 完成！", flush=True)
        sys.stdout.flush()
    
    def mousePressEvent(self, event):
        """处理鼠标点击，检测点击的六边形"""
        scene_pos = event.scenePos()
        q, r = self._pixel_to_hex(scene_pos.x(), scene_pos.y())
        
        # 检查是否点击了有数据的六边形
        if hasattr(self, 'hex_layer') and (q, r) in self.hex_layer.grid_data:
            indices = self.hex_layer.grid_data[(q, r)]
            metadata_list = [self.metadata[i] for i in indices if i < len(self.metadata)]
            
            # 发射信号
            if metadata_list:
                self.assets_selected.emit(metadata_list)
        
        super().mousePressEvent(event)
    
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
        # 传入 self.norm_coords 确保参数正确传递
        if hasattr(self, 'norm_coords') and self.norm_coords is not None:
            self._build_scene_data(self.norm_coords)
        else:
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
        
  