# Phase 1 技术总结文档

## 1. 项目文件结构

```
SonicCompass/
├── config_loader.py          # 配置加载模块
├── ucs_manager.py            # UCS分类系统管理器
├── importer.py               # Soundminer数据库导入器
├── vector_engine.py          # BGE-M3向量引擎
├── verify_pipeline.py        # 集成测试脚本
├── deploy_model.py           # 模型部署脚本
│
├── data_config/              # 配置文件目录
│   ├── axis_definitions.json  # 轴定义配置
│   ├── presets.json          # 预设配置
│   ├── pillars_data.csv      # 支柱概念数据
│   ├── ucs_catid_list.csv    # UCS分类列表
│   └── ucs_alias.csv         # UCS别名映射
│
├── models/                   # 模型目录
│   └── bge-m3/              # BGE-M3模型文件
│       ├── config.json
│       ├── model.safetensors
│       ├── tokenizer.json
│       └── ...
│
└── test_assets/              # 测试数据
    ├── Sonic.sqlite         # Soundminer测试数据库
    └── Nas_SoundLibrary.sqlite
```

## 2. 核心类（Classes）功能说明

### 2.1 ConfigManager (config_loader.py)

**功能**: 统一管理所有配置文件，提供结构化的数据访问接口。

**核心职责**:
- 加载 `axis_definitions.json`（音频特征轴定义）
- 加载 `presets.json`（预设风格配置）
- 加载 `pillars_data.csv`（支柱概念和关键词）
- 提供按ID/名称查询的便捷接口

**关键方法**:
- `load_all()`: 一次性加载所有配置文件
- `get_axis_by_id(axis_id)`: 根据ID获取轴定义
- `get_preset_by_name(name)`: 根据名称获取预设
- `get_all_keywords_for_pillars()`: 获取所有支柱关键词（用于语义向量生成）

### 2.2 UCSManager (ucs_manager.py)

**功能**: 管理UCS（Universal Category System）分类系统，实现CatID与完整分类名称的双向映射，以及别名解析。

**核心职责**:
- 构建 CatID ↔ FullCategory 双向映射字典
- 加载别名映射表，实现关键词到标准CatID的转换
- 提供分类搜索和查询功能

**关键方法**:
- `load_all()`: 加载UCS分类列表和别名映射
- `resolve_alias(keyword)`: 解析别名/关键词，返回标准CatID
- `get_category_by_catid(cat_id)`: 根据CatID获取完整分类信息
- `search_categories(query)`: 在分类系统中搜索

**数据结构**:
```python
@dataclass
class UCSCategory:
    category: str           # 主分类
    subcategory: str        # 子分类
    cat_id: str            # 分类ID
    cat_short: str          # 简短标识
    full_category: str      # 完整分类名称 (Category-SubCategory)
    # ... 其他字段
```

### 2.3 SoundminerImporter (importer.py)

**功能**: 从Soundminer数据库文件中提取音频元数据，并构建语义文本。

**核心职责**:
- 自动检测数据库表名（支持 `items`, `miner_embed_source_data`, `justinmetadata`）
- 提取核心字段：recID, filename, filepath, description, keywords, category
- 集成UCSManager处理分类和别名
- 构建 `semantic_text` 字段（合并文件名、描述、关键词和处理后的分类）

**关键方法**:
- `__init__(db_path, ucs_manager)`: 初始化，接收数据库路径（不硬编码）
- `detect_table_name()`: 自动检测可用的表名
- `import_all(limit)`: 导入所有音频元数据
- `_build_semantic_text()`: 构建语义文本字段

**数据结构**:
```python
@dataclass
class AudioMetadata:
    recID: int
    filename: str
    filepath: str
    description: str
    keywords: str
    category: str
    semantic_text: str  # 构建的语义文本
```

### 2.4 VectorEngine (vector_engine.py)

**功能**: 使用BGE-M3模型将文本转换为1024维向量。

**核心职责**:
- 加载BGE-M3模型（支持本地路径或HuggingFace模型名称）
- 自动检测计算设备（CUDA/MPS/CPU）
- 批量编码文本为向量
- 提供向量维度查询接口

**关键方法**:
- `__init__(model_path)`: 初始化向量引擎，默认路径 `./models/bge-m3`
- `encode_batch(texts, batch_size)`: 批量编码文本为向量
- `encode(text)`: 编码单个文本
- `get_embedding_dim()`: 获取向量维度（1024）

## 3. 关键函数代码片段

### 3.1 UCS别名解析 (ucs_manager.py)

```python
def resolve_alias(self, keyword: str) -> Optional[str]:
    """
    解析别名，返回标准CatID
    
    Args:
        keyword: 输入的关键词或别名（如 "Gun"）
        
    Returns:
        对应的标准CatID（如 "WPN"），如果未找到则返回None
    """
    if not keyword:
        return None
    
    keyword_lower = keyword.strip().lower()
    
    # 首先在别名映射中查找
    if keyword_lower in self.alias_to_catid:
        alias_result = self.alias_to_catid[keyword_lower]
        # 如果别名映射的值是简短名称，需要进一步查找
        if alias_result not in self.catid_to_category:
            resolved = self._find_catid_by_short_name(alias_result)
            if resolved:
                return resolved
        else:
            return alias_result
    
    # 尝试在CatID本身中查找
    if keyword in self.catid_to_category:
        return keyword
    
    # 尝试在同义词中查找
    for cat_id, category in self.catid_to_category.items():
        for synonym in category.synonyms:
            if synonym.lower() == keyword_lower:
                return cat_id
    
    return None
```

### 3.2 语义文本构建 (importer.py)

```python
def _build_semantic_text(self, row: sqlite3.Row, mapping: Dict[str, str]) -> str:
    """
    构建语义文本字段
    
    Args:
        row: 数据库行
        mapping: 字段映射
        
    Returns:
        构建的语义文本
    """
    parts = []
    
    # 添加文件名
    if mapping['filename']:
        filename = row[mapping['filename']]
        if filename:
            parts.append(str(filename))
    
    # 添加描述
    if mapping['description']:
        description = row[mapping['description']]
        if description:
            parts.append(str(description))
    
    # 添加关键词
    if mapping['keywords']:
        keywords = row[mapping['keywords']]
        if keywords:
            parts.append(str(keywords))
    
    # 添加处理后的分类（使用UCSManager处理）
    category = row[mapping['category']] if mapping['category'] else None
    keywords_str = row[mapping['keywords']] if mapping['keywords'] else None
    processed_category = self._process_category_with_ucs(category, keywords_str)
    if processed_category:
        parts.append(processed_category)
    
    return " ".join(parts)
```

### 3.3 批量向量编码 (vector_engine.py)

```python
def encode_batch(
    self,
    texts: List[str],
    batch_size: int = 32,
    show_progress: bool = True,
    normalize_embeddings: bool = True
) -> np.ndarray:
    """
    批量编码文本为向量
    
    Args:
        texts: 文本列表
        batch_size: 批处理大小
        show_progress: 是否显示进度条
        normalize_embeddings: 是否归一化向量
        
    Returns:
        numpy数组，形状为 (n_texts, embedding_dim)
    """
    if not texts:
        return np.array([])
    
    # 过滤空文本
    valid_texts = [text if text else "" for text in texts]
    
    # 使用模型编码
    embeddings = self.model.encode(
        valid_texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=normalize_embeddings,
        convert_to_numpy=True
    )
    
    return embeddings
```

### 3.4 表名自动检测 (importer.py)

```python
def detect_table_name(self) -> str:
    """
    自动检测表名
    
    Returns:
        检测到的表名
        
    Raises:
        ImporterError: 如果找不到有效的表
    """
    if self.conn is None:
        self.connect()
    
    cursor = self.conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0].lower() for row in cursor.fetchall()}
    
    # 按优先级查找表
    for table_name in self.POSSIBLE_TABLE_NAMES:
        if table_name.lower() in existing_tables:
            # 验证表是否包含必需的列
            if self._validate_table(table_name):
                self.table_name = table_name
                return table_name
    
    raise ImporterError(
        f"无法找到有效的表。已存在的表: {sorted(existing_tables)}。"
        f"期望的表名: {', '.join(self.POSSIBLE_TABLE_NAMES)}"
    )
```

## 4. 数据流向

```
SQLite 数据库
    ↓
SoundminerImporter.import_all()
    ↓
提取: recID, filename, filepath, description, keywords, category
    ↓
UCSManager.resolve_alias() 处理分类和关键词
    ↓
构建 semantic_text (文件名 + 描述 + 关键词 + UCS分类)
    ↓
VectorEngine.encode_batch()
    ↓
BGE-M3 模型编码
    ↓
Numpy Array (n_samples, 1024)
```

## 5. 已知限制条件

### 5.1 数据库兼容性

- **支持的表名**: 目前支持 `items`, `miner_embed_source_data`, `justinmetadata` 三种表名
- **必需字段**: 至少需要 `recid` 和 `filename` 列
- **字段映射**: 自动适配不同的列名（如 `filepath`/`pathname`/`file_path`）

### 5.2 UCS别名解析

- **优先级**: 别名映射 > CatID精确匹配 > CatShort匹配 > 同义词匹配
- **大小写**: 所有匹配默认不区分大小写
- **部分匹配**: 在同义词中支持部分匹配，可能返回多个结果中的第一个

### 5.3 向量引擎

- **模型要求**: 需要BGE-M3模型（1024维），模型文件约1.2GB
- **设备支持**: 自动检测CUDA/MPS/CPU，优先使用GPU加速
- **内存占用**: 模型加载后约占用2-3GB内存
- **批处理**: 默认batch_size=32，可根据显存调整

### 5.4 性能限制

- **数据库读取**: 单次读取速度取决于数据库大小和索引
- **向量编码**: CPU模式下约0.1秒/条，GPU模式下可提升10-50倍
- **内存占用**: 大规模批量处理时需要注意内存限制

### 5.5 编码问题

- **Windows控制台**: 某些特殊字符（如emoji）在GBK编码下可能无法显示
- **文件路径**: 支持Windows和Unix路径格式

### 5.6 依赖要求

- **必需库**:
  - `pandas`: CSV文件处理
  - `sentence-transformers`: 向量模型加载
  - `torch`: 深度学习框架
  - `numpy`: 数值计算
- **Python版本**: 建议Python 3.10+

## 6. 验证结果

通过 `verify_pipeline.py` 集成测试验证：

- ✅ ConfigManager: 9个轴定义, 11个预设, 78个支柱概念
- ✅ UCSManager: 754个分类, 1373个别名映射
- ✅ SoundminerImporter: 成功读取数据库，构建语义文本
- ✅ VectorEngine: 模型加载成功，向量维度1024
- ✅ 完整流水线: SQLite → UCS清洗 → Semantic Text → BGE-M3 → (5, 1024) 向量

**输出示例**:
```
[SUCCESS] 验证通过! 输出形状: (5, 1024) (5条数据, 1024维)
数据流向: SQLite -> UCS清洗 -> Semantic Text -> BGE-M3 -> Numpy Array
```

---

**文档版本**: Phase 1 Final  
**最后更新**: 2024-12-21

