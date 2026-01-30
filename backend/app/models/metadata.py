"""
数据库元数据模型
用于存储从外部数据库同步的元数据信息
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ColumnMetadata(BaseModel):
    """字段元数据"""
    name: str
    data_type: str  # 原始数据类型
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_auto_increment: bool = False
    is_unique: bool = False
    comment: Optional[str] = None
    ordinal_position: int = 0  # 字段在表中的位置
    character_max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class TableMetadata(BaseModel):
    """表元数据"""
    name: str
    schema_name: str
    catalog_name: str
    table_type: str = "BASE TABLE"  # BASE TABLE, VIEW, etc.
    engine: Optional[str] = None  # MySQL: InnoDB, MyISAM, etc.
    comment: Optional[str] = None
    row_count: Optional[int] = None
    data_length: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    columns: List[ColumnMetadata] = Field(default_factory=list)
    primary_keys: List[str] = Field(default_factory=list)
    indexes: List[Dict[str, Any]] = Field(default_factory=list)
    foreign_keys: List[Dict[str, Any]] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class SchemaMetadata(BaseModel):
    """Schema（数据库）元数据"""
    name: str
    catalog_name: str
    character_set: Optional[str] = None
    collation: Optional[str] = None
    comment: Optional[str] = None
    table_count: int = 0
    tables: List[TableMetadata] = Field(default_factory=list)
    synced_at: Optional[datetime] = None
    connection_type: str = "mysql"
    connection_host: Optional[str] = None
    connection_port: Optional[int] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class SyncResult(BaseModel):
    """元数据同步结果"""
    success: bool = True
    schemas_synced: int = 0
    tables_synced: int = 0
    columns_synced: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    synced_at: datetime = Field(default_factory=datetime.now)
