"""
微缩验证工具 - 快速验证分类效果
从 SQLite 数据库提取特定关键词的数据，运行分类逻辑，生成可视化报告
"""

import sys
import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Tuple

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data import SoundminerImporter
from core import DataProcessor, VectorEngine, UCSManager, inject_category_vectors, umap_config
import umap


def query_by_keyword(importer: SoundminerImporter, keyword: str, limit: int = 500) -> List[Dict]:
    """
    从数据库查询包含关键词的数据（使用原始 SQL）
    
    Args:
        importer: SoundminerImporter 实例
        keyword: 搜索关键词
        limit: 最大返回数量
    
    Returns:
        元数据字典列表
    """
    importer._connect()
    
    # 【修复】确保表名已检测
    if importer.table_name is None:
        importer.table_name = importer._detect_table_name()
        importer.field_mapping = importer.FIELD_MAPPINGS.get(importer.table_name, {})
    
    cursor = importer.conn.cursor()
    
    # 【修复】先获取表的实际列名，支持大小写不敏感查询
    cursor.execute(f"PRAGMA table_info({importer.table_name})")
    table_info = cursor.fetchall()
    column_names = [col[1] for col in table_info]  # col[1] 是列名
    
    # 查找可能的字段名（大小写不敏感）
    filename_col = None
    description_col = None
    keywords_col = None
    
    for col in column_names:
        col_lower = col.lower()
        if col_lower == 'filename' and filename_col is None:
            filename_col = col
        if col_lower == 'description' and description_col is None:
            description_col = col
        if col_lower == 'keywords' and keywords_col is None:
            keywords_col = col
    
    # 使用实际字段名构建查询
    table_name = importer.table_name
    conditions = []
    params = []
    
    if filename_col:
        conditions.append(f"{filename_col} LIKE ?")
        params.append(f"%{keyword}%")
    if description_col:
        conditions.append(f"{description_col} LIKE ?")
        params.append(f"%{keyword}%")
    if keywords_col:
        conditions.append(f"{keywords_col} LIKE ?")
        params.append(f"%{keyword}%")
    
    if not conditions:
        # 如果没有找到任何字段，使用通配符查询所有列
        print(f"[WARNING] 未找到 filename/description/keywords 字段，使用通配符查询")
        query = f"SELECT * FROM {table_name} LIMIT ?"
        cursor.execute(query, (limit,))
    else:
        query = f"""
            SELECT * FROM {table_name}
            WHERE {' OR '.join(conditions)}
            LIMIT ?
        """
        params.append(limit)
        cursor.execute(query, tuple(params))
    
    rows = cursor.fetchall()
    all_columns = [desc[0] for desc in cursor.description]
    
    # 转换为字典列表
    results = []
    for row in rows:
        row_dict = dict(row)
        
        # 【修复】确保使用正确的字段名（数据库可能是大小写混合）
        # 将字段名统一为小写，方便后续访问
        row_dict_lower = {}
        for key, value in row_dict.items():
            row_dict_lower[key.lower()] = value
            row_dict_lower[key] = value  # 保留原始字段名
        
        # 构建 rich_context_text（使用原始 row 和 all_columns）
        rich_text = importer._build_rich_context_text(row, all_columns)
        row_dict['rich_context_text'] = rich_text
        row_dict['semantic_text'] = rich_text  # 向后兼容
        
        # 【修复】确保 filename 字段可用（尝试多种可能的字段名）
        if 'filename' not in row_dict or not row_dict.get('filename'):
            # 尝试查找可能的字段名（大小写不敏感）
            for col in all_columns:
                if col.lower() == 'filename':
                    row_dict['filename'] = row_dict.get(col, 'Unknown')
                    break
            else:
                # 如果还是找不到，使用第一个字段或 'Unknown'
                row_dict['filename'] = row_dict.get(all_columns[0] if all_columns else 'Unknown', 'Unknown')
        
        # 【修复】确保 category 字段可用
        if 'category' not in row_dict:
            for col in all_columns:
                if col.lower() == 'category':
                    row_dict['category'] = row_dict.get(col, '')
                    break
            else:
                row_dict['category'] = ''
        
        results.append(row_dict)
    
    return results


def classify_data(processor: DataProcessor, metadata_list: List[Dict]) -> List[Dict]:
    """
    对数据进行分类（规则 + AI）
    
    【重要】使用与正式流程完全相同的分类逻辑（_extract_category）
    确保测试结果与正式流程一致。
    
    Args:
        processor: DataProcessor 实例
        metadata_list: 元数据列表
    
    Returns:
        分类后的元数据列表（包含 category 和 classification_source）
    """
    classified = []
    
    for meta_dict in metadata_list:
        # 【关键】使用与正式流程完全相同的分类逻辑
        # _extract_category 返回 (category, source) 元组
        
        # 【调试】检查 ucs_manager 是否可用
        if not processor.ucs_manager:
            print(f"[WARNING] processor.ucs_manager 为 None，无法进行短路逻辑匹配")
        
        result = processor._extract_category(meta_dict)
        
        if result:
            category, source = result
        else:
            category = "UNCATEGORIZED"
            source = "未分类"
        
        # 【调试】如果分类失败，打印调试信息（仅前3条）
        if category == "UNCATEGORIZED" and len(classified) < 3:
            filename = meta_dict.get('filename', 'Unknown')
            if filename.startswith('ANML'):
                # 测试短路逻辑
                if processor.ucs_manager:
                    test_catid = processor.ucs_manager.resolve_category_from_filename(filename)
                    if test_catid:
                        test_validated = processor.ucs_manager.enforce_strict_category(test_catid)
                        print(f"[调试] 文件 {filename[:50]}: 短路逻辑返回 {test_catid} -> {test_validated}")
        
        # 更新元数据
        meta_dict['category'] = category
        meta_dict['classification_source'] = source
        
        # 【新增】获取主类别信息（用于聚类分析）
        if processor.ucs_manager and category != "UNCATEGORIZED":
            main_cat = processor.ucs_manager.get_main_category_by_id(category)
            meta_dict['main_category'] = main_cat if main_cat != "UNCATEGORIZED" else category
        else:
            meta_dict['main_category'] = category
        
        classified.append(meta_dict)
    
    return classified


def _generate_lod0_labels(
    categories: Dict[str, Dict],
    coordinates: np.ndarray,
    metadata_list: List[Dict],
    min_cluster_size: int = 5
) -> List[Tuple[str, Tuple[float, float], int]]:
    """
    生成 LOD 0 标签（主类别区域标注）
    类似于软件中的连通域分析，找到同一主类别的聚集区域并标注
    
    Args:
        categories: 按主类别分组的数据字典
        coordinates: 所有点的坐标
        metadata_list: 元数据列表
        min_cluster_size: 最小聚类大小（少于这个数量的区域不标注）
    
    Returns:
        标签列表，每个元素是 (标签文本, 中心坐标(x, y), 点数量)
    """
    from sklearn.cluster import DBSCAN
    
    labels = []
    
    for main_cat, data in categories.items():
        if main_cat == 'UNCATEGORIZED':
            continue
        
        coords = np.array(data['coords'])
        if len(coords) < min_cluster_size:
            continue
        
        # 使用 DBSCAN 找到聚集的区域
        # eps: 聚类半径（根据坐标范围自适应调整）
        coord_range = coordinates.max(axis=0) - coordinates.min(axis=0)
        avg_range = np.mean(coord_range)
        eps = avg_range * 0.1  # 使用坐标范围的10%作为聚类半径
        
        clustering = DBSCAN(eps=eps, min_samples=min_cluster_size).fit(coords)
        
        # 为每个聚类找到中心并生成标签
        unique_labels = set(clustering.labels_)
        unique_labels.discard(-1)  # 移除噪声点
        
        for cluster_id in unique_labels:
            cluster_mask = clustering.labels_ == cluster_id
            cluster_coords = coords[cluster_mask]
            
            if len(cluster_coords) >= min_cluster_size:
                # 计算聚类中心
                center = cluster_coords.mean(axis=0)
                labels.append((main_cat, (center[0], center[1]), len(cluster_coords)))
    
    # 如果 DBSCAN 没有找到足够的聚类，使用简单的中心点方法
    if len(labels) == 0:
        for main_cat, data in categories.items():
            if main_cat == 'UNCATEGORIZED':
                continue
            
            coords = np.array(data['coords'])
            if len(coords) >= min_cluster_size:
                center = coords.mean(axis=0)
                labels.append((main_cat, (center[0], center[1]), len(coords)))
    
    return labels


def visualize_results(
    metadata_list: List[Dict],
    embeddings: np.ndarray,
    output_path: Path,
    keyword: str,
    processor: DataProcessor,
    show_lod0_labels: bool = True
):
    """
    使用 matplotlib 生成散点图，支持 LOD 0 标签标注
    
    【UMAP 坐标说明】
    - X轴（UMAP 维度 1）: 降维后的第一个维度，表示数据在语义空间中的位置
    - Y轴（UMAP 维度 2）: 降维后的第二个维度，表示数据在语义空间中的位置
    - 坐标范围: 通常为 -10 到 10 之间（取决于 UMAP 参数）
    - 聚类效果: 同一主类别（如 WEAPON）的数据应该在坐标上聚集在一起
    
    Args:
        metadata_list: 分类后的元数据列表（已包含 coordinates）
        embeddings: 向量嵌入矩阵
        output_path: 输出图片路径
        keyword: 搜索关键词（用于标题）
        processor: DataProcessor 实例（用于获取 UCSManager）
        show_lod0_labels: 是否显示 LOD 0 标签（主类别区域标注）
    """
    # 计算 UMAP 降维（2D）
    print(f"[可视化] 计算 UMAP 降维...")
    print(f"[说明] UMAP 坐标含义:")
    print(f"  - X轴: 降维后的第一个维度（语义空间位置）")
    print(f"  - Y轴: 降维后的第二个维度（语义空间位置）")
    print(f"  - 同一主类别的数据应该在坐标上聚集（形成'大陆'）")
    if len(metadata_list) > 5000:
        print(f"[提示] 数据量较大（{len(metadata_list)} 条），UMAP 计算可能需要几分钟，请耐心等待...")
    
    # 提取标签用于监督学习（使用主类别）
    targets = []
    for meta in metadata_list:
        main_cat = meta.get('main_category', 'UNCATEGORIZED')
        targets.append(main_cat if main_cat != "UNCATEGORIZED" else "UNCATEGORIZED")
    
    # 【超级锚点策略】保存原始字符串列表（用于向量注入）
    targets_original = targets.copy()  # 保存字符串列表，避免None
    
    # 使用更强的监督参数（与主流程一致）
    use_supervised = len(metadata_list) > 100 and any(t != "UNCATEGORIZED" and t is not None for t in targets)
    
    # 【超级锚点策略】向量注入：将主类别的One-Hot向量注入到音频embedding中
    if use_supervised and len(metadata_list) > 50:  # 小数据集可以跳过，避免过度约束
        print(f"[可视化] 应用超级锚点策略（数据量: {len(metadata_list)}）...")
        # 从统一配置获取注入参数（支持自适应权重）
        injection_params = umap_config.get_injection_params(
            data_size=len(metadata_list),
            use_adaptive=True  # 启用自适应：小数据集用较小权重
        )
        X_combined, _ = inject_category_vectors(
            embeddings=embeddings,
            target_labels=targets_original,
            audio_weight=injection_params['audio_weight'],
            category_weight=injection_params['category_weight']
        )
        print(f"[可视化] 向量注入完成: {embeddings.shape} -> {X_combined.shape} (权重: {injection_params['category_weight']})")
        embeddings = X_combined  # 使用混合向量替代原始embeddings
    else:
        print(f"[可视化] 跳过超级锚点策略（数据量: {len(metadata_list)}）...")
    
    # 从统一配置获取UMAP参数（支持自适应和场景判断）
    umap_params = umap_config.get_umap_params(
        data_size=len(metadata_list),
        use_adaptive=True,  # 启用自适应：小数据集使用较小的 min_dist
        is_supervised=use_supervised  # 根据是否为监督学习决定是否添加监督参数
    )
    # 根据数据量调整n_neighbors（避免超出数据量）
    umap_params['n_neighbors'] = min(umap_params['n_neighbors'], len(embeddings) - 1) if len(embeddings) > 1 else 15
    
    reducer = umap.UMAP(**umap_params)
    
    # 如果有标签，使用监督 UMAP
    if use_supervised:
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        encoded_targets = []
        for t in targets_original:
            if t == "UNCATEGORIZED" or t is None:
                encoded_targets.append(-1)
            else:
                encoded_targets.append(t)
        
        unique_targets = sorted(set([t for t in encoded_targets if t != -1]))
        if len(unique_targets) > 1:
            le.fit(unique_targets)
            encoded = [le.transform([t])[0] if t != -1 else -1 for t in encoded_targets]
            encoded = np.array(encoded)
            coordinates = reducer.fit_transform(embeddings, y=encoded)  # embeddings已经是X_combined（如果应用了超级锚点）
        else:
            coordinates = reducer.fit_transform(embeddings)
    else:
        coordinates = reducer.fit_transform(embeddings)
    
    # 【新增】保存坐标到 metadata_list（用于后续 CSV 导出）
    for i, meta in enumerate(metadata_list):
        meta['umap_x'] = float(coordinates[i][0])
        meta['umap_y'] = float(coordinates[i][1])
    
    # 按主类别分组（用于可视化）
    categories = {}
    for i, meta in enumerate(metadata_list):
        main_cat = meta.get('main_category', 'UNCATEGORIZED')
        cat_id = meta.get('category', 'UNCATEGORIZED')
        source = meta.get('classification_source', 'UNCATEGORIZED')
        
        # 使用主类别作为标签（用于验证聚类效果）
        label = main_cat
        
        if label not in categories:
            categories[label] = {
                'coords': [],
                'sources': [],
                'filenames': [],
                'catids': []
            }
        
        categories[label]['coords'].append(coordinates[i])
        categories[label]['sources'].append(source)
        categories[label]['filenames'].append(meta.get('filename', 'Unknown'))
        categories[label]['catids'].append(cat_id)
    
    # 绘制散点图
    plt.figure(figsize=(16, 12))
    
    # 为每个主类别分配颜色
    try:
        color_map = plt.colormaps.get_cmap('tab20')
    except AttributeError:
        # 兼容旧版本 matplotlib
        color_map = plt.cm.get_cmap('tab20')
    
    colors = {cat: color_map(i / len(categories)) for i, cat in enumerate(categories.keys())}
    
    for label, data in categories.items():
        coords = np.array(data['coords'])
        plt.scatter(
            coords[:, 0],
            coords[:, 1],
            label=f"{label} ({len(coords)})",
            alpha=0.6,
            s=50,
            c=[colors[label]]
        )
    
    # 【新增】LOD 0 标签标注（主类别区域标注）
    if show_lod0_labels:
        print(f"[可视化] 生成 LOD 0 标签（主类别区域标注）...")
        lod0_labels = _generate_lod0_labels(categories, coordinates, metadata_list, min_cluster_size=max(5, len(metadata_list) // 100))
        
        for label_text, (x, y), count in lod0_labels:
            # 绘制白色半透明背景（增强可读性）
            plt.text(
                x, y, label_text,
                fontsize=14,
                fontweight='bold',
                color='white',
                ha='center',
                va='center',
                bbox=dict(
                    boxstyle='round,pad=0.5',
                    facecolor='black',
                    alpha=0.6,
                    edgecolor='white',
                    linewidth=1.5
                ),
                zorder=100  # 确保标签在最上层
            )
        
        print(f"[可视化] 已标注 {len(lod0_labels)} 个主类别区域")
    
    plt.title(f'分类验证结果 - 关键词: "{keyword}"\n共 {len(metadata_list)} 条数据' + (' (含LOD0标签)' if show_lod0_labels else ''), 
              fontsize=14, fontweight='bold')
    plt.xlabel('UMAP Dimension 1 (X-axis)', fontsize=12)
    plt.ylabel('UMAP Dimension 2 (Y-axis)', fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"[可视化] 图片已保存: {output_path}")
    plt.close()


def print_classification_report(metadata_list: List[Dict], processor: DataProcessor):
    """
    打印分类报告
    
    Args:
        metadata_list: 分类后的元数据列表（已包含 coordinates）
        processor: DataProcessor 实例（用于获取 UCSManager）
    """
    print("\n" + "="*80)
    print("分类报告")
    print("="*80)
    
    # 统计分类来源
    source_counts = {}
    category_counts = {}
    main_category_counts = {}
    
    for meta in metadata_list:
        source = meta.get('classification_source', 'UNCATEGORIZED')
        cat_id = meta.get('category', 'UNCATEGORIZED')
        main_cat = meta.get('main_category', 'UNCATEGORIZED')
        
        source_counts[source] = source_counts.get(source, 0) + 1
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        main_category_counts[main_cat] = main_category_counts.get(main_cat, 0) + 1
    
    print(f"\n📊 分类来源统计:")
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        percentage = count / len(metadata_list) * 100
        print(f"  {source}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 主类别分布 (Top 10):")
    for main_cat, count in sorted(main_category_counts.items(), key=lambda x: -x[1])[:10]:
        percentage = count / len(metadata_list) * 100
        print(f"  {main_cat}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 CatID 分布 (Top 10):")
    for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1])[:10]:
        percentage = count / len(metadata_list) * 100
        print(f"  {cat_id}: {count} ({percentage:.1f}%)")
    
    print(f"\n📝 详细分类结果 (前20条):")
    print("-" * 80)
    print(f"{'序号':<5} {'文件名':<45} {'CatID':<15} {'主类别':<15} {'来源':<25} {'坐标(X,Y)':<20}")
    print("-" * 80)
    for i, meta in enumerate(metadata_list[:20]):
        filename = meta.get('filename') or meta.get('Filename') or meta.get('FILENAME') or 'Unknown'
        cat_id = meta.get('category', 'UNCATEGORIZED')
        main_cat = meta.get('main_category', 'UNCATEGORIZED')
        source = meta.get('classification_source', 'UNCATEGORIZED')
        x = meta.get('umap_x', 0)
        y = meta.get('umap_y', 0)
        print(f"{i+1:3d}. {str(filename)[:43]:<43} {cat_id:<15} {main_cat:<15} {source[:23]:<23} ({x:.2f}, {y:.2f})")
    
    if len(metadata_list) > 20:
        print(f"\n... 还有 {len(metadata_list) - 20} 条数据未显示")
    
    print("="*80)


def export_to_csv(metadata_list: List[Dict], output_dir: Path, keyword: str, timestamp: str):
    """
    导出详细数据到 CSV 文件
    
    Args:
        metadata_list: 分类后的元数据列表（已包含 coordinates）
        output_dir: 输出文件夹路径
        keyword: 搜索关键词（用于文件名）
        timestamp: 时间戳（格式：MMDDHHmm）
    """
    import csv
    
    csv_path = output_dir / f"verify_{keyword}_details_{timestamp}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # 表头
        writer.writerow([
            '序号', '文件名', 'CatID', '主类别', '分类来源', 
            'UMAP_X', 'UMAP_Y', 'Rich Text (前100字符)'
        ])
        
        # 数据行
        for i, meta in enumerate(metadata_list):
            filename = meta.get('filename') or meta.get('Filename') or meta.get('FILENAME') or 'Unknown'
            cat_id = meta.get('category', 'UNCATEGORIZED')
            main_cat = meta.get('main_category', 'UNCATEGORIZED')
            source = meta.get('classification_source', 'UNCATEGORIZED')
            x = meta.get('umap_x', 0)
            y = meta.get('umap_y', 0)
            rich_text = meta.get('rich_context_text', '')[:100]
            
            writer.writerow([
                i + 1,
                filename,
                cat_id,
                main_cat,
                source,
                f"{x:.4f}",
                f"{y:.4f}",
                rich_text
            ])
    
    print(f"[导出] CSV 文件已保存: {csv_path}")
    print(f"       可以用 Excel 打开，查看详细数据和坐标分布")


def query_all_data(importer: SoundminerImporter, limit: int = 10000) -> List[Dict]:
    """
    从数据库查询所有数据（全库模式）
    
    Args:
        importer: SoundminerImporter 实例
        limit: 最大返回数量（避免数据过多）
    
    Returns:
        元数据字典列表
    """
    importer._connect()
    
    # 【修复】确保表名已检测
    if importer.table_name is None:
        importer.table_name = importer._detect_table_name()
        importer.field_mapping = importer.FIELD_MAPPINGS.get(importer.table_name, {})
    
    cursor = importer.conn.cursor()
    table_name = importer.table_name
    
    # 查询所有数据
    query = f"SELECT * FROM {table_name} LIMIT ?"
    cursor.execute(query, (limit,))
    
    rows = cursor.fetchall()
    all_columns = [desc[0] for desc in cursor.description]
    
    # 转换为字典列表
    results = []
    for row in rows:
        row_dict = dict(zip(all_columns, row))
        
        # 构建 rich_context_text
        rich_text = importer._build_rich_context_text(row, all_columns)
        row_dict['rich_context_text'] = rich_text
        row_dict['semantic_text'] = rich_text
        
        # 确保必要字段存在
        if 'filename' not in row_dict or not row_dict.get('filename'):
            for col in all_columns:
                if col.lower() == 'filename':
                    row_dict['filename'] = row_dict.get(col, 'Unknown')
                    break
            else:
                row_dict['filename'] = row_dict.get(all_columns[0] if all_columns else 'Unknown', 'Unknown')
        
        if 'category' not in row_dict:
            for col in all_columns:
                if col.lower() == 'category':
                    row_dict['category'] = row_dict.get(col, '')
                    break
            else:
                row_dict['category'] = ''
        
        results.append(row_dict)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='微缩验证工具 - 快速验证分类效果')
    parser.add_argument('keyword', type=str, nargs='?', default=None, help='搜索关键词（如 AIR, WEAPON, VEHICLE），可选')
    parser.add_argument('--all', '--full-db', action='store_true', dest='full_db', help='全库模式：处理整个数据库（不使用关键词）')
    parser.add_argument('--limit', type=int, default=500, help='最大返回数量（默认 500，全库模式默认 10000）')
    parser.add_argument('--db', type=str, default=None, help='数据库路径（默认从配置文件读取）')
    parser.add_argument('--output', type=str, default=None, help='输出图片路径（可选，默认自动生成）')
    parser.add_argument('--no-lod0', action='store_true', dest='no_lod0', help='禁用 LOD 0 标签标注')
    
    args = parser.parse_args()
    
    # 全库模式：不需要关键词
    if args.full_db:
        keyword = "ALL"
        limit = max(args.limit, 1000)  # 全库模式至少1000条
        print(f"[模式] 全库模式：将处理最多 {limit} 条数据")
    elif args.keyword:
        keyword = args.keyword.upper()
        limit = args.limit
    else:
        print("❌ 错误：请指定搜索关键词或使用 --all 参数进行全库模式")
        parser.print_help()
        sys.exit(1)
    
    # 【新增】从配置文件读取数据库路径（如果用户未指定）
    if args.db:
        db_path = Path(args.db)
    else:
        from data.database_config import get_database_path
        db_path_str = get_database_path()
        db_path = Path(db_path_str)
        print(f"[INFO] 使用配置文件中的数据库路径: {db_path}")
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 【新增】创建专属输出文件夹
    output_dir = Path("verify_output")
    output_dir.mkdir(exist_ok=True)
    
    # 【新增】生成时间戳（格式：MMDDHHmm，例如：01061223 表示 1月6日12点23分）
    from datetime import datetime
    timestamp = datetime.now().strftime("%m%d%H%M")
    
    # 生成输出文件路径（带时间戳）
    if args.output:
        # 如果用户指定了输出路径，提取文件名并添加时间戳
        user_path = Path(args.output)
        # 添加时间戳：原文件名_时间戳.扩展名
        # 如果用户没有指定扩展名，默认使用 .png
        if not user_path.suffix:
            output_path = output_dir / f"{user_path.stem}_{timestamp}.png"
        else:
            output_path = output_dir / f"{user_path.stem}_{timestamp}{user_path.suffix}"
    else:
        # 默认文件名：verify_{keyword}_{timestamp}.png
        output_path = output_dir / f"verify_{keyword}_{timestamp}.png"
    
    print(f"🔍 微缩验证工具")
    if args.full_db:
        print(f"模式: 全库模式")
    else:
        print(f"关键词: {keyword}")
    print(f"数据库: {db_path}")
    print(f"最大数量: {limit}")
    print(f"输出文件夹: {output_dir}/")
    print(f"输出图片: {output_path.name}")
    print(f"时间戳: {timestamp}")
    print(f"LOD 0 标签: {'禁用' if args.no_lod0 else '启用'}")
    print()
    
    # 1. 初始化组件
    print("[步骤 1/5] 初始化组件...")
    importer = SoundminerImporter(db_path=str(db_path))
    vector_engine = VectorEngine(model_path="./models/bge-m3")
    ucs_manager = UCSManager()
    processor = DataProcessor(
        importer=importer,
        vector_engine=vector_engine,
        cache_dir="./cache"
    )
    processor.ucs_manager = ucs_manager
    ucs_manager.load_all()  # 确保 UCS Manager 已加载
    processor._load_platinum_centroids()
    
    # 【调试】验证 UCS Manager 是否正确加载
    if processor.ucs_manager:
        test_catid = processor.ucs_manager.resolve_category_from_filename("ANMLAqua_Test.wav")
        if test_catid:
            validated = processor.ucs_manager.enforce_strict_category(test_catid)
            print(f"[调试] 短路逻辑测试: ANMLAqua -> {validated}")
    
    print("✅ 初始化完成")
    
    # 2. 查询数据
    if args.full_db:
        print(f"\n[步骤 2/5] 查询所有数据（全库模式）...")
    else:
        print(f"\n[步骤 2/5] 查询包含 '{keyword}' 的数据...")
    start_time = time.time()
    
    if args.full_db:
        raw_metadata = query_all_data(importer, limit=limit)
    else:
        raw_metadata = query_by_keyword(importer, keyword, limit=limit)
    
    print(f"✅ 查询完成，找到 {len(raw_metadata)} 条数据（耗时 {time.time() - start_time:.2f} 秒）")
    
    if len(raw_metadata) == 0:
        print("❌ 未找到匹配的数据")
        sys.exit(1)
    
    # 【调试】显示前3条数据的详细信息
    print(f"\n[调试] 前3条数据示例:")
    for i, meta in enumerate(raw_metadata[:3]):
        filename = meta.get('filename') or meta.get('Filename') or 'Unknown'
        rich_text = meta.get('rich_context_text', '')
        print(f"  {i+1}. Filename: {filename}")
        print(f"     Rich Text (前100字符): {rich_text[:100] if rich_text else '(空)'}")
        print(f"     Category (原始): {meta.get('category', '(空)')}")
        print()
    
    # 3. 向量化
    print(f"\n[步骤 3/5] 向量化数据...")
    start_time = time.time()
    texts = [meta.get('rich_context_text', '') or meta.get('semantic_text', '') for meta in raw_metadata]
    embeddings = vector_engine.encode_batch(texts, batch_size=32, normalize_embeddings=True)
    print(f"✅ 向量化完成（耗时 {time.time() - start_time:.2f} 秒）")
    
    # 4. 分类
    print(f"\n[步骤 4/5] 运行分类逻辑...")
    start_time = time.time()
    classified_metadata = classify_data(processor, raw_metadata)
    print(f"✅ 分类完成（耗时 {time.time() - start_time:.2f} 秒）")
    
    # 5. 可视化
    print(f"\n[步骤 5/5] 生成可视化...")
    visualize_results(classified_metadata, embeddings, output_path, keyword, processor, show_lod0_labels=not args.no_lod0)
    
    # 6. 打印报告
    print_classification_report(classified_metadata, processor)
    
    # 7. 导出 CSV（详细数据表）
    print(f"\n[步骤 6/6] 导出详细数据到 CSV...")
    export_to_csv(classified_metadata, output_dir, keyword, timestamp)
    
    csv_filename = f"verify_{keyword}_details_{timestamp}.csv"
    
    print(f"\n✅ 验证完成！")
    print(f"   输出文件夹: {output_dir}/")
    print(f"   图片已保存: {output_path.name}")
    print(f"   CSV 已保存: {csv_filename}")
    print(f"   时间戳: {timestamp}")
    print(f"\n💡 提示:")
    print(f"   - 所有输出文件都在 '{output_dir}/' 文件夹中")
    print(f"   - 查看 CSV 文件可以了解每条数据的详细分类结果")
    print(f"   - 检查 UMAP_X 和 UMAP_Y 坐标，同一主类别的数据应该聚集在一起")
    print(f"   - 如果同一主类别的数据分散，说明聚类效果需要改进")


if __name__ == "__main__":
    main()

