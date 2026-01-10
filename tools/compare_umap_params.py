"""
比较两个UMAP参数配置下生成的CSV文件，分析参数的实际影响
"""

import csv
import sys
from pathlib import Path
import numpy as np

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def compare_csv_files(file1_path: Path, file2_path: Path):
    """比较两个CSV文件，分析坐标差异"""
    
    print("="*80)
    print("UMAP参数影响分析")
    print("="*80)
    print(f"文件1: {file1_path.name} (target_weight=0.5)")
    print(f"文件2: {file2_path.name} (target_weight=1.0)")
    print()
    
    # 读取两个文件
    data1 = {}
    data2 = {}
    
    with open(file1_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['文件名']
            data1[filename] = {
                'x': float(row['UMAP_X']),
                'y': float(row['UMAP_Y']),
                'cat': row['主类别']
            }
    
    with open(file2_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['文件名']
            data2[filename] = {
                'x': float(row['UMAP_X']),
                'y': float(row['UMAP_Y']),
                'cat': row['主类别']
            }
    
    # 检查文件数量
    print(f"文件1数据量: {len(data1)}")
    print(f"文件2数据量: {len(data2)}")
    
    if len(data1) != len(data2):
        print(f"⚠️  警告：两个文件的数据量不同！")
        print()
    
    # 找出共同的文件
    common_files = set(data1.keys()) & set(data2.keys())
    print(f"共同文件数: {len(common_files)}")
    print()
    
    # 计算坐标差异
    differences = []
    exact_matches = 0
    
    for filename in common_files:
        x1, y1 = data1[filename]['x'], data1[filename]['y']
        x2, y2 = data2[filename]['x'], data2[filename]['y']
        
        # 欧氏距离
        dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        if dist < 1e-6:  # 浮点数精度误差
            exact_matches += 1
        else:
            differences.append({
                'filename': filename,
                'dist': dist,
                'x_diff': x2 - x1,
                'y_diff': y2 - y1,
                'x1': x1,
                'y1': y1,
                'x2': x2,
                'y2': y2,
                'category': data1[filename]['cat']
            })
    
    print("="*80)
    print("坐标差异分析")
    print("="*80)
    print(f"完全相同的点: {exact_matches} ({exact_matches/len(common_files)*100:.2f}%)")
    print(f"有差异的点: {len(differences)} ({len(differences)/len(common_files)*100:.2f}%)")
    print()
    
    if len(differences) == 0:
        print("✅ 结论：两个文件的所有坐标完全相同！")
        print("   target_weight参数（从0.5改为1.0）没有产生任何影响。")
        print()
        print("可能原因：")
        print("1. 向量注入权重(category_weight=50.0)太强，已经主导了聚类")
        print("2. UMAP的随机种子(random_state=42)确保了结果的可重复性")
        print("3. 在已经应用超级锚点策略的情况下，target_weight的影响被完全掩盖")
        return
    
    # 统计差异分布
    distances = [d['dist'] for d in differences]
    
    print("差异统计：")
    print(f"  最小差异: {min(distances):.6f}")
    print(f"  最大差异: {max(distances):.6f}")
    print(f"  平均差异: {np.mean(distances):.6f}")
    print(f"  中位数差异: {np.median(distances):.6f}")
    print(f"  标准差: {np.std(distances):.6f}")
    print()
    
    # 显示差异最大的前10个点
    differences.sort(key=lambda x: x['dist'], reverse=True)
    
    print("差异最大的前10个点：")
    print("-"*80)
    print(f"{'序号':<5} {'文件名':<45} {'类别':<15} {'差异距离':<12} {'X变化':<12} {'Y变化':<12}")
    print("-"*80)
    for i, d in enumerate(differences[:10], 1):
        filename_short = d['filename'][:43] if len(d['filename']) > 43 else d['filename']
        print(f"{i:<5} {filename_short:<45} {d['category']:<15} {d['dist']:<12.6f} {d['x_diff']:<12.6f} {d['y_diff']:<12.6f}")
    print()
    
    # 按类别分析差异
    category_diffs = {}
    for d in differences:
        cat = d['category']
        if cat not in category_diffs:
            category_diffs[cat] = []
        category_diffs[cat].append(d['dist'])
    
    print("按类别分析平均差异：")
    print("-"*80)
    print(f"{'类别':<20} {'差异点数':<12} {'平均差异':<15} {'最大差异':<15}")
    print("-"*80)
    for cat in sorted(category_diffs.keys(), key=lambda x: np.mean(category_diffs[x]), reverse=True):
        diffs = category_diffs[cat]
        print(f"{cat:<20} {len(diffs):<12} {np.mean(diffs):<15.6f} {max(diffs):<15.6f}")
    print()
    
    # 结论
    avg_diff = np.mean(distances)
    max_diff = max(distances)
    
    print("="*80)
    print("结论")
    print("="*80)
    
    if avg_diff < 0.01:
        print("✅ target_weight参数的影响极小（平均差异 < 0.01）")
        print("   这可能是因为：")
        print("   1. 向量注入权重(category_weight=50.0)已经非常强，主导了聚类")
        print("   2. 在超级锚点策略下，target_weight只是辅助参数，影响被掩盖")
        print("   3. 建议：可以保持target_weight=0.5，或者考虑移除这个参数")
    elif avg_diff < 0.1:
        print("⚠️  target_weight参数有一定影响，但影响较小（平均差异 < 0.1）")
    else:
        print("📊 target_weight参数有明显影响（平均差异 >= 0.1）")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python compare_umap_params.py <file1.csv> <file2.csv>")
        print("示例: python compare_umap_params.py verify_ALL_details_01101515.csv verify_ALL_details_01101518.csv")
        sys.exit(1)
    
    file1 = Path(sys.argv[1])
    file2 = Path(sys.argv[2])
    
    if not file1.exists():
        print(f"❌ 文件不存在: {file1}")
        sys.exit(1)
    
    if not file2.exists():
        print(f"❌ 文件不存在: {file2}")
        sys.exit(1)
    
    compare_csv_files(file1, file2)
