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
from core import DataProcessor, VectorEngine, UCSManager
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


def visualize_results(
    metadata_list: List[Dict],
    embeddings: np.ndarray,
    output_path: Path,
    keyword: str,
    processor: DataProcessor
):
    """
    使用 matplotlib 生成散点图
    
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
    """
    # 计算 UMAP 降维（2D）
    print(f"[可视化] 计算 UMAP 降维...")
    print(f"[说明] UMAP 坐标含义:")
    print(f"  - X轴: 降维后的第一个维度（语义空间位置）")
    print(f"  - Y轴: 降维后的第二个维度（语义空间位置）")
    print(f"  - 同一主类别的数据应该在坐标上聚集（形成'大陆'）")
    
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        random_state=42
    )
    
    # 提取标签用于监督学习（使用主类别）
    targets = []
    for meta in metadata_list:
        main_cat = meta.get('main_category', 'UNCATEGORIZED')
        targets.append(main_cat if main_cat != "UNCATEGORIZED" else None)
    
    # 如果有标签，使用监督 UMAP
    if any(t is not None for t in targets):
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        encoded_targets = []
        for t in targets:
            if t is None:
                encoded_targets.append(-1)
            else:
                encoded_targets.append(t)
        
        unique_targets = sorted(set([t for t in encoded_targets if t != -1]))
        if len(unique_targets) > 1:
            le.fit(unique_targets)
            encoded = [le.transform([t])[0] if t != -1 else -1 for t in encoded_targets]
            coordinates = reducer.fit_transform(embeddings, y=encoded)
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
    
    plt.title(f'分类验证结果 - 关键词: "{keyword}"\n共 {len(metadata_list)} 条数据', fontsize=14, fontweight='bold')
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


def main():
    parser = argparse.ArgumentParser(description='微缩验证工具 - 快速验证分类效果')
    parser.add_argument('keyword', type=str, help='搜索关键词（如 AIR, WEAPON, VEHICLE）')
    parser.add_argument('--limit', type=int, default=500, help='最大返回数量（默认 500）')
    parser.add_argument('--db', type=str, default=None, help='数据库路径（默认从配置文件读取）')
    parser.add_argument('--output', type=str, default=None, help='输出图片路径（可选，默认自动生成）')
    
    args = parser.parse_args()
    
    keyword = args.keyword.upper()
    limit = args.limit
    
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
    print(f"关键词: {keyword}")
    print(f"数据库: {db_path}")
    print(f"最大数量: {limit}")
    print(f"输出文件夹: {output_dir}/")
    print(f"输出图片: {output_path.name}")
    print(f"时间戳: {timestamp}")
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
    print(f"\n[步骤 2/5] 查询包含 '{keyword}' 的数据...")
    start_time = time.time()
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
    visualize_results(classified_metadata, embeddings, output_path, keyword, processor)
    
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

