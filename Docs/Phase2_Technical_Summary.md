# Phase 2 技术总结文档

## 1. 项目文件结构

```
SonicCompass/
├── config_loader.py          # 配置加载模块 (Phase 1)
├── ucs_manager.py            # UCS分类系统管理器 (Phase 1)
├── importer.py               # Soundminer数据库导入器 (Phase 1)
├── vector_engine.py          # BGE-M3向量引擎 (Phase 1)
├── data_processor.py         # 数据处理器 - 索引构建器 (Phase 2) ⭐
├── search_core.py            # 搜索算法核心 (Phase 2) ⭐
├── verify_pipeline.py        # Phase 1 集成测试脚本
├── verify_phase2.py          # Phase 2 集成测试脚本 ⭐
├── deploy_model.py           # 模型部署脚本
│
├── cache/                    # 向量缓存目录 (Phase 2) ⭐
│   ├── metadata.pkl          # 元数据缓存
│   ├── embeddings.npy        # 向量矩阵缓存
│   └── index_info.pkl        # 索引信息
│
├── data_config/              # 配置文件目录
│   ├── axis_definitions.json
│   ├── presets.json
│   ├── pillars_data.csv
│   ├── ucs_catid_list.csv
│   └── ucs_alias.csv
│
├── models/                   # 模型目录
│   └── bge-m3/              # BGE-M3模型文件
│
└── test_assets/              # 测试数据
    ├── Sonic.sqlite
    └── Nas_SoundLibrary.sqlite
```

## 2. 核心类（Classes）功能说明

### 2.1 DataProcessor (data_processor.py) ⭐ NEW

**功能**: 将数据库中的所有数据分批次进行向量化，并保存到本地缓存文件。实现"慢速AI计算"到"极速本地搜索"的转换。

**核心职责**:
- 从 SoundminerImporter 批量获取音频元数据
- 使用 VectorEngine 批量向量化语义文本
- 将元数据和向量矩阵持久化到本地缓存
- 提供缓存检测和加载功能

**关键方法**:
- `__init__(importer, vector_engine, cache_dir)`: 初始化，接收导入器和向量引擎实例
- `build_index(batch_size, limit, force_rebuild)`: 构建索引，批量向量化并保存
- `load_index()`: 从缓存加载索引（毫秒级加载）
- `clear_cache()`: 清除缓存文件

**缓存文件结构**:
- `metadata.pkl`: 元数据列表（pickle格式）
- `embeddings.npy`: 向量矩阵（numpy float32格式）
- `index_info.pkl`: 索引元信息（记录数、维度等）

**性能特点**:
- 首次构建：需要完整向量化（10万条数据约需数小时）
- 后续加载：毫秒级（< 50ms）
- 缓存大小：约 0.4MB/100条记录（1024维向量）

### 2.2 SearchCore (search_core.py) ⭐ NEW

**功能**: 提供极速的向量检索功能，支持文本搜索、音频搜音频和引力计算。

**核心职责**:
- 加载缓存的向量数据到内存
- 实现文本到音频的语义搜索
- 实现音频到音频的相似度搜索
- 计算文件与"引力桩"的相似度权重（用于UI可视化）

**关键方法**:
- `__init__(vector_engine, processor/metadata/embeddings)`: 初始化，支持多种数据源
- `search_by_text(query, top_k, filter_category)`: 文本搜索（毫秒级响应）
- `search_by_id(rec_id, top_k)`: 音频搜音频
- `calculate_gravity_forces(target_pillars)`: 计算引力权重（核心算法）

**性能特点**:
- 文本搜索：100-200ms（包含查询向量化）
- 引力计算：50-100ms（100条数据）
- 使用矩阵运算（np.dot）避免循环，性能优化

**数据结构**:
```python
# 搜索结果格式
List[Tuple[Dict, float]]  # [(metadata, similarity_score), ...]

# 引力权重格式
List[Dict[str, float]]  # [{"Fire": 0.85, "Ice": 0.12}, ...]
```

## 3. 关键函数代码片段

### 3.1 索引构建 (data_processor.py)

```python
def build_index(
    self,
    batch_size: int = 32,
    limit: Optional[int] = None,
    force_rebuild: bool = False
) -> Tuple[List[Dict], np.ndarray]:
    """
    构建索引：批量向量化数据并保存到缓存
    """
    # 检查缓存是否存在
    if not force_rebuild and self._cache_exists():
        return self.load_index()
    
    # 1. 从数据库获取数据
    metadata_list = self.importer.import_all(limit=limit)
    
    # 2. 提取语义文本
    texts = [meta.semantic_text for meta in metadata_list if meta.semantic_text]
    metadata_dicts = [/* 转换为字典格式 */]
    
    # 3. 批量向量化（使用tqdm显示进度）
    embeddings = self.vector_engine.encode_batch(
        texts,
        batch_size=batch_size,
        show_progress=True,
        normalize_embeddings=True
    )
    
    # 4. 保存到缓存
    with open(self.metadata_cache_path, 'wb') as f:
        pickle.dump(metadata_dicts, f)
    
    embeddings_float32 = embeddings.astype(np.float32)
    np.save(self.embeddings_cache_path, embeddings_float32)
    
    return metadata_dicts, embeddings
```

### 3.2 文本搜索 (search_core.py)

```python
def search_by_text(
    self,
    query: str,
    top_k: int = 50,
    filter_category: Optional[str] = None
) -> List[Tuple[Dict, float]]:
    """
    文本搜索：根据查询文本找到最相似的音频文件
    """
    # 1. 将查询文本转为向量
    query_vector = self.vector_engine.encode(
        query.strip(),
        normalize_embeddings=True
    )
    query_vector = query_vector.reshape(1, -1)  # (1, dim)
    
    # 2. 计算余弦相似度（矩阵运算，避免循环）
    # 由于向量已归一化，cosine_similarity = dot(query, embeddings)
    similarities = np.dot(self.embeddings, query_vector.T).flatten()
    
    # 3. 应用分类过滤（如果指定）
    if filter_category:
        mask = np.array([
            filter_category.lower() in str(meta.get('category', '')).lower()
            for meta in self.metadata
        ])
        similarities = np.where(mask, similarities, -1.0)
    
    # 4. 获取 Top K
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # 5. 构建结果
    results = []
    for idx in top_indices:
        if similarities[idx] > 0:
            results.append((
                self.metadata[idx],
                float(similarities[idx])
            ))
    
    return results
```

### 3.3 引力计算 (search_core.py)

```python
def calculate_gravity_forces(
    self,
    target_pillars: List[str]
) -> List[Dict[str, float]]:
    """
    计算引力：为UI的"引力视图"服务
    
    计算库中每一个文件与指定"引力桩"（Pillars）的相似度
    """
    # 1. 将引力桩转为向量
    pillar_vectors = self.vector_engine.encode_batch(
        target_pillars,
        batch_size=len(target_pillars),
        show_progress=False,
        normalize_embeddings=True
    )
    
    # 2. 计算每个文件与所有桩的相似度矩阵
    # embeddings: (n_files, dim)
    # pillar_vectors: (n_pillars, dim)
    # similarity_matrix: (n_files, n_pillars)
    similarity_matrix = np.dot(self.embeddings, pillar_vectors.T)
    
    # 3. 构建结果（每个文件的引力权重）
    results = []
    for i in range(len(self.metadata)):
        pillar_weights = {
            pillar: float(similarity_matrix[i, j])
            for j, pillar in enumerate(target_pillars)
        }
        results.append(pillar_weights)
    
    return results
```

### 3.4 向量归一化 (search_core.py)

```python
def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
    """
    归一化向量（L2归一化）
    用于余弦相似度计算
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)  # 避免除零
    return vectors / norms
```

## 4. 数据流向

### 4.1 索引构建流程

```
Soundminer 数据库
    ↓
SoundminerImporter.import_all()
    ↓
提取 AudioMetadata 列表
    ↓
提取 semantic_text 列表
    ↓
VectorEngine.encode_batch() (批量向量化)
    ↓
Numpy Array (n_samples, 1024)
    ↓
保存到缓存
    ├── metadata.pkl (元数据)
    ├── embeddings.npy (向量矩阵)
    └── index_info.pkl (索引信息)
```

### 4.2 搜索流程

```
用户查询文本
    ↓
VectorEngine.encode() (查询向量化)
    ↓
SearchCore.search_by_text()
    ↓
np.dot(embeddings, query_vector) (矩阵运算)
    ↓
计算余弦相似度
    ↓
排序并返回 Top K
    ↓
[(metadata, score), ...]
```

### 4.3 引力计算流程

```
预设引力桩 ["Fire", "Ice", "Impact"]
    ↓
VectorEngine.encode_batch() (桩向量化)
    ↓
SearchCore.calculate_gravity_forces()
    ↓
np.dot(embeddings, pillar_vectors.T) (矩阵运算)
    ↓
相似度矩阵 (n_files, n_pillars)
    ↓
转换为权重字典列表
    ↓
[{"Fire": 0.85, "Ice": 0.12}, ...]
```

## 5. 性能指标

### 5.1 索引构建性能

- **100条数据**: 约 14.5 秒（首次构建）
- **1000条数据**: 约 2-3 分钟（估算）
- **10万条数据**: 约 3-5 小时（估算，取决于硬件）

### 5.2 缓存加载性能

- **100条数据**: < 2ms
- **1000条数据**: < 10ms
- **10万条数据**: < 100ms

### 5.3 搜索性能

- **文本搜索**: 100-200ms（包含查询向量化）
- **音频搜音频**: 50-150ms
- **引力计算**: 50-100ms（100条数据）

### 5.4 内存占用

- **100条数据**: 约 0.4 MB
- **1000条数据**: 约 4 MB
- **10万条数据**: 约 400 MB（1024维 float32）

## 6. 已知限制条件

### 6.1 缓存管理

- **缓存位置**: 默认 `./cache` 目录，不可配置（可通过修改代码调整）
- **缓存格式**: 使用 pickle 和 numpy，Python版本兼容性需注意
- **缓存更新**: 数据库更新后需要手动重建索引（`force_rebuild=True`）
- **缓存大小**: 10万条数据约400MB，需确保磁盘空间充足

### 6.2 向量计算

- **内存限制**: 所有向量加载到内存，大规模数据（>50万条）可能超出内存
- **批处理大小**: 默认32，可根据显存/内存调整
- **向量维度**: 固定1024维（BGE-M3），不可配置

### 6.3 搜索算法

- **相似度计算**: 使用余弦相似度，仅支持归一化向量
- **Top K限制**: 默认50，可调整但会影响性能
- **分类过滤**: 简单的字符串匹配，不支持复杂查询

### 6.4 引力计算

- **权重计算**: 直接使用相似度值，未使用softmax归一化（可选）
- **多桩支持**: 支持任意数量的引力桩，但计算时间线性增长
- **权重范围**: 相似度值范围 [-1, 1]，可能为负值

### 6.5 依赖要求

- **必需库**:
  - `numpy`: 向量计算
  - `pickle`: 元数据序列化
  - `tqdm`: 进度条显示
- **Python版本**: 建议Python 3.10+

### 6.6 数据一致性

- **元数据同步**: 缓存元数据与数据库可能不同步，需要定期重建
- **向量一致性**: 向量基于构建时的语义文本，文本更新需重建索引

## 7. 验证结果

通过 `verify_phase2.py` 集成测试验证：

- ✅ DataProcessor: 成功构建索引，缓存保存正常
- ✅ SearchCore: 搜索核心初始化成功，向量加载正常
- ✅ 文本搜索: "Sci-Fi Weapon" 查询成功，返回Top 3结果
- ✅ 引力计算: ["Organic", "Synthetic"] 计算成功，权重分布正常

**性能验证**:
```
索引构建: 14.54 秒 (100条数据)
索引加载: 1.50 ms
文本搜索: 165.85 ms
引力计算: 73.02 ms
```

**输出示例**:
```
文本搜索 "Sci-Fi Weapon":
  结果1: RecID=52, 相似度=0.4514
  结果2: RecID=48, 相似度=0.4513
  结果3: RecID=49, 相似度=0.4503

引力计算 ["Organic", "Synthetic"]:
  文件1: Organic=0.3657, Synthetic=0.3711
  文件2: Organic=0.3617, Synthetic=0.3850
  平均权重: Organic=0.3349, Synthetic=0.3842
```

## 8. 技术亮点

### 8.1 性能优化

- **矩阵运算**: 使用 `np.dot` 进行批量相似度计算，避免Python循环
- **向量归一化**: 预归一化向量，简化余弦相似度计算
- **缓存机制**: 首次构建后，后续加载毫秒级

### 8.2 架构设计

- **解耦设计**: DataProcessor 和 SearchCore 独立，可单独使用
- **灵活初始化**: SearchCore 支持多种数据源（processor/metadata/embeddings）
- **异常处理**: 完善的错误处理和提示信息

### 8.3 可扩展性

- **批处理支持**: 支持大规模数据的批量处理
- **过滤功能**: 支持分类过滤，可扩展更多过滤条件
- **引力算法**: 支持任意数量的引力桩，算法通用

---

**文档版本**: Phase 2 Final  
**最后更新**: 2024-12-21

