"""
数据库配置模块
提供统一的数据库路径获取接口
"""

from pathlib import Path
from typing import Optional
from data.config_loader import ConfigManager


def get_database_path(default: str = "./test_assets/Sonic.sqlite") -> str:
    """
    获取数据库路径（从配置文件读取，如果不存在则使用默认值）
    
    Args:
        default: 默认数据库路径（如果配置文件不存在或未设置）
        
    Returns:
        数据库路径字符串
        
    Example:
        >>> db_path = get_database_path()
        >>> print(db_path)
        ./test_assets/Boom_Test_AlienLife.sqlite
    """
    try:
        config_manager = ConfigManager()
        config_manager.load_user_config()
        db_path = config_manager.get_database_path(default)
        
        # 验证路径是否存在
        if not Path(db_path).exists():
            print(f"[WARNING] 配置的数据库路径不存在: {db_path}")
            print(f"[WARNING] 使用默认路径: {default}")
            return default
        
        return db_path
    except Exception as e:
        print(f"[WARNING] 加载数据库配置失败: {e}")
        print(f"[WARNING] 使用默认路径: {default}")
        return default


if __name__ == "__main__":
    # 测试
    db_path = get_database_path()
    print(f"数据库路径: {db_path}")
    print(f"文件存在: {Path(db_path).exists()}")

