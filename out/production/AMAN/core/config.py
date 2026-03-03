"""
应用配置模块
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 服务配置
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DEBUG: bool = True
    
    # 数据目录配置
    DATA_DIR: Path = Path.home() / ".localbrisk" / "data"
    
    # Catalogs 目录配置（基于文件系统的 Catalog 存储）
    CATALOGS_DIR: Path = Path.home() / ".localbrisk" / "App_Data" / "Catalogs"
    
    # DuckDB 配置
    DUCKDB_PATH: Path = Path.home() / ".localbrisk" / "localbrisk.db"
    
    class Config:
        env_prefix = "LOCALBRISK_"
        case_sensitive = True


# 全局配置实例
settings = Settings()

# 确保数据目录存在
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# 确保 Catalogs 目录存在
settings.CATALOGS_DIR.mkdir(parents=True, exist_ok=True)
