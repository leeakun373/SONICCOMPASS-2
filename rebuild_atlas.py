"""
Sonic Compass - 重建星图脚本
"""
import sys
import os
import time
import numpy as np
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# 导入工具脚本
print("[导入] 开始导入模块...", flush=True)
sys.stdout.flush()

# 使用 importlib 动态导入，避免在导入时执行模块级代码
try:
    print("[导入] 导入 generate_platinum_centroids...", flush=True)
    sys.stdout.flush()
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_platinum_centroids",
        Path(__file__).parent / "tools" / "generate_platinum_centroids.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generate_platinum_centroids = module.generate_platinum_centroids
    print("[导入] ✅ generate_platinum_centroids 导入成功", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"❌ 无法导入质心生成工具: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)

try:
    print("[导入] 导入 umap...", flush=True)
    sys.stdout.flush()
    import umap
    print("✅ 检测到 UMAP 库", flush=True)
    sys.stdout.flush()
except ImportError:
    print("❌ 未检测到 UMAP！请先运行: pip install umap-learn", flush=True)
    sys.stdout.flush()
    sys.exit(1)

try:
    print("[导入] 导入 sklearn...", flush=True)
    sys.stdout.flush()
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
    print("[导入] ✅ sklearn 导入成功", flush=True)
    sys.stdout.flush()
except ImportError:
    print("❌ 未检测到 scikit-learn！请先运行: pip install scikit-learn", flush=True)
    sys.stdout.flush()
    sys.exit(1)

# 延迟导入：不在模块级别导入 data 和 core，避免在导入时触发初始化
# from data import SoundminerImporter
# from core import DataProcessor, VectorEngine

def rebuild():
    print("=" * 60, flush=True)
    print("🚀 Sonic Compass: 正在重绘星系地图 (Rebuilding Atlas)", flush=True)
    print("=" * 60, flush=True)
    sys.stdout.flush()

    # 1. 检查并生成白金质心 (Phase 3.5 Critical Step)
    centroid_path = Path("./cache/platinum_centroids_754.pkl")
    print(f"[DEBUG] 检查质心文件: {centroid_path.absolute()}", flush=True)
    print(f"[DEBUG] 文件存在: {centroid_path.exists()}", flush=True)
    sys.stdout.flush()
    
    if not centroid_path.exists():
        print("\n[自动执行] 未检测到质心缓存，正在从 JSON 生成 753 个白金质心...", flush=True)
        sys.stdout.flush()
        try:
            # 调用工具脚本生成
            print("[DEBUG] 开始调用 generate_platinum_centroids()...", flush=True)
            sys.stdout.flush()
            generate_platinum_centroids() 
            print("✅ 白金质心生成完毕", flush=True)
            sys.stdout.flush()
        except Exception as e:
            print(f"❌ 质心生成失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            sys.exit(1)
    else:
        print("\n[INFO] 检测到现有白金质心缓存，跳过生成。", flush=True)
        sys.stdout.flush()

    # 2. 延迟导入并初始化核心组件
    print("\n📦 初始化引擎...")
    sys.stdout.flush()
    
    # 【新增】从配置文件读取数据库路径
    from data.database_config import get_database_path
    DB_PATH = get_database_path()
    CACHE_DIR = "./cache"
    
    if not Path(DB_PATH).exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        print("   请检查 data_config/user_config.json 中的 database_path 配置")
        sys.exit(1)
    
    print("   [步骤] 导入 data 模块...", flush=True)
    sys.stdout.flush()
    try:
        from data import SoundminerImporter
        print("   [步骤] ✅ SoundminerImporter 导入成功", flush=True)
        sys.stdout.flush()
    except ImportError as e:
        print(f"   ❌ 导入 SoundminerImporter 失败: {e}", flush=True)
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("   [步骤] 导入 core 模块...", flush=True)
    sys.stdout.flush()
    try:
        from core import DataProcessor, VectorEngine, inject_category_vectors, umap_config
        print("   [步骤] ✅ DataProcessor 和 VectorEngine 导入成功", flush=True)
        sys.stdout.flush()
    except ImportError as e:
        print(f"   ❌ 导入 core 模块失败: {e}", flush=True)
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("   正在初始化 SoundminerImporter...", flush=True)
    sys.stdout.flush()
    importer = SoundminerImporter(db_path=DB_PATH)
    
    print("   正在加载向量模型（这可能需要几秒钟）...", flush=True)
    sys.stdout.flush()
    vector_engine = VectorEngine(model_path="./models/bge-m3")
    print("   ✅ 模型加载完成", flush=True)
    sys.stdout.flush()
    
    print("   正在创建 DataProcessor...", flush=True)
    sys.stdout.flush()
    processor = DataProcessor(
        importer=importer,
        vector_engine=vector_engine,
        cache_dir=CACHE_DIR
    )
    print("   ✅ 初始化完成", flush=True)
    sys.stdout.flush()

    # 3. 清除旧数据
    print("\n🧹 清除旧缓存...")
    sys.stdout.flush()
    processor.clear_cache()

    # 4. 构建索引 (这将触发 AI 仲裁)
    print("\n⚙️  开始计算...")
    sys.stdout.flush()
    start_time = time.time()
    
    print("   [步骤 1/4] 加载数据并计算 Category 质心...")
    sys.stdout.flush()
    print("   [步骤 2/4] 向量化数据（使用 GPU 加速）...")
    sys.stdout.flush()
    
    try:
        metadata, embeddings = processor.build_index(
            limit=None,  # 处理所有数据
            force_rebuild=True  # 强制重建
        )
        print(f"✅ 向量化完成 ({len(metadata)} 条记录)")
        print(f"   耗时: {time.time() - start_time:.2f} 秒")
        sys.stdout.flush()
    except Exception as e:
        print(f"❌ 索引构建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 5. 计算 UMAP
    print("\n🗺️  计算 Supervised UMAP 坐标...")
    sys.stdout.flush()
    try:
        # 加载刚刚生成的 embeddings 和 metadata
        meta, embeddings = processor.load_index()
        
        # 提取用于监督学习的标签（UCS主类别名称）
        # 关键：从 CatID（如 AMBFORST）映射到主类别名称（如 AMBIENCE），确保按82个主类别聚类
        targets = []
        missing_count = 0
        
        # 确保 ucs_manager 已初始化
        if not processor.ucs_manager:
            print("   [警告] UCSManager 未初始化，无法进行主类别映射")
            sys.stdout.flush()
        
        for m in meta:
            # metadata 的 'category' 字段存储的是 CatID（如 "AMBFORST"）
            raw_cat = m.get('category', '') if isinstance(m, dict) else getattr(m, 'category', '')
            
            if not raw_cat or raw_cat == '' or raw_cat == 'UNCATEGORIZED':
                # 缺失类别：标记为 "UNCATEGORIZED"，后续将编码为 -1
                targets.append("UNCATEGORIZED")
                missing_count += 1
                continue
            
            # 使用 UCSManager 将 CatID 映射到主类别名称
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
        print(f"✅ [Supervision] Unique Main Categories found: {len(unique_cats)}")
        if len(unique_cats) > 100:
            print(f"⚠️  [警告] 唯一类别数过多 ({len(unique_cats)})，可能仍在使用 CatID 而非主类别名称")
        elif len(unique_cats) < 5:
            print(f"⚠️  [警告] 分类过少 ({len(unique_cats)})，请检查 AI 仲裁逻辑")
        else:
            print(f"📋 Sample Labels: {list(sorted(unique_cats))[:15]}")
        
        if missing_count > 0:
            print(f"   [统计] 缺失类别数量: {missing_count} (已标记为 -1)")
        sys.stdout.flush()

        # 【超级锚点策略】向量注入：将主类别的One-Hot向量注入到音频embedding中
        print("   ⚓ 正在实施超级锚点策略 (Super-Anchor Strategy)...", flush=True)
        print("   强制同一主类别的数据聚集，解决'大陆漂移'问题...", flush=True)
        injection_params = umap_config.get_injection_params()
        X_combined, _ = inject_category_vectors(
            embeddings=embeddings,
            target_labels=targets_original,  # 使用原始字符串列表，避免-1陷阱
            audio_weight=injection_params['audio_weight'],
            category_weight=injection_params['category_weight']
        )
        print(f"   ✅ 向量注入完成: {embeddings.shape} -> {X_combined.shape}", flush=True)
        print(f"   音频权重: {injection_params['audio_weight']}, 类别锚点权重: {injection_params['category_weight']}", flush=True)
        sys.stdout.flush()

        # 从统一配置获取UMAP参数
        umap_params = umap_config.get_umap_params()
        reducer = umap.UMAP(**umap_params)
        
        print("   [进度] 正在运行 UMAP fit_transform（这可能需要几分钟）...")
        print("   [提示] UMAP 会显示详细的计算进度信息")
        sys.stdout.flush()
        
        # 记录开始时间
        umap_start = time.time()
        # 使用注入后的混合向量（X_combined）替代原始embeddings
        coords_2d = reducer.fit_transform(X_combined, y=targets_encoded)
        umap_elapsed = time.time() - umap_start
        
        print(f"   ✅ UMAP 计算完成（耗时 {umap_elapsed:.1f} 秒）")
        sys.stdout.flush()
        
        # 归一化
        min_coords = coords_2d.min(axis=0)
        max_coords = coords_2d.max(axis=0)
        scale = 3000.0 / (np.max(max_coords - min_coords) + 1e-5)
        coords_2d = (coords_2d - min_coords) * scale
        
        processor.save_coordinates(coords_2d)
        print("✅ 坐标计算完成并保存")
        sys.stdout.flush()

    except Exception as e:
        print(f"❌ UMAP 计算失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 6. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("✅ 重建完成！现在请运行 python main.py")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    print("=" * 60)

if __name__ == "__main__":
    # 立即输出，确保用户能看到脚本开始运行
    print("[启动] rebuild_atlas.py 开始运行...", flush=True)
    sys.stdout.flush()
    try:
        rebuild()
    except KeyboardInterrupt:
        print("\n[中断] 用户中断了脚本执行", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 脚本执行失败: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)
