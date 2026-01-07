"""
文本归一化工具
用于统一处理文件名、关键词等文本，确保匹配的一致性
"""

import re
from typing import Optional


def normalize_text(text: str, remove_numbers: bool = False) -> str:
    """
    标准化文本用于匹配：
    1. 转小写
    2. 将下划线/连字符替换为空格
    3. 移除文件扩展名和版本号（如 '01', 'v2'）
    4. 保留单词之间的空格（关键：'metal door' vs 'metaldoor'）
    5. 去除首尾空白
    
    Args:
        text: 输入文本
        remove_numbers: 是否移除数字（默认 False，保留数字）
    
    Returns:
        归一化后的文本
    
    Examples:
        >>> normalize_text("Train_Horn-01.wav")
        'train horn 01'
        >>> normalize_text("Train_Horn-01.wav", remove_numbers=True)
        'train horn'
        >>> normalize_text("laser gun")
        'laser gun'
        >>> normalize_text("SCI-FI")
        'sci fi'
        >>> normalize_text("metal door")
        'metal door'
    """
    if not text:
        return ""
    
    # 转小写
    normalized = text.lower()
    
    # 移除文件扩展名（.wav, .mp3 等）
    normalized = re.sub(r'\.[a-z0-9]+$', '', normalized)
    
    # 将下划线和连字符替换为空格
    normalized = re.sub(r'[_-]', ' ', normalized)
    
    # 移除版本号模式（如 '01', 'v2', 'v1.0'）
    normalized = re.sub(r'\b(v\d+(?:\.\d+)?|\d+)\b', '', normalized)
    
    # 如果移除数字，移除所有数字
    if remove_numbers:
        normalized = re.sub(r'\d+', '', normalized)
    
    # 规范化空格（多个空格变为单个空格）
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # 去除首尾空白
    normalized = normalized.strip()
    
    return normalized


def normalize_keyword(keyword: str) -> str:
    """
    归一化关键词（用于规则匹配）
    
    这是 normalize_text 的别名，但语义更清晰
    
    Args:
        keyword: 关键词
    
    Returns:
        归一化后的关键词
    """
    return normalize_text(keyword, remove_numbers=False)


def extract_base_name(filename: str) -> str:
    """
    从文件名提取基础名称（去除扩展名和路径）
    
    Args:
        filename: 文件名（可能包含路径）
    
    Returns:
        基础名称（不含扩展名）
    
    Examples:
        >>> extract_base_name("Train_Horn-01.wav")
        'Train_Horn-01'
        >>> extract_base_name("/path/to/file.mp3")
        'file'
    """
    if not filename:
        return ""
    
    # 提取文件名（去除路径）
    base = filename.split('/')[-1].split('\\')[-1]
    
    # 去除扩展名
    if '.' in base:
        base = '.'.join(base.split('.')[:-1])
    
    return base


def normalize_filename(filename: str, remove_numbers: bool = False) -> str:
    """
    归一化文件名：提取基础名称并归一化
    
    Args:
        filename: 文件名（可能包含路径）
        remove_numbers: 是否移除数字
    
    Returns:
        归一化后的文件名
    
    Examples:
        >>> normalize_filename("Train_Horn-01.wav")
        'trainhorn01'
        >>> normalize_filename("Train_Horn-01.wav", remove_numbers=True)
        'trainhorn'
    """
    base_name = extract_base_name(filename)
    return normalize_text(base_name, remove_numbers=remove_numbers)

