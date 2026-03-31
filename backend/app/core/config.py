"""
Application configuration module.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DEBUG: bool = True
    
    # Data directory configuration
    DATA_DIR: Path = Path.home() / ".localbrisk" / "data"
    
    # Catalogs directory configuration (filesystem-based Catalog storage)
    CATALOGS_DIR: Path = Path.home() / ".localbrisk" / "App_Data" / "Catalogs"
    
    # DuckDB configuration
    DUCKDB_PATH: Path = Path.home() / ".localbrisk" / "localbrisk.db"
    
    class Config:
        env_prefix = "LOCALBRISK_"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ensure Catalogs directory exists
settings.CATALOGS_DIR.mkdir(parents=True, exist_ok=True)
