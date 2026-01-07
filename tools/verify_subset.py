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
    cursor = importer.conn.cursor()
    
    # 使用原始 SQL 查询：在 filename, description, keywords 中搜索
    table_name = importer.table_name
    query = f"""
        SELECT * FROM {table_name}
        WHERE 
            filename LIKE ? OR
            description LIKE ? OR
            keywords LIKE ?
        LIMIT ?
    """
    
    keyword_pattern = f"%{keyword}%"
    cursor.execute(query, (keyword_pattern, keyword_pattern, keyword_pattern, limit))
    
    rows = cursor.fetchall()
    all_columns = [desc[0] for desc in cursor.description]
    
    # 转换为字典列表
    results = []
    for row in rows:
        row_dict = dict(row)
        # 构建 rich_context_text
        rich_text = importer._build_rich_context_text(row, all_columns)
        row_dict['rich_context_text'] = rich_text
        row_dict['semantic_text'] = rich_text  # 向后兼容
        results.append(row_dict)
    
    return results


def classify_data(processor: DataProcessor, metadata_list: List[Dict]) -> List[Dict]:
    """
    对数据进行分类（规则 + AI）
    
    Args:
        processor: DataProcessor 实例
        metadata_list: 元数据列表
    
    Returns:
        分类后的元数据列表（包含 category 和 classification_source）
    """
    import re
    classified = []
    
    for meta_dict in metadata_list:
        # 运行分类逻辑
        category, source = processor._extract_category(meta_dict)
        
        # 确定分类来源（使用与 _extract_category 相同的逻辑）
        classification_source = "UNCATEGORIZED"
        if category != "UNCATEGORIZED":
            rich_text = meta_dict.get('rich_context_text', '') or meta_dict.get('semantic_text', '')
            text_lower = rich_text.lower() if rich_text else ""
            
            # 检查 Level 0: 强规则（使用整词匹配）
            rule_matched = False
            for keyword, target_id in processor.strong_rules.items():
                keyword_lower = keyword.lower()
                pattern = rf"\b{re.escape(keyword_lower)}\b"
                if re.search(pattern, text_lower):
                    classification_source = "Level 0 (Rule)"
                    rule_matched = True
                    break
            
            if not rule_matched:
                # 检查 Level 1: 显式 Metadata
                raw_cat = meta_dict.get('category', '').strip()
                if raw_cat and "MISC" not in raw_cat.upper() and raw_cat.upper() != "UNCATEGORIZED":
                    classification_source = "Level 1 (Explicit Metadata)"
                else:
                    # Level 2: AI 预测
                    classification_source = "Level 2 (AI Prediction)"
        else:
            classification_source = "UNCATEGORIZED"
        
        # 更新元数据
        meta_dict['category'] = category
        meta_dict['classification_source'] = classification_source
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
    
    Args:
        metadata_list: 分类后的元数据列表
        embeddings: 向量嵌入矩阵
        output_path: 输出图片路径
        keyword: 搜索关键词（用于标题）
        processor: DataProcessor 实例（用于获取 UCSManager）
    """
    # 计算 UMAP 降维（2D）
    print(f"[可视化] 计算 UMAP 降维...")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        random_state=42
    )
    
    # 提取标签用于监督学习
    targets = []
    for meta in metadata_list:
        cat_id = meta.get('category', 'UNCATEGORIZED')
        if processor.ucs_manager:
            main_cat = processor.ucs_manager.get_main_category_by_id(cat_id)
            targets.append(main_cat if main_cat != "UNCATEGORIZED" else None)
        else:
            targets.append(cat_id if cat_id != "UNCATEGORIZED" else None)
    
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
    
    # 按分类来源分组
    categories = {}
    for i, meta in enumerate(metadata_list):
        cat_id = meta.get('category', 'UNCATEGORIZED')
        source = meta.get('classification_source', 'UNCATEGORIZED')
        
        # 获取主类别名称用于颜色
        if processor.ucs_manager:
            main_cat = processor.ucs_manager.get_main_category_by_id(cat_id)
            label = main_cat if main_cat != "UNCATEGORIZED" else cat_id
        else:
            label = cat_id
        
        if label not in categories:
            categories[label] = {
                'coords': [],
                'sources': [],
                'filenames': []
            }
        
        categories[label]['coords'].append(coordinates[i])
        categories[label]['sources'].append(source)
        categories[label]['filenames'].append(meta.get('filename', 'Unknown'))
    
    # 绘制散点图
    plt.figure(figsize=(16, 12))
    
    # 为每个类别分配颜色
    color_map = plt.cm.get_cmap('tab20')
    colors = {cat: color_map(i / len(categories)) for i, cat in enumerate(categories.keys())}
    
    for label, data in categories.items():
        coords = np.array(data['coords'])
        plt.scatter(
            coords[:, 0],
            coords[:, 1],
            label=label,
            alpha=0.6,
            s=50,
            c=[colors[label]]
        )
    
    plt.title(f'分类验证结果 - 关键词: "{keyword}"\n共 {len(metadata_list)} 条数据', fontsize=14, fontweight='bold')
    plt.xlabel('UMAP 维度 1', fontsize=12)
    plt.ylabel('UMAP 维度 2', fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"[可视化] 图片已保存: {output_path}")
    plt.close()


def print_classification_report(metadata_list: List[Dict]):
    """
    打印分类报告
    
    Args:
        metadata_list: 分类后的元数据列表
    """
    print("\n" + "="*80)
    print("分类报告")
    print("="*80)
    
    # 统计分类来源
    source_counts = {}
    category_counts = {}
    
    for meta in metadata_list:
        source = meta.get('classification_source', 'UNCATEGORIZED')
        cat_id = meta.get('category', 'UNCATEGORIZED')
        
        source_counts[source] = source_counts.get(source, 0) + 1
        category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
    
    print(f"\n📊 分类来源统计:")
    for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        percentage = count / len(metadata_list) * 100
        print(f"  {source}: {count} ({percentage:.1f}%)")
    
    print(f"\n📋 类别分布 (Top 10):")
    for cat_id, count in sorted(category_counts.items(), key=lambda x: -x[1])[:10]:
        percentage = count / len(metadata_list) * 100
        print(f"  {cat_id}: {count} ({percentage:.1f}%)")
    
    print(f"\n📝 详细分类结果 (前20条):")
    print("-" * 80)
    for i, meta in enumerate(metadata_list[:20]):
        filename = meta.get('filename', 'Unknown')
        cat_id = meta.get('category', 'UNCATEGORIZED')
        source = meta.get('classification_source', 'UNCATEGORIZED')
        print(f"{i+1:3d}. {filename[:50]:<50} -> {cat_id:<15} [{source}]")
    
    if len(metadata_list) > 20:
        print(f"\n... 还有 {len(metadata_list) - 20} 条数据未显示")
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='微缩验证工具 - 快速验证分类效果')
    parser.add_argument('keyword', type=str, help='搜索关键词（如 AIR, WEAPON, VEHICLE）')
    parser.add_argument('--limit', type=int, default=500, help='最大返回数量（默认 500）')
    parser.add_argument('--db', type=str, default='./test_assets/Sonic.sqlite', help='数据库路径')
    parser.add_argument('--output', type=str, default=None, help='输出图片路径（默认 verification_result.png）')
    
    args = parser.parse_args()
    
    keyword = args.keyword.upper()
    db_path = Path(args.db)
    limit = args.limit
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 默认输出为 verification_result.png
    output_path = Path(args.output) if args.output else Path("verification_result.png")
    
    print(f"🔍 微缩验证工具")
    print(f"关键词: {keyword}")
    print(f"数据库: {db_path}")
    print(f"最大数量: {limit}")
    print(f"输出: {output_path}")
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
    processor._load_platinum_centroids()
    print("✅ 初始化完成")
    
    # 2. 查询数据
    print(f"\n[步骤 2/5] 查询包含 '{keyword}' 的数据...")
    start_time = time.time()
    raw_metadata = query_by_keyword(importer, keyword, limit=limit)
    print(f"✅ 查询完成，找到 {len(raw_metadata)} 条数据（耗时 {time.time() - start_time:.2f} 秒）")
    
    if len(raw_metadata) == 0:
        print("❌ 未找到匹配的数据")
        sys.exit(1)
    
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
    print_classification_report(classified_metadata)
    
    print(f"\n✅ 验证完成！")
    print(f"   图片已保存: {output_path}")


if __name__ == "__main__":
    main()

