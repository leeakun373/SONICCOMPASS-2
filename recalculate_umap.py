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
from core import DataProcessor, VectorEngine, inject_category_vectors, umap_config


def recalculate_umap():
    """仅重新计算UMAP坐标（使用现有向量缓存）"""
    print("=" * 60)
    print("🔄 Sonic Compass: 重新计算UMAP坐标 (Recalculate UMAP Only)")
    print("=" * 60)
    
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
    
    # 【超级锚点策略】向量注入：将主类别的One-Hot向量注入到音频embedding中
    print("\n⚓ 正在实施超级锚点策略 (Super-Anchor Strategy)...")
    print("   强制同一主类别的数据聚集，解决'大陆漂移'问题...")
    injection_params = umap_config.get_injection_params()
    X_combined, _ = inject_category_vectors(
        embeddings=embeddings,
        target_labels=targets_original,  # 使用原始字符串列表，避免-1陷阱
        audio_weight=injection_params['audio_weight'],
        category_weight=injection_params['category_weight']
    )
    print(f"   ✅ 向量注入完成: {embeddings.shape} -> {X_combined.shape}")
    print(f"   音频权重: {injection_params['audio_weight']}, 类别锚点权重: {injection_params['category_weight']}")
    
    # 6. Phase 3.5: 计算 Supervised UMAP 坐标（使用超级锚点策略）
    print("\n🗺️  计算 Supervised UMAP 坐标（使用超级锚点策略）...")
    print(f"   数据量: {len(embeddings)} 条，混合向量维度: {X_combined.shape[1]}")
    print(f"   标签数量: {len(set(targets_original)) - (1 if 'UNCATEGORIZED' in targets_original else 0)} 个唯一类别")
    print("   ⏳ 这可能需要几分钟，请耐心等待...")
    import sys
    sys.stdout.flush()  # 强制刷新输出
    
    coord_start = time.time()
    
    try:
        # 从统一配置获取UMAP参数
        umap_params = umap_config.get_umap_params()
        reducer = umap.UMAP(**umap_params)
        print("   [进度] 正在运行 UMAP fit_transform（这可能需要几分钟）...")
        print(f"   [信息] 数据量: {len(embeddings)} 条，向量维度: {embeddings.shape[1]}")
        if isinstance(targets, (list, np.ndarray)):
            unique_labels = len(set(targets)) if len(targets) < 100000 else "大量"
            print(f"   [信息] 标签数量: {unique_labels} 个唯一类别")
        print("   [提示] UMAP verbose 输出会显示在标准错误流（stderr）中")
        print("   [提示] 如果长时间无输出，UMAP 可能正在计算中，请耐心等待...")
        print("   [开始] 开始计算 UMAP...")
        sys.stdout.flush()
        sys.stderr.flush()  # 也刷新 stderr，因为 UMAP 的 verbose 输出到 stderr
        
        # 记录开始时间
        umap_start = time.time()
        start_time_str = time.strftime('%H:%M:%S')
        print(f"   [时间] 开始时间: {start_time_str}")
        sys.stdout.flush()
        
        try:
            # 【修复】检查 targets 格式
            print(f"   [检查] targets 类型: {type(targets)}, 长度: {len(targets) if hasattr(targets, '__len__') else 'N/A'}")
            if isinstance(targets, np.ndarray):
                print(f"   [检查] targets 形状: {targets.shape}, dtype: {targets.dtype}")
                print(f"   [检查] targets 范围: min={targets.min()}, max={targets.max()}")
                nan_targets = np.sum(~np.isfinite(targets))
                if nan_targets > 0:
                    print(f"   ⚠️  [警告] targets 包含 {nan_targets} 个无效值")
            elif isinstance(targets, list):
                unique_targets = len(set(targets))
                print(f"   [检查] targets 唯一值数量: {unique_targets}")
            
            # 【修复】确保 targets 是 numpy 数组
            if not isinstance(targets, np.ndarray):
                targets = np.array(targets)
            
            # 【修复】检查 embeddings
            print(f"   [检查] embeddings 形状: {embeddings.shape}, dtype: {embeddings.dtype}")
            nan_embeddings = np.sum(~np.isfinite(embeddings))
            if nan_embeddings > 0:
                print(f"   ⚠️  [警告] embeddings 包含 {nan_embeddings} 个无效值")
            
            sys.stdout.flush()
            
            # UMAP 的 verbose 输出会到 stderr，所以我们需要确保 stderr 也被刷新
            print("   [开始] 调用 UMAP fit_transform...")
            print(f"   [参数] n_neighbors={reducer.n_neighbors}, target_weight={reducer.target_weight}")
            print("   [提示] UMAP 计算可能需要 5-10 分钟（大数据集），请耐心等待...")
            print("   [提示] 每 30 秒会输出一次心跳，证明程序仍在运行")
            print("   [提示] UMAP 的详细进度会显示在 stderr 中（可能不会立即显示）")
            print("   [提示] 如果超过 15 分钟无响应，可以按 Ctrl+C 中断，然后降低 n_neighbors 参数（如改为 50）")
            sys.stdout.flush()
            sys.stderr.flush()
            
            # 在后台线程中定期输出心跳（防止看起来卡住）
            import threading
            import time as time_module
            heartbeat_running = [True]
            
            def heartbeat():
                """定期输出心跳，证明程序还在运行"""
                count = 0
                while heartbeat_running[0]:
                    time_module.sleep(30)  # 每30秒输出一次
                    if heartbeat_running[0]:
                        count += 1
                        elapsed = time_module.time() - umap_start
                        print(f"   [心跳 #{count}] 仍在计算中... 已耗时 {elapsed/60:.1f} 分钟", flush=True)
                        sys.stdout.flush()
            
            heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
            heartbeat_thread.start()
            
            try:
                # 使用注入后的混合向量（X_combined）替代原始embeddings
                coords_2d = reducer.fit_transform(X_combined, y=targets)
            finally:
                heartbeat_running[0] = False
        except Exception as e:
            print(f"   ❌ UMAP 计算出错: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        umap_elapsed = time.time() - umap_start
        end_time_str = time.strftime('%H:%M:%S')
        print(f"   ✅ UMAP 计算完成")
        print(f"   [时间] 结束时间: {end_time_str}，耗时: {umap_elapsed:.1f} 秒 ({umap_elapsed/60:.1f} 分钟)")
        
        # 【修复】检查 UMAP 返回的坐标是否有效
        print(f"   [检查] UMAP 返回坐标形状: {coords_2d.shape}")
        print(f"   [检查] 坐标范围（归一化前）: min={coords_2d.min(axis=0)}, max={coords_2d.max(axis=0)}")
        
        # 检查是否有 NaN 或 Inf
        nan_count = np.sum(~np.isfinite(coords_2d))
        if nan_count > 0:
            print(f"   ⚠️  [警告] UMAP 返回的坐标包含 {nan_count} 个无效值（NaN/Inf）")
            nan_indices = np.where(~np.isfinite(coords_2d).any(axis=1))[0]
            print(f"   [调试] 无效值位置（前10个）: {nan_indices[:10]}")
            
            # 【改进修复】不是简单替换为 0，而是使用有效坐标的均值或随机分布
            valid_mask = np.isfinite(coords_2d).all(axis=1)
            if np.sum(valid_mask) > 0:
                # 使用有效坐标的中心点作为默认位置
                valid_coords = coords_2d[valid_mask]
                center = valid_coords.mean(axis=0)
                std = valid_coords.std(axis=0)
                
                # 为 NaN 点生成随机位置（在有效坐标范围内）
                for idx in nan_indices:
                    # 在中心附近随机分布，避免全部聚集在原点
                    coords_2d[idx] = center + np.random.normal(0, std * 0.1, size=2)
                
                print(f"   [修复] 已将 {nan_count} 个 NaN/Inf 替换为有效坐标范围内的随机位置")
            else:
                # 如果全部无效，使用默认值
                coords_2d = np.nan_to_num(coords_2d, nan=0.0, posinf=0.0, neginf=0.0)
                print(f"   [修复] 所有坐标都无效，已替换为 0")
        
        sys.stdout.flush()
    except Exception as e:
        print(f"   ❌ UMAP 计算失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 坐标归一化到 0-3000 范围
    print("   [归一化] 开始归一化坐标...")
    sys.stdout.flush()
    
    min_coords = coords_2d.min(axis=0)
    max_coords = coords_2d.max(axis=0)
    coord_range = max_coords - min_coords
    
    print(f"   [归一化] 坐标范围: min={min_coords}, max={max_coords}, range={coord_range}")
    
    # 检查范围是否有效
    if np.any(~np.isfinite(min_coords)) or np.any(~np.isfinite(max_coords)):
        print(f"   ❌ [错误] 坐标范围包含无效值，无法归一化")
        print(f"   [调试] min_coords: {min_coords}, max_coords: {max_coords}")
        sys.exit(1)
    
    if np.any(coord_range <= 0) or not np.isfinite(np.max(coord_range)):
        print(f"   ⚠️  [警告] 坐标范围异常: {coord_range}")
        print(f"   [修复] 使用默认范围进行归一化")
        # 如果范围异常，使用默认范围
        scale = 3000.0
        coords_2d = (coords_2d - coords_2d.mean(axis=0)) * scale / (coords_2d.std(axis=0) + 1e-5)
    else:
        # 【改进】使用相同的缩放因子，保持纵横比，但确保两个轴都填满 0-3000 范围
        # 方法：使用最大范围作为基准，然后分别缩放两个轴
        max_range = np.max(coord_range)
        scale_x = 3000.0 / coord_range[0] if coord_range[0] > 0 else 3000.0 / max_range
        scale_y = 3000.0 / coord_range[1] if coord_range[1] > 0 else 3000.0 / max_range
        
        # 归一化到 0-3000
        coords_2d[:, 0] = (coords_2d[:, 0] - min_coords[0]) * scale_x
        coords_2d[:, 1] = (coords_2d[:, 1] - min_coords[1]) * scale_y
    
    # 再次检查归一化后的坐标
    print(f"   [归一化] 归一化后坐标范围: min={coords_2d.min(axis=0)}, max={coords_2d.max(axis=0)}")
    nan_count_after = np.sum(~np.isfinite(coords_2d))
    if nan_count_after > 0:
        print(f"   ❌ [错误] 归一化后仍有 {nan_count_after} 个无效值")
        sys.exit(1)
    
    sys.stdout.flush()
    
    # 保存坐标
    processor.save_coordinates(coords_2d)
    
    print(f"✅ 坐标计算完成")
    print(f"   耗时: {time.time() - coord_start:.2f} 秒")
    print(f"   坐标范围: [{coords_2d.min(axis=0)[0]:.1f}, {coords_2d.min(axis=0)[1]:.1f}] 到 [{coords_2d.max(axis=0)[0]:.1f}, {coords_2d.max(axis=0)[1]:.1f}]")
    
    # 7. 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✅ UMAP坐标重新计算完成！")
    print(f"   总耗时: {total_time:.2f} 秒")
    print(f"   数据量: {len(metadata)} 条记录")
    print(f"   坐标已保存至: {os.path.join(CACHE_DIR, 'coordinates.npy')}")
    print("=" * 60)
    print("\n👉 现在可以运行: python main.py")


if __name__ == "__main__":
    recalculate_umap()

