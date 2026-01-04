"""
生成 Platinum Centroids（白金质心）
从 ucs_definitions.json 读取 UCS 定义，生成标准质心向量文件
"""

import json
import pickle
import sys
from pathlib import Path

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.vector_engine import VectorEngine
from core.category_color_mapper import CategoryColorMapper


def generate_platinum_centroids():
    """
    从 ucs_definitions.json 生成 Platinum Centroids
    
    流程：
    1. 加载 data_config/ucs_definitions.json
    2. 使用 VectorEngine 编码每个 CatID 的描述文本
    3. 保存为 cache/platinum_centroids.pkl (格式: {CatID: Vector})
    """
    print("=" * 60)
    print("✨ 生成 Platinum Centroids (白金质心)")
    print("=" * 60)
    
    # 1. 配置路径
    json_path = Path("data_config/ucs_definitions.json")
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    output_path = cache_dir / "platinum_centroids_754.pkl"  # 更新文件名以反映 754 个 CatID
    
    # 2. 检查 JSON 文件是否存在
    if not json_path.exists():
        print(f"❌ JSON 文件不存在: {json_path}")
        print("   请先创建 ucs_definitions.json 文件")
        sys.exit(1)
    
    # 3. 加载 JSON
    print(f"\n📂 加载 UCS 定义文件: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            ucs_definitions = json.load(f)
        print(f"   ✅ 加载成功，共 {len(ucs_definitions)} 个 CatID 定义")
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        sys.exit(1)
    
    # 4. 初始化 VectorEngine
    print("\n🤖 初始化向量引擎...")
    try:
        vector_engine = VectorEngine(model_path="./models/bge-m3")
        print("   ✅ 向量引擎初始化完成")
    except Exception as e:
        print(f"   ❌ 向量引擎初始化失败: {e}")
        sys.exit(1)
    
    # 5. 初始化 CategoryColorMapper（用于验证 CatID）
    print("\n🎨 初始化 CategoryColorMapper...")
    try:
        mapper = CategoryColorMapper()
        print("   ✅ CategoryColorMapper 初始化完成")
    except Exception as e:
        print(f"   [WARNING] CategoryColorMapper 初始化失败: {e}")
        mapper = None
    
    # 6. 准备文本列表（按 CatID 顺序）
    print("\n📝 准备编码文本...")
    catids = []
    descriptions = []
    
    for catid, description in ucs_definitions.items():
        if not description or not str(description).strip():
            print(f"   [WARNING] CatID {catid} 的描述为空，跳过")
            continue
        
        # 验证 CatID 是否有效（可选）
        if mapper:
            category = mapper.get_category_from_catid(catid)
            if not category:
                print(f"   [WARNING] CatID {catid} 无法映射到 Category，但将继续处理")
        
        catids.append(catid)
        descriptions.append(str(description).strip())
    
    print(f"   ✅ 准备完成，共 {len(catids)} 个有效定义")
    
    # 7. 批量编码为向量
    print("\n🔄 开始编码向量（这可能需要一些时间）...")
    try:
        embeddings = vector_engine.encode_batch(
            descriptions,
            batch_size=32,
            show_progress=True,
            normalize_embeddings=True
        )
        print(f"   ✅ 编码完成，向量维度: {embeddings.shape}")
    except Exception as e:
        print(f"   ❌ 编码失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 8. 构建质心字典 {CatID: Vector}
    print("\n💎 构建 Platinum Centroids 字典...")
    platinum_centroids = {}
    for i, catid in enumerate(catids):
        platinum_centroids[catid] = embeddings[i]
    
    # 9. 保存到文件
    print(f"\n💾 保存到: {output_path}")
    try:
        with open(output_path, 'wb') as f:
            pickle.dump(platinum_centroids, f)
        print(f"   ✅ 保存成功")
    except Exception as e:
        print(f"   ❌ 保存失败: {e}")
        sys.exit(1)
    
    # 10. 统计信息
    print("\n" + "=" * 60)
    print("✅ Platinum Centroids (754 CatID) 生成完成！")
    print(f"   文件路径: {output_path}")
    print(f"   CatID 数量: {len(platinum_centroids)}")
    print(f"   向量维度: {embeddings.shape[1]}")
    print("=" * 60)
    print("\n👉 现在可以运行: python rebuild_atlas.py")
    print("   【754 CatID Source of Truth】AI 仲裁将基于这 754 个精确定义进行匹配")


if __name__ == "__main__":
    generate_platinum_centroids()

