"""
Schema 服务 - 管理 Schema 及其 Asset
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.constants import (
    SCHEMA_CONFIG_FILE, ASSET_FILE_SUFFIX,
    TABLES_DIR, VOLUMES_DIR, FUNCTIONS_DIR, NOTES_DIR, ASSET_TYPE_TO_DIR,
)
from app.models.catalog import (
    Schema, SchemaCreate, SchemaUpdate, ConnectionConfig, EntityType,
    Asset, AssetCreate, AssetType,
)
from app.models.metadata import SyncResult
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.catalog_service_new import CatalogService


# Asset 类型目录映射
ASSET_TYPE_DIRS = {
    AssetType.TABLE: TABLES_DIR,
    AssetType.VOLUME: VOLUMES_DIR,
    AssetType.AGENT: "agents",
    AssetType.NOTE: NOTES_DIR,
}


class SchemaService(BaseService):
    """Schema 服务类"""
    
    def __init__(self, catalog_service: "CatalogService"):
        super().__init__()
        self.catalog_service = catalog_service
    
    # ==================== 路径方法 ====================
    
    def _get_schema_path(self, catalog_id: str, schema_name: str) -> Optional[Path]:
        """获取 Schema 路径"""
        return self.catalog_service.get_schema_path(catalog_id, schema_name)
    
    def _get_type_dir(self, asset_type: AssetType) -> str:
        """获取 Asset 类型目录名"""
        if isinstance(asset_type, str):
            return ASSET_TYPE_DIRS.get(AssetType(asset_type), asset_type + "s")
        return ASSET_TYPE_DIRS.get(asset_type, str(asset_type.value) + "s")
    
    # ==================== Schema CRUD ====================
    
    def scan_schemas(self, catalog_path: Path, catalog_id: str) -> List[Schema]:
        """扫描 Schema"""
        schemas_dir = self.catalog_service.get_schemas_dir(catalog_path)
        return self._scan_subdirs(schemas_dir, lambda p: self._load_schema(catalog_id, p))
    
    def _load_schema(self, catalog_id: str, schema_path: Path) -> Optional[Schema]:
        """加载 Schema"""
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE) or {}
        baseinfo = self._extract_baseinfo(config, schema_path.name)
        
        connection = ConnectionConfig(**config["connection"]) if config.get("connection") else None
        
        return Schema(
            id=f"{catalog_id}_{schema_path.name}",
            name=schema_path.name,
            display_name=baseinfo.get("display_name") or schema_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            catalog_id=catalog_id,
            entity_type=EntityType.SCHEMA,
            schema_type=config.get("schema_type", "local"),
            connection=connection,
            path=str(schema_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            synced_at=self._parse_datetime(config.get("synced_at")),
        )
    
    def get_schemas(self, catalog_id: str) -> List[Schema]:
        """获取 Schema 列表"""
        catalog = self.catalog_service.get_catalog(catalog_id)
        return catalog.schemas if catalog else []
    
    def get_schema_config_content(self, catalog_id: str, schema_name: str) -> Optional[str]:
        """获取 Schema 配置内容"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        return self._read_file(schema_path / SCHEMA_CONFIG_FILE)
    
    def create_schema(self, catalog_id: str, data: SchemaCreate) -> Schema:
        """创建 Schema"""
        catalog_path = self.catalog_service.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        schema_type = data.schema_type or "local"
        if schema_type == "external" and not data.connection:
            raise ValueError("External 类型必须配置数据库连接")
        
        schemas_dir = self.catalog_service.get_schemas_dir(catalog_path)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        
        schema_path = schemas_dir / data.name
        if schema_path.exists():
            raise ValueError(f"Schema '{data.name}' 已存在")
        
        # 创建目录结构
        schema_path.mkdir(parents=True, exist_ok=True)
        for dir_name in ["models", "tables", "functions", "volumes"]:
            (schema_path / dir_name).mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        config = {"baseinfo": baseinfo, "schema_type": schema_type}
        
        connection = data.connection if schema_type == "external" else None
        if connection:
            config["connection"] = connection.model_dump()
            # 同步外部元数据
            sync_result = self._sync_metadata(schema_path, catalog_id, data.name, connection)
            if sync_result.success:
                config["synced_at"] = self._now_iso()
        
        self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        return self._load_schema(catalog_id, schema_path)
    
    def update_schema(self, catalog_id: str, schema_name: str, update: SchemaUpdate) -> Optional[Schema]:
        """更新 Schema"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        config_path = schema_path / SCHEMA_CONFIG_FILE
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, schema_path.name)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        if update.connection is not None and config.get("schema_type") == "external":
            config["connection"] = update.connection.model_dump()
        
        config["baseinfo"] = baseinfo
        self._save_yaml(config_path, config)
        return self._load_schema(catalog_id, schema_path)
    
    def delete_schema(self, catalog_id: str, schema_name: str) -> bool:
        """删除 Schema"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        return self._remove_dir(schema_path) if schema_path else False
    
    def _sync_metadata(self, schema_path: Path, catalog_id: str, schema_name: str, connection: ConnectionConfig) -> SyncResult:
        """同步 Schema 元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        sync_service = MetadataSyncService(schema_path, catalog_id, schema_name)
        return sync_service.sync_connection(connection)
    
    def sync_schema_metadata(self, catalog_id: str, schema_name: str) -> SyncResult:
        """手动同步 Schema 元数据"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return SyncResult(success=False, errors=[f"Schema '{schema_name}' 不存在"])
        
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE)
        if not config or not config.get("connection"):
            return SyncResult(success=False, errors=["Schema 没有配置数据库连接"])
        
        connection = ConnectionConfig(**config["connection"])
        result = self._sync_metadata(schema_path, catalog_id, schema_name, connection)
        
        if result.success:
            config["synced_at"] = self._now_iso()
            self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        
        return result
    
    # ==================== Asset 操作 ====================
    
    def scan_assets(self, catalog_id: str, schema_name: str) -> List[Asset]:
        """扫描 Schema 下的资产"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return []
        
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE)
        is_external = config and config.get("schema_type") == "external"
        
        assets = []
        for asset_type, dir_name in ASSET_TYPE_DIRS.items():
            type_dir = schema_path / dir_name
            if type_dir.exists() and type_dir.is_dir():
                assets.extend(self._scan_asset_dir(catalog_id, schema_name, type_dir, asset_type, is_external))
        
        # 函数目录
        functions_dir = schema_path / FUNCTIONS_DIR
        if functions_dir.exists():
            assets.extend(self._scan_asset_dir(catalog_id, schema_name, functions_dir, AssetType.AGENT, is_external))
        
        return assets
    
    def _scan_asset_dir(self, catalog_id: str, schema_name: str, type_dir: Path, asset_type: AssetType, is_external: bool) -> List[Asset]:
        """扫描资产目录"""
        assets = []
        for item in type_dir.iterdir():
            if item.name.startswith(".") or item.suffix != ".yaml":
                continue
            
            config = self._load_yaml(item) or {}
            baseinfo = self._extract_baseinfo(config, item.stem)
            
            metadata = {k: v for k, v in config.items() if k not in ["baseinfo", "name", "created_at", "updated_at"]}
            metadata["source"] = "synced" if is_external else "local"
            
            assets.append(Asset(
                id=f"{catalog_id}_{schema_name}_{item.stem}",
                name=baseinfo.get("name") or item.stem,
                display_name=baseinfo.get("display_name") or item.stem,
                description=baseinfo.get("description"),
                tags=baseinfo.get("tags", []),
                schema_id=f"{catalog_id}_{schema_name}",
                asset_type=asset_type,
                entity_type=EntityType(asset_type.value) if asset_type.value in [e.value for e in EntityType] else EntityType.TABLE,
                path=str(item),
                metadata=metadata,
                created_at=self._parse_datetime(baseinfo.get("created_at")),
                updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            ))
        return assets
    
    def get_asset_config_content(self, catalog_id: str, schema_name: str, asset_name: str) -> Optional[str]:
        """获取 Asset 配置内容"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        for dir_name in ASSET_TYPE_TO_DIR.values():
            asset_file = schema_path / dir_name / f"{asset_name}{ASSET_FILE_SUFFIX}"
            content = self._read_file(asset_file)
            if content is not None:
                return content
        return None
    
    def create_asset(self, catalog_id: str, schema_name: str, data: AssetCreate) -> Asset:
        """创建 Asset"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise FileNotFoundError(f"Schema '{schema_name}' 不存在")
        
        type_dir = schema_path / self._get_type_dir(data.asset_type)
        type_dir.mkdir(parents=True, exist_ok=True)
        
        asset_path = type_dir / f"{data.name}.yaml"
        if asset_path.exists():
            raise ValueError(f"资产 '{data.name}' 已存在")
        
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        
        asset_config = {
            "baseinfo": baseinfo,
            "asset_type": data.asset_type.value if hasattr(data.asset_type, 'value') else data.asset_type,
            "source": "local",
        }
        
        # 类型特有字段
        if data.asset_type == AssetType.VOLUME or data.asset_type == "volume":
            asset_config["volume_type"] = data.volume_type or "local"
            if data.volume_type == "local":
                asset_config["storage_location"] = data.storage_location
            elif data.volume_type == "s3":
                asset_config.update({
                    "s3_endpoint": data.s3_endpoint,
                    "s3_bucket": data.s3_bucket,
                    "s3_access_key": data.s3_access_key,
                    "s3_secret_key": data.s3_secret_key,
                })
        elif data.asset_type == AssetType.TABLE or data.asset_type == "table":
            asset_config["format"] = data.format
            asset_config["columns"] = []
        
        self._save_yaml(asset_path, asset_config)
        
        return Asset(
            id=f"{catalog_id}_{schema_name}_{data.name}",
            name=data.name,
            display_name=baseinfo["display_name"],
            description=baseinfo["description"],
            tags=baseinfo["tags"],
            schema_id=f"{catalog_id}_{schema_name}",
            asset_type=data.asset_type,
            path=str(asset_path),
            metadata={"source": "local"},
            created_at=self._parse_datetime(baseinfo["created_at"]),
            updated_at=self._parse_datetime(baseinfo["updated_at"]),
        )
    
    def delete_asset(self, catalog_id: str, schema_name: str, asset_name: str) -> bool:
        """删除 Asset"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        
        for dir_name in list(ASSET_TYPE_DIRS.values()) + [FUNCTIONS_DIR]:
            asset_path = schema_path / dir_name / f"{asset_name}.yaml"
            if asset_path.exists():
                asset_path.unlink()
                return True
        return False
    
    def preview_table_data(self, catalog_id: str, schema_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """预览表数据"""
        from app.services.connectors import ConnectorFactory
        
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise ValueError(f"Schema '{schema_name}' 不存在")
        
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE)
        if not config or config.get("schema_type") != "external":
            raise ValueError("只有 External 类型的 Schema 支持数据预览")
        
        if not config.get("connection"):
            raise ValueError("Schema 没有配置数据库连接")
        
        connection = ConnectionConfig(**config["connection"])
        connector = ConnectorFactory.create(connection)
        if not connector:
            raise ValueError(f"不支持的连接类型: {connection.type}")
        
        try:
            if not connector.connect():
                raise ValueError("无法连接到数据库")
            return connector.preview_data(connection.db_name, table_name, limit, offset)
        finally:
            connector.disconnect()
