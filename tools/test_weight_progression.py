"""
权重渐进测试工具 - 用于测试不同category_weight值的效果

用法：
1. 修改 core/umap_config.py 中的 CATEGORY_WEIGHT 值
2. 运行: python tools/verify_subset.py --all --limit 1000
3. 分析生成的CSV文件，检查子类是否回到大类范围
"""

import sys
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import umap_config
import csv
import numpy as np

def analyze_clustering(csv_path: Path, category: str = "ANIMALS"):
    """
    分析指定类别内的聚类效果
    
    参数:
        csv_path: CSV文件路径
        category: 要分析的主类别（默认ANIMALS）
    
    返回:
        聚类统计信息
    """
    data = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['主类别'] == category:
                data.append({
                    'filename': row['文件名'],
                    'catid': row['CatID'],
                    'x': float(row['UMAP_X']),
                    'y': float(row['UMAP_Y'])
                })
    
    if len(data) == 0:
        return None
    
    # 计算坐标统计
    coords = np.array([[d['x'], d['y']] for d in data])
    center = coords.mean(axis=0)
    distances = np.sqrt(np.sum((coords - center)**2, axis=1))
    
    # 计算聚类紧密度（标准差）
    std_x = np.std(coords[:, 0])
    std_y = np.std(coords[:, 1])
    spread = np.sqrt(std_x**2 + std_y**2)
    
    # 找到离中心最远的点
    max_dist_idx = np.argmax(distances)
    max_dist_point = data[max_dist_idx]
    
    return {
        'count': len(data),
        'center': center,
        'mean_distance': np.mean(distances),
        'max_distance': np.max(distances),
        'std_distance': np.std(distances),
        'spread': spread,
        'furthest_point': max_dist_point,
        'catids': set([d['catid'] for d in data])
    }

def compare_with_reference(test_csv: Path, reference_csv: Path, category: str = "ANIMALS"):
    """比较测试结果与参考结果"""
    
    print("="*80)
    print(f"聚类效果对比 - {category}")
    print("="*80)
    print(f"参考文件: {reference_csv.name}")
    print(f"测试文件: {test_csv.name}")
    print()
    
    ref_stats = analyze_clustering(reference_csv, category)
    test_stats = analyze_clustering(test_csv, category)
    
    if ref_stats is None or test_stats is None:
        print(f"⚠️  未找到 {category} 类别的数据")
        return
    
    print("聚类统计对比：")
    print("-"*80)
    print(f"{'指标':<25} {'参考值':<20} {'测试值':<20} {'变化':<15}")
    print("-"*80)
    
    # 数据量
    print(f"{'数据量':<25} {ref_stats['count']:<20} {test_stats['count']:<20} {test_stats['count'] - ref_stats['count']:<15}")
    
    # 平均距离
    mean_dist_change = test_stats['mean_distance'] - ref_stats['mean_distance']
    print(f"{'平均距离（到中心）':<25} {ref_stats['mean_distance']:<20.4f} {test_stats['mean_distance']:<20.4f} {mean_dist_change:+.4f}")
    
    # 最大距离
    max_dist_change = test_stats['max_distance'] - ref_stats['max_distance']
    print(f"{'最大距离（到中心）':<25} {ref_stats['max_distance']:<20.4f} {test_stats['max_distance']:<20.4f} {max_dist_change:+.4f}")
    
    # 扩散度
    spread_change = test_stats['spread'] - ref_stats['spread']
    print(f"{'扩散度（标准差）':<25} {ref_stats['spread']:<20.4f} {test_stats['spread']:<20.4f} {spread_change:+.4f}")
    
    print()
    
    # 最远点信息
    print(f"参考文件中最远的点: {ref_stats['furthest_point']['filename'][:60]}")
    print(f"  位置: ({ref_stats['furthest_point']['x']:.2f}, {ref_stats['furthest_point']['y']:.2f})")
    print(f"  距离中心: {ref_stats['max_distance']:.4f}")
    print()
    
    print(f"测试文件中最远的点: {test_stats['furthest_point']['filename'][:60]}")
    print(f"  位置: ({test_stats['furthest_point']['x']:.2f}, {test_stats['furthest_point']['y']:.2f})")
    print(f"  距离中心: {test_stats['max_distance']:.4f}")
    print()
    
    # 结论
    print("="*80)
    print("结论")
    print("="*80)
    
    if test_stats['max_distance'] < ref_stats['max_distance'] * 0.9:
        print("✅ 聚类效果明显改善：最大距离显著减小")
    elif test_stats['max_distance'] < ref_stats['max_distance']:
        print("⚠️  聚类效果略有改善：最大距离略有减小")
    else:
        print("❌ 聚类效果未改善：最大距离没有减小（可能需要进一步提高权重）")
    
    if test_stats['spread'] < ref_stats['spread'] * 0.9:
        print("✅ 扩散度明显降低：聚类更加紧密")
    elif test_stats['spread'] < ref_stats['spread']:
        print("⚠️  扩散度略有降低")
    else:
        print("❌ 扩散度未降低")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python test_weight_progression.py <reference_csv> <test_csv> [category]")
        print("示例: python test_weight_progression.py verify_ALL_details_01101515.csv verify_ALL_details_01101900.csv ANIMALS")
        sys.exit(1)
    
    ref_file = Path(sys.argv[1])
    test_file = Path(sys.argv[2])
    category = sys.argv[3] if len(sys.argv) > 3 else "ANIMALS"
    
    if not ref_file.exists():
        print(f"❌ 参考文件不存在: {ref_file}")
        sys.exit(1)
    
    if not test_file.exists():
        print(f"❌ 测试文件不存在: {test_file}")
        sys.exit(1)
    
    # 显示当前配置
    print(f"当前配置:")
    print(f"  CATEGORY_WEIGHT = {umap_config.CATEGORY_WEIGHT}")
    print(f"  MIN_DIST = {umap_config.MIN_DIST}")
    print()
    
    compare_with_reference(test_file, ref_file, category)
