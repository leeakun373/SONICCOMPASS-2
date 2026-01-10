"""
可视化UCS布局工具 - 快速调整坐标配置

读取 ucs_coordinates.json 并绘制82个圆圈（每个大类一个），
在不运行庞大UMAP之前，快速调整JSON中的x, y, radius，像拼图一样设计世界地图。
"""

import sys
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.patches import Rectangle

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent.parent))


def plot_ucs_layout(config_path: str = "data_config/ucs_coordinates.json", output_path: str = None):
    """
    可视化UCS布局
    
    Args:
        config_path: UCS坐标配置文件路径
        output_path: 输出图片路径（可选，默认显示在窗口中）
    """
    print("=" * 60)
    print("📊 可视化UCS布局 (Plot UCS Layout)")
    print("=" * 60)
    
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("   请先运行: python tools/extract_category_centroids.py")
        sys.exit(1)
    
    # 加载配置
    print(f"\n📂 加载配置: {config_path}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"   已加载 {len(config)} 个类别")
    
    # 创建图形
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_aspect('equal')
    
    # 绘制每个类别
    categories = sorted(config.keys())
    colors = plt.cm.tab20(np.linspace(0, 1, len(categories)))
    
    for i, category in enumerate(categories):
        settings = config[category]
        x = settings['x']
        y = settings['y']
        radius = settings['radius']
        gap_buffer = settings.get('gap_buffer', radius * 0.15)
        
        # 绘制圆形（使用有效半径，减去gap_buffer）
        effective_radius = radius - gap_buffer
        circle = Circle((x, y), effective_radius, 
                       fill=True, alpha=0.3, 
                       edgecolor=colors[i % len(colors)], 
                       linewidth=1.5,
                       facecolor=colors[i % len(colors)])
        ax.add_patch(circle)
        
        # 绘制中心点
        ax.plot(x, y, 'o', color=colors[i % len(colors)], markersize=4)
        
        # 添加标签（只显示前30个字符，避免拥挤）
        label = category[:30] if len(category) <= 30 else category[:27] + "..."
        ax.text(x, y, label, fontsize=6, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
    
    # 检查重叠
    print("\n🔍 检查重叠...")
    overlaps = []
    for i, cat1 in enumerate(categories):
        config1 = config[cat1]
        for j, cat2 in enumerate(categories):
            if i >= j:
                continue
            
            config2 = config[cat2]
            dist = np.sqrt((config1['x'] - config2['x'])**2 + 
                          (config1['y'] - config2['y'])**2)
            overlap_radius = config1['radius'] + config2['radius'] + \
                           config1.get('gap_buffer', 0) + \
                           config2.get('gap_buffer', 0)
            
            if dist < overlap_radius:
                overlaps.append((cat1, cat2, dist, overlap_radius))
    
    if overlaps:
        print(f"   ⚠️  发现 {len(overlaps)} 组重叠:")
        for cat1, cat2, dist, overlap_radius in overlaps[:10]:  # 只显示前10个
            print(f"      {cat1} <-> {cat2}: 距离={dist:.2f}, 重叠半径={overlap_radius:.2f}")
        if len(overlaps) > 10:
            print(f"      ... 还有 {len(overlaps) - 10} 组重叠")
    else:
        print("   ✅ 未发现重叠")
    
    # 设置图形属性
    all_x = [config[cat]['x'] for cat in categories]
    all_y = [config[cat]['y'] for cat in categories]
    all_radii = [config[cat]['radius'] + config[cat].get('gap_buffer', 0) 
                 for cat in categories]
    
    x_min = min(all_x) - max(all_radii) - 10
    x_max = max(all_x) + max(all_radii) + 10
    y_min = min(all_y) - max(all_radii) - 10
    y_max = max(all_y) + max(all_radii) + 10
    
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel('X 坐标', fontsize=12)
    ax.set_ylabel('Y 坐标', fontsize=12)
    ax.set_title(f'UCS布局可视化 (共 {len(categories)} 个类别)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 添加说明
    info_text = f"类别数: {len(categories)}\n重叠数: {len(overlaps)}"
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存或显示
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n💾 图片已保存到: {output_path}")
    else:
        print("\n📺 显示图形窗口（关闭窗口以退出）...")
        plt.show()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='可视化UCS布局')
    parser.add_argument('--config', type=str, default='data_config/ucs_coordinates.json',
                       help='UCS坐标配置文件路径')
    parser.add_argument('--output', type=str, default=None,
                       help='输出图片路径（可选，默认显示在窗口中）')
    
    args = parser.parse_args()
    
    try:
        plot_ucs_layout(args.config, args.output)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
