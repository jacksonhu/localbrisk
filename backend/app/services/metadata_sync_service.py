"""
元数据同步服务
负责从外部数据库拉取元数据并保存到本地文件系统
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

import yaml

from app.core.constants import (
    SCHEMA_CONFIG_FILE,
    ASSET_FILE_SUFFIX,
    TABLES_DIR,
    VOLUMES_DIR,
    FUNCTIONS_DIR,
    MODELS_DIR,
    AGENTS_DIR,
    NOTES_DIR,
)
from app.models.catalog import ConnectionConfig
from app.models.metadata import SchemaMetadata, TableMetadata, SyncResult
from app.services.connectors import ConnectorFactory

logger = logging.getLogger(__name__)


class MetadataSyncService:
    """
    元数据同步服务
    从外部数据库读取元数据并保存为本地 YAML 文件
    """
    
    def __init__(self, catalog_path: Path, catalog_id: str):
        """
        初始化同步服务
        
        Args:
            catalog_path: Catalog 文件夹路径
            catalog_id: Catalog ID
        """
        self.catalog_path = catalog_path
        self.catalog_id = catalog_id
    
    def sync_connection(self, connection: ConnectionConfig) -> SyncResult:
        """
        同步单个连接的元数据
        
        Args:
            connection: 连接配置
            
        Returns:
            SyncResult 同步结果
        """
        result = SyncResult()
        
        # 如果不需要同步 Schema，直接返回
        if not connection.sync_schema:
            logger.info(f"连接 {connection.db_name} 配置为不同步 Schema")
            return result
        
        # 创建连接器
        connector = ConnectorFactory.create(connection)
        if connector is None:
            result.success = False
            result.errors.append(f"不支持的连接类型: {connection.type}")
            return result
        
        try:
            # 建立连接
            if not connector.connect():
                result.success = False
                result.errors.append(f"无法连接到数据库: {connection.host}:{connection.port}")
                return result
            
            # 获取完整的元数据
            schemas_metadata = connector.get_full_metadata()
            
            for schema_meta in schemas_metadata:
                try:
                    # 设置 catalog 名称
                    schema_meta.catalog_name = self.catalog_id
                    for table in schema_meta.tables:
                        table.catalog_name = self.catalog_id
                    
                    # 保存 Schema 元数据到本地
                    self._save_schema_metadata(schema_meta)
                    result.schemas_synced += 1
                    result.tables_synced += len(schema_meta.tables)
                    
                    for table in schema_meta.tables:
                        result.columns_synced += len(table.columns)
                    
                except Exception as e:
                    error_msg = f"保存 Schema '{schema_meta.name}' 元数据失败: {e}"
                    logger.error(error_msg)
                    result.warnings.append(error_msg)
            
            logger.info(
                f"元数据同步完成: {result.schemas_synced} 个 Schema, "
                f"{result.tables_synced} 张表, {result.columns_synced} 个字段"
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(f"同步过程发生错误: {str(e)}")
            logger.exception(f"同步元数据失败: {e}")
        finally:
            connector.disconnect()
        
        return result
    
    def sync_all_connections(self, connections: List[ConnectionConfig]) -> SyncResult:
        """
        同步所有连接的元数据
        
        Args:
            connections: 连接配置列表
            
        Returns:
            合并的 SyncResult
        """
        total_result = SyncResult()
        
        for connection in connections:
            if not connection.sync_schema:
                continue
            
            logger.info(f"开始同步连接: {connection.type}://{connection.host}:{connection.port}/{connection.db_name}")
            result = self.sync_connection(connection)
            
            # 合并结果
            total_result.schemas_synced += result.schemas_synced
            total_result.tables_synced += result.tables_synced
            total_result.columns_synced += result.columns_synced
            total_result.errors.extend(result.errors)
            total_result.warnings.extend(result.warnings)
            
            if not result.success:
                total_result.success = False
        
        return total_result
    
    def _save_schema_metadata(self, schema_meta: SchemaMetadata) -> Path:
        """
        保存 Schema 元数据到本地文件系统
        
        在 catalog 目录下创建 schema 目录，并生成：
        - schema.yaml: Schema 元数据
        - tables/{table_name}.yaml: 每张表的元数据
        
        Args:
            schema_meta: Schema 元数据
            
        Returns:
            Schema 目录路径
        """
        # 创建 Schema 目录
        schema_dir = self.catalog_path / schema_meta.name
        schema_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 Schema 元数据（不包含表详情）
        schema_meta_dict = {
            "name": schema_meta.name,
            "catalog_name": schema_meta.catalog_name,
            "source": "connection",
            "connection_type": schema_meta.connection_type,
            "connection_host": schema_meta.connection_host,
            "connection_port": schema_meta.connection_port,
            "character_set": schema_meta.character_set,
            "collation": schema_meta.collation,
            "comment": schema_meta.comment,
            "table_count": schema_meta.table_count,
            "synced_at": schema_meta.synced_at.isoformat() if schema_meta.synced_at else datetime.now().isoformat(),
            "readonly": True,  # 外部连接的 Schema 是只读的
        }
        
        schema_meta_path = schema_dir / SCHEMA_CONFIG_FILE
        self._write_yaml(schema_meta_path, schema_meta_dict)
        logger.debug(f"保存 Schema 元数据: {schema_meta_path}")
        
        # 保存每张表的元数据
        for table_meta in schema_meta.tables:
            self._save_table_metadata(schema_dir, table_meta)
        
        return schema_dir
    
    def _save_table_metadata(self, schema_dir: Path, table_meta: TableMetadata) -> Path:
        """
        保存表元数据到 YAML 文件
        表元数据保存在 schema_dir/tables/{table_name}.yaml
        
        Args:
            schema_dir: Schema 目录路径
            table_meta: 表元数据
            
        Returns:
            表元数据文件路径
        """
        # 创建 tables 子目录
        tables_dir = schema_dir / TABLES_DIR
        tables_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成表元数据字典
        table_meta_dict = {
            "name": table_meta.name,
            "schema_name": table_meta.schema_name,
            "catalog_name": table_meta.catalog_name,
            "table_type": table_meta.table_type,
            "engine": table_meta.engine,
            "comment": table_meta.comment,
            "row_count": table_meta.row_count,
            "data_length": table_meta.data_length,
            "create_time": table_meta.create_time.isoformat() if table_meta.create_time else None,
            "update_time": table_meta.update_time.isoformat() if table_meta.update_time else None,
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
        
        # 表文件名：tables/{table_name}.yaml
        table_file_name = f"{table_meta.name}{ASSET_FILE_SUFFIX}"
        table_meta_path = tables_dir / table_file_name
        self._write_yaml(table_meta_path, table_meta_dict)
        logger.debug(f"保存表元数据: {table_meta_path}")
        
        return table_meta_path
    
    def _write_yaml(self, path: Path, data: dict) -> None:
        """
        写入 YAML 文件
        
        Args:
            path: 文件路径
            data: 要写入的数据
        """
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
            )
    
    def load_schema_metadata(self, schema_name: str) -> Optional[dict]:
        """
        加载 Schema 元数据
        
        Args:
            schema_name: Schema 名称
            
        Returns:
            元数据字典
        """
        schema_dir = self.catalog_path / schema_name
        meta_path = schema_dir / SCHEMA_CONFIG_FILE
        
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载 Schema 元数据失败 {meta_path}: {e}")
            return None
    
    def load_table_metadata(self, schema_name: str, table_name: str) -> Optional[dict]:
        """
        加载表元数据
        
        Args:
            schema_name: Schema 名称
            table_name: 表名称
            
        Returns:
            元数据字典
        """
        schema_dir = self.catalog_path / schema_name
        tables_dir = schema_dir / TABLES_DIR
        table_path = tables_dir / f"{table_name}{ASSET_FILE_SUFFIX}"
        
        if not table_path.exists():
            return None
        
        try:
            with open(table_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载表元数据失败 {table_path}: {e}")
            return None
    
    def get_synced_schemas(self) -> List[str]:
        """
        获取所有已同步的 Schema 名称
        
        Returns:
            Schema 名称列表
        """
        schemas = []
        
        if not self.catalog_path.exists():
            return schemas
        
        for item in self.catalog_path.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            
            # 检查是否有 schema.yaml 且 source 为 connection
            meta = self.load_schema_metadata(item.name)
            if meta and meta.get("source") == "connection":
                schemas.append(item.name)
        
        return schemas
