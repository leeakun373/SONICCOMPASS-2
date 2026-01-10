"""
Sonic Compass - 仅重新计算UMAP坐标脚本
用于在已有向量缓存的情况下，仅重新计算UMAP坐标（适用于参数调整）
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

try:
    import umap
    print("✅ 检测到 UMAP 库")
except ImportError:
    print("❌ 未检测到 UMAP！请先运行: pip install umap-learn")
    sys.exit(1)

try:
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    print("❌ 未检测到 scikit-learn！请先运行: pip install scikit-learn")
    sys.exit(1)

from data import SoundminerImporter
from core import (
    DataProcessor, VectorEngine, inject_category_vectors, umap_config,
    compute_ucs_layout, compute_gravity_layout, UCSManager
)


def recalculate_umap(mode: str = "both"):
    """
    仅重新计算UMAP坐标（使用现有向量缓存）
    
    Args:
        mode: 计算模式 ("ucs", "gravity", "both")
            - "ucs": 只计算UCS模式坐标
            - "gravity": 只计算Gravity模式坐标
            - "both": 同时计算两种模式（默认）
    """
    print("=" * 60)
    print(f"🔄 Sonic Compass: 重新计算UMAP坐标 (Recalculate UMAP Only) - Mode: {mode}")
    print("=" * 60)
    
    if mode not in ["ucs", "gravity", "both"]:
        print(f"❌ 无效的模式: {mode}，请使用 'ucs', 'gravity' 或 'both'")
        sys.exit(1)
    
    # 1. 配置路径（从配置文件读取）
    from data.database_config import get_database_path
    DB_PATH = get_database_path()
    CACHE_DIR = "./cache"
    
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    # 2. 初始化核心组件
    print("\n📦 初始化引擎...")
    print("   正在初始化 SoundminerImporter...")
    try:
        from core import UCSManager
        ucs_manager = UCSManager()
        ucs_manager.load_all()
        importer = SoundminerImporter(
            db_path=DB_PATH,
            ucs_manager=ucs_manager
        )
    except Exception as e:
        print(f"   [WARNING] UCSManager 初始化失败，使用默认配置: {e}")
        importer = SoundminerImporter(db_path=DB_PATH)
    
    print("   正在加载向量模型（这可能需要几秒钟）...")
    import sys
    sys.stdout.flush()  # 强制刷新输出
    
    try:
        vector_engine = VectorEngine(model_path="./models/bge-m3")
        print("   ✅ 模型加载完成")
    except Exception as e:
        print(f"   ❌ 模型加载失败: {e}")
        sys.exit(1)
    
    print("   正在创建 DataProcessor...")
    processor = DataProcessor(
        importer=importer,
        vector_engine=vector_engine,
        cache_dir=CACHE_DIR
    )
    # 【修复】确保 processor 有 ucs_manager（如果 importer 有的话）
    if hasattr(importer, 'ucs_manager') and importer.ucs_manager:
        processor.ucs_manager = importer.ucs_manager
    elif 'ucs_manager' in locals():
        processor.ucs_manager = ucs_manager
    print("   ✅ 初始化完成")
    
    # 3. 检查缓存是否存在
    if not processor._cache_exists():
        print("❌ 向量缓存不存在！")
        print("   请先运行: python rebuild_atlas.py")
        sys.exit(1)
    
    # 4. 加载现有向量和元数据（不重新计算）
    print("\n📂 加载现有向量缓存...")
    start_time = time.time()
    
    try:
        metadata, embeddings = processor.load_index()
        print(f"✅ 加载完成 ({len(metadata)} 条记录)")
        print(f"   耗时: {time.time() - start_time:.2f} 秒")
    except Exception as e:
        print(f"❌ 加载缓存失败: {e}")
        print("   请先运行: python rebuild_atlas.py")
        sys.exit(1)
    
    # 5. Phase 3.5: 提取主类别标签（关键：从 CatID 映射到主类别名称）
    print("\n🏷️  提取主类别标签（从 CatID 映射到主类别名称）...")
    
    # 确保 ucs_manager 已初始化
    if not processor.ucs_manager:
        print("   [警告] UCSManager 未初始化，尝试重新加载...")
        try:
            from core import UCSManager
            processor.ucs_manager = UCSManager()
            processor.ucs_manager.load_all()
            print("   ✅ UCSManager 初始化成功")
        except Exception as e:
            print(f"   [错误] UCSManager 初始化失败: {e}")
            print("   将使用 CatID 作为标签（可能产生 600+ 个类别）")
    
    targets = []
    missing_count = 0
    
    for meta in metadata:
        # metadata 的 'category' 字段存储的是 CatID（如 "AMBFORST"）
        raw_cat = meta.get('category', '') if isinstance(meta, dict) else getattr(meta, 'category', '')
        
        if not raw_cat or raw_cat == '' or raw_cat == 'UNCATEGORIZED':
            # 缺失类别：标记为 "UNCATEGORIZED"，后续将编码为 -1
            targets.append("UNCATEGORIZED")
            missing_count += 1
            continue
        
        # 【关键修复】使用 UCSManager 将 CatID 映射到主类别名称
        # 例如："AMBFORST" -> "AMBIENCE", "WPNGUN" -> "WEAPONS"
        if processor.ucs_manager:
            target_label = processor.ucs_manager.get_main_category_by_id(raw_cat)
        else:
            target_label = "UNCATEGORIZED"
        
        # 验证：如果映射结果为 "UNCATEGORIZED"，标记为缺失
        if target_label == "UNCATEGORIZED":
            targets.append("UNCATEGORIZED")
            missing_count += 1
        else:
            targets.append(target_label)  # 列表里是 [AMBIENCE, AMBIENCE, WEAPONS, WEAPONS, ...]
    
    # 【超级锚点策略】保存原始字符串列表（避免-1陷阱）
    targets_original = targets.copy()  # 保存字符串列表，用于向量注入
    
    # 使用 LabelEncoder 编码为整数数组
    # 将 "UNCATEGORIZED" 标记为特殊值，编码后再替换为 -1
    label_encoder = LabelEncoder()
    targets_encoded = label_encoder.fit_transform(targets)
    
    # 将 "UNCATEGORIZED" 的标签替换为 -1
    uncategorized_label_idx = None
    for i, cls in enumerate(label_encoder.classes_):
        if cls == 'UNCATEGORIZED':
            uncategorized_label_idx = i
            break
    
    if uncategorized_label_idx is not None:
        targets_encoded[targets_encoded == uncategorized_label_idx] = -1
    
    # 验证打印：检查唯一主类别数量
    unique_cats = set([t for t in targets if t != 'UNCATEGORIZED'])
    print(f"   发现 {len(unique_cats)} 个唯一主类别（应该是约 82 个）")
    if len(unique_cats) > 100:
        print(f"   ⚠️  [警告] 唯一类别数过多 ({len(unique_cats)})，可能仍在使用 CatID 而非主类别名称")
        print(f"   前20个类别: {list(sorted(unique_cats))[:20]}")
    elif len(unique_cats) < 5:
        print(f"   ⚠️  [警告] 分类过少 ({len(unique_cats)})，请检查 UCSManager 映射逻辑")
    else:
        print(f"   ✅ 主类别数量正常: {len(unique_cats)} 个")
        print(f"   示例类别: {list(sorted(unique_cats))[:10]}")
    
    if missing_count > 0:
        print(f"   [统计] 缺失类别数量: {missing_count} (已标记为 -1)")
    
    # 使用编码后的 targets（用于UMAP监督学习）
    targets = targets_encoded
    
    # 根据模式选择计算方式
    if mode in ["ucs", "both"]:
        print("\n" + "=" * 60)
        print("🗺️  UCS模式: 定锚群岛策略 (Fixed Archipelago Strategy)")
        print("=" * 60)
        
        # 确保UCSManager已初始化
        if not processor.ucs_manager:
            try:
                from core import UCSManager
                processor.ucs_manager = UCSManager()
                processor.ucs_manager.load_all()
            except Exception as e:
                print(f"❌ UCSManager 初始化失败: {e}")
                if mode == "ucs":
                    sys.exit(1)
        
        # 使用新的布局引擎计算UCS坐标
        try:
            coords_ucs, _ = compute_ucs_layout(
                metadata=metadata,
                embeddings=embeddings,
                ucs_manager=processor.ucs_manager,
                config_path="data_config/ucs_coordinates.json",
                use_parallel=True
            )
            processor.save_coordinates(coords_ucs, mode="ucs")
            print("✅ UCS坐标计算完成并保存")
        except FileNotFoundError as e:
            print(f"❌ UCS模式需要配置文件: {e}")
            print("   请先运行: python tools/extract_category_centroids.py")
            if mode == "ucs":
                sys.exit(1)
        except Exception as e:
            print(f"❌ UCS模式计算失败: {e}")
            import traceback
            traceback.print_exc()
            if mode == "ucs":
                sys.exit(1)
    
    if mode in ["gravity", "both"]:
        print("\n" + "=" * 60)
        print("🌌 Gravity模式: 纯无监督全局UMAP")
        print("=" * 60)
        
        # 使用新的布局引擎计算Gravity坐标
        try:
            coords_gravity = compute_gravity_layout(
                metadata=metadata,
                embeddings=embeddings
            )
            processor.save_coordinates(coords_gravity, mode="gravity")
            print("✅ Gravity坐标计算完成并保存")
        except Exception as e:
            print(f"❌ Gravity模式计算失败: {e}")
            import traceback
            traceback.print_exc()
            if mode == "gravity":
                sys.exit(1)
    
    # 【旧代码已删除】
    # 旧的归一化代码已被移除，因为新的 layout_engine 已经处理了坐标放置：
    # - UCS模式: compute_ucs_layout() 根据配置文件直接放置坐标，无需归一化
    # - Gravity模式: compute_gravity_layout() 返回原始UMAP坐标，归一化在保存前处理（如需要）
    
    # 坐标已在各模式分支中计算并保存完成
    print(f"\n✅ 坐标计算完成")
    
    # 7. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ UMAP坐标重新计算完成！")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    if mode == "ucs":
        print(f"   坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates_ucs.npy')}")
    elif mode == "gravity":
        print(f"   坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates_gravity.npy')}")
    else:
        print(f"   UCS坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates_ucs.npy')}")
        print(f"   Gravity坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates_gravity.npy')}")
    print("=" * 60)
    print("\n👉 现在可以运行: python main.py")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='重新计算UMAP坐标')
    parser.add_argument('--mode', type=str, default='both',
                       choices=['ucs', 'gravity', 'both'],
                       help='计算模式: ucs (UCS模式), gravity (Gravity模式), both (两者都计算，默认)')
    
    args = parser.parse_args()
    recalculate_umap(mode=args.mode)

