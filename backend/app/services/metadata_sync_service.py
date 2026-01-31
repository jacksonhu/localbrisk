"""
元数据同步服务
负责从外部数据库拉取元数据并保存到本地文件系统

设计原则：
1. 同步的表元数据统一使用 baseinfo 结构存储基础属性
2. 表特有的元数据与 baseinfo 同级存储
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

import yaml

from app.core.constants import TABLES_DIR, ASSET_FILE_SUFFIX
from app.models.catalog import ConnectionConfig
from app.models.metadata import SchemaMetadata, TableMetadata, SyncResult
from app.services.connectors import ConnectorFactory

logger = logging.getLogger(__name__)


class MetadataSyncService:
    """元数据同步服务"""
    
    def __init__(self, schema_path: Path, catalog_id: str, schema_name: str):
        self.schema_path = schema_path
        self.catalog_id = catalog_id
        self.schema_name = schema_name
    
    def sync_connection(self, connection: ConnectionConfig) -> SyncResult:
        """同步连接的元数据"""
        result = SyncResult()
        
        connector = ConnectorFactory.create(connection)
        if connector is None:
            result.success = False
            result.errors.append(f"不支持的连接类型: {connection.type}")
            return result
        
        try:
            if not connector.connect():
                result.success = False
                result.errors.append(f"无法连接到数据库: {connection.host}:{connection.port}")
                return result
            
            schemas_metadata = connector.get_full_metadata()
            
            # 查找目标 schema
            target_schema = None
            for schema_meta in schemas_metadata:
                if schema_meta.name == connection.db_name:
                    target_schema = schema_meta
                    break
            
            if not target_schema and schemas_metadata:
                target_schema = schemas_metadata[0]
            
            if not target_schema:
                result.warnings.append(f"数据库 '{connection.db_name}' 中没有找到可同步的表")
                return result
            
            # 设置 catalog 和 schema 名称
            target_schema.catalog_name = self.catalog_id
            for table in target_schema.tables:
                table.catalog_name = self.catalog_id
                table.schema_name = self.schema_name
            
            # 保存表元数据
            for table in target_schema.tables:
                self._save_table_metadata(table)
                result.tables_synced += 1
                result.columns_synced += len(table.columns)
            
            result.schemas_synced = 1
            
            logger.info(
                f"Schema '{self.schema_name}' 元数据同步完成: "
                f"{result.tables_synced} 张表, {result.columns_synced} 个字段"
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(f"同步过程发生错误: {str(e)}")
            logger.exception(f"同步元数据失败: {e}")
        finally:
            connector.disconnect()
        
        return result
    
    def _save_table_metadata(self, table_meta: TableMetadata) -> Path:
        """保存表元数据（使用 baseinfo 结构）"""
        tables_dir = self.schema_path / TABLES_DIR
        tables_dir.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now().isoformat()
        
        # 构建 baseinfo
        baseinfo = {
            "name": table_meta.name,
            "display_name": table_meta.name,
            "description": table_meta.comment or "",
            "tags": [],
            "owner": "admin",
            "created_at": table_meta.create_time.isoformat() if table_meta.create_time else now,
            "updated_at": table_meta.update_time.isoformat() if table_meta.update_time else now,
        }
        
        # 构建完整配置
        table_config = {
            "baseinfo": baseinfo,
            # 表特有元数据
            "schema_name": self.schema_name,
            "catalog_name": self.catalog_id,
            "table_type": table_meta.table_type,
            "engine": table_meta.engine,
            "row_count": table_meta.row_count,
            "data_length": table_meta.data_length,
            "primary_keys": table_meta.primary_keys,
            "source": "connection",
            "readonly": True,
            "columns": [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "default_value": col.default_value,
                    "is_primary_key": col.is_primary_key,
                    "is_auto_increment": col.is_auto_increment,
                    "is_unique": col.is_unique,
                    "comment": col.comment,
                    "ordinal_position": col.ordinal_position,
                }
                for col in table_meta.columns
            ],
            "indexes": table_meta.indexes,
            "foreign_keys": table_meta.foreign_keys,
        }
        
        table_path = tables_dir / f"{table_meta.name}{ASSET_FILE_SUFFIX}"
        self._write_yaml(table_path, table_config)
        logger.debug(f"保存表元数据: {table_path}")
        
        return table_path
    
    def _write_yaml(self, path: Path, data: dict) -> None:
        """写入 YAML 文件"""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    
    def load_table_metadata(self, table_name: str) -> Optional[dict]:
        """加载表元数据"""
        table_path = self.schema_path / TABLES_DIR / f"{table_name}{ASSET_FILE_SUFFIX}"
        
        if not table_path.exists():
            return None
        
        try:
            with open(table_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载表元数据失败 {table_path}: {e}")
            return None
    
    def get_synced_tables(self) -> List[str]:
        """获取已同步的表列表"""
        tables = []
        tables_dir = self.schema_path / TABLES_DIR
        
        if not tables_dir.exists():
            return tables
        
        for item in tables_dir.iterdir():
            if item.is_file() and item.suffix == ".yaml" and not item.name.startswith("."):
                table_meta = self.load_table_metadata(item.stem)
                if table_meta and table_meta.get("source") == "connection":
                    tables.append(item.stem)
        
        return tables
