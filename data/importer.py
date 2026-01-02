"""
Soundminer 数据库导入器
从 Soundminer 数据库文件中提取音频元数据，并构建语义文本
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class AudioMetadata:
    """音频元数据"""
    recID: int
    filename: str
    filepath: str
    description: str
    keywords: str
    category: str
    semantic_text: str  # 构建的语义文本


class SoundminerImporter:
    """Soundminer 数据库导入器"""
    
    # 支持的表名（按优先级排序）
    SUPPORTED_TABLES = [
        'items',
        'miner_embed_source_data',
        'justinmetadata'
    ]
    
    # 字段映射（表名 -> 字段名）
    FIELD_MAPPINGS = {
        'items': {
            'recID': 'recID',
            'filename': 'filename',
            'filepath': 'filepath',
            'description': 'description',
            'keywords': 'keywords',
            'category': 'category'
        },
        'miner_embed_source_data': {
            'recID': 'recID',
            'filename': 'filename',
            'filepath': 'filepath',
            'description': 'description',
            'keywords': 'keywords',
            'category': 'category'
        },
        'justinmetadata': {
            'recID': 'recID',
            'filename': 'filename',
            'filepath': 'filepath',
            'description': 'description',
            'keywords': 'keywords',
            'category': 'category'
        }
    }
    
    def __init__(
        self,
        db_path: str,
        ucs_manager=None
    ):
        """
        初始化导入器
        
        Args:
            db_path: 数据库文件路径
            ucs_manager: UCSManager 实例（可选，用于处理分类）
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        self.ucs_manager = ucs_manager
        self.conn: Optional[sqlite3.Connection] = None
        self.table_name: Optional[str] = None
        self.field_mapping: Optional[Dict[str, str]] = None
    
    def _connect(self):
        """连接到数据库"""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
    
    def _detect_table_name(self) -> str:
        """自动检测可用的表名"""
        self._connect()
        cursor = self.conn.cursor()
        
        for table_name in self.SUPPORTED_TABLES:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if cursor.fetchone():
                return table_name
        
        raise ValueError(f"未找到支持的表，支持的表名: {self.SUPPORTED_TABLES}")
    
    def _process_category_with_ucs(self, category: Optional[str], keywords: Optional[str]) -> str:
        """
        使用 UCSManager 处理分类
        
        Args:
            category: 原始分类
            keywords: 关键词
            
        Returns:
            处理后的分类字符串
        """
        if not self.ucs_manager:
            return category or ""
        
        # 尝试从分类中解析
        if category:
            resolved = self.ucs_manager.resolve_alias(category)
            if resolved:
                return resolved
        
        # 尝试从关键词中解析
        if keywords:
            for keyword in keywords.split():
                resolved = self.ucs_manager.resolve_alias(keyword)
                if resolved:
                    return resolved
        
        return category or ""
    
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
        if mapping.get('filename'):
            filename = row[mapping['filename']]
            if filename:
                parts.append(str(filename))
        
        # 添加描述
        if mapping.get('description'):
            description = row[mapping['description']]
            if description:
                parts.append(str(description))
        
        # 添加关键词
        if mapping.get('keywords'):
            keywords = row[mapping['keywords']]
            if keywords:
                parts.append(str(keywords))
        
        # 添加处理后的分类（使用UCSManager处理）
        category = row[mapping['category']] if mapping.get('category') else None
        keywords_str = row[mapping['keywords']] if mapping.get('keywords') else None
        processed_category = self._process_category_with_ucs(category, keywords_str)
        if processed_category:
            parts.append(processed_category)
        
        return " ".join(parts)
    
    def import_all(self, limit: Optional[int] = None) -> List[AudioMetadata]:
        """
        导入所有音频元数据
        
        Args:
            limit: 限制导入的数量（用于测试）
            
        Returns:
            AudioMetadata 列表
        """
        self._connect()
        
        # 检测表名
        if self.table_name is None:
            self.table_name = self._detect_table_name()
            self.field_mapping = self.FIELD_MAPPINGS.get(self.table_name, {})
        
        # 构建查询
        query = f"SELECT * FROM {self.table_name}"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        results = []
        for row in cursor:
            # 提取字段
            recID = row[self.field_mapping['recID']] if self.field_mapping.get('recID') else None
            filename = row[self.field_mapping['filename']] if self.field_mapping.get('filename') else ""
            filepath = row[self.field_mapping['filepath']] if self.field_mapping.get('filepath') else ""
            description = row[self.field_mapping['description']] if self.field_mapping.get('description') else ""
            keywords = row[self.field_mapping['keywords']] if self.field_mapping.get('keywords') else ""
            category = row[self.field_mapping['category']] if self.field_mapping.get('category') else ""
            
            # 构建语义文本
            semantic_text = self._build_semantic_text(row, self.field_mapping)
            
            # 创建元数据对象
            metadata = AudioMetadata(
                recID=recID or 0,
                filename=filename or "",
                filepath=filepath or "",
                description=description or "",
                keywords=keywords or "",
                category=category or "",
                semantic_text=semantic_text
            )
            
            results.append(metadata)
        
        return results
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

