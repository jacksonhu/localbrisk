"""
Catalog 服务层
实现基于文件系统的混合 Catalog 管理
- 本地模式 (Local-first)：扫描文件系统
- 外部挂载模式 (Connection-sync)：连接外部数据库并同步元数据

树形结构定义：
├── Catalog (Namespace)
│   ├── agents/{agent_name}/           # Agent 智能体目录
│   │   ├── agent.yaml                 # Agent 配置（提示词策略、Skills 列表）
│   │   ├── prompts/                   # 提示词模板目录
│   │   └── skills/                    # Skills 文件目录
│   └── schemas/{schema_name}/         # Schema 逻辑库目录
│       ├── schema.yaml                # Schema 配置（资产发现规则）
│       ├── models/                    # 模型定义目录
│       ├── tables/                    # 表映射目录
│       ├── functions/                 # 自定义函数目录
│       └── volumes/                   # 文档存储目录

物理存储映射：
- Catalog 层: App_Data/Catalogs/{catalog_name}/
  - 包含 config.yaml：定义连接池和 Catalog 元数据
- Agent 层: agents/{agent_name}/ 文件夹
  - 包含 agent.yaml：定义提示词策略和 Skills 列表
- Schema 层: schemas/{schema_name}/ 文件夹
  - 包含 schema.yaml：定义资产发现规则

配置文件格式：YAML
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

import yaml

from app.core.config import settings
from app.core.constants import (
    CATALOG_CONFIG_FILE,
    AGENT_CONFIG_FILE,
    SCHEMA_CONFIG_FILE,
    ASSET_FILE_SUFFIX,
    AGENTS_DIR,
    SCHEMAS_DIR,
    TABLES_DIR,
    VOLUMES_DIR,
    FUNCTIONS_DIR,
    MODELS_DIR,
    NOTES_DIR,
    ASSET_TYPE_TO_DIR,
    DIR_TO_ASSET_TYPE,
)
from app.models.catalog import (
    Catalog,
    CatalogConfig,
    CatalogCreate,
    CatalogUpdate,
    CatalogTreeNode,
    ConnectionConfig,
    Schema,
    SchemaCreate,
    SchemaUpdate,
    SchemaSource,
    Asset,
    AssetCreate,
    AssetType,
    Agent,
    AgentCreate,
    AgentUpdate,
    Model,
    ModelCreate,
    ModelUpdate,
    Prompt,
    PromptCreate,
    PromptUpdate,
)
from app.models.metadata import SyncResult

logger = logging.getLogger(__name__)

# 资产类型目录映射（使用枚举类型作为键，便于类型检查）
ASSET_TYPE_DIRS = {
    AssetType.TABLE: TABLES_DIR,
    AssetType.VOLUME: VOLUMES_DIR,
    AssetType.AGENT: AGENTS_DIR,
    AssetType.NOTE: NOTES_DIR,
}


class CatalogService:
    """
    Catalog 服务类
    负责 Catalog 的发现、加载和管理
    
    目录结构：
    App_Data/Catalogs/{catalog_name}/
    ├── config.yaml                    # Catalog 配置
    ├── agents/                        # Agent 目录
    │   └── {agent_name}/
    │       ├── agent.yaml             # Agent 配置
    │       ├── prompts/               # Prompts 子目录
    │       └── skills/                # Skills 子目录
    └── schemas/                       # Schema 目录
        └── {schema_name}/
            ├── schema.yaml            # Schema 配置
            ├── models/                # Models 子目录
            ├── tables/                # Tables 子目录
            ├── functions/             # Functions 子目录
            └── volumes/               # Volumes 子目录
    """
    
    def __init__(self):
        self.catalogs_dir = settings.CATALOGS_DIR
        self._ensure_catalogs_dir()
    
    def _ensure_catalogs_dir(self):
        """确保 Catalogs 目录存在"""
        self.catalogs_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== 路径辅助方法 ====================
    
    def _get_catalog_path(self, catalog_name: str) -> Path:
        """获取 Catalog 文件夹路径"""
        return self.catalogs_dir / catalog_name
    
    def _get_config_path(self, catalog_path: Path) -> Path:
        """获取 Catalog 配置文件路径 (config.yaml)"""
        return catalog_path / CATALOG_CONFIG_FILE
    
    def _get_agents_dir(self, catalog_path: Path) -> Path:
        """获取 Agent 目录路径"""
        return catalog_path / AGENTS_DIR
    
    def _get_schemas_dir(self, catalog_path: Path) -> Path:
        """获取 Schema 目录路径"""
        return catalog_path / SCHEMAS_DIR
    
    def _get_schema_path(self, catalog_id: str, schema_name: str) -> Optional[Path]:
        """
        获取 Schema 路径
        
        Args:
            catalog_id: Catalog ID
            schema_name: Schema 名称
            
        Returns:
            Schema 路径，不存在返回 None
        """
        catalog_path = self._get_catalog_path(catalog_id)
        schemas_dir = self._get_schemas_dir(catalog_path)
        schema_path = schemas_dir / schema_name
        return schema_path if schema_path.exists() else None
    
    # ==================== 配置加载/保存 ====================
    
    def _load_catalog_config(self, catalog_path: Path) -> Optional[CatalogConfig]:
        """
        加载 Catalog 配置文件 (config.yaml)
        
        Args:
            catalog_path: Catalog 文件夹路径
            
        Returns:
            CatalogConfig 对象，如果配置文件不存在则返回 None
        """
        config_path = self._get_config_path(catalog_path)
        
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            if config_data is None:
                return None
            return CatalogConfig(**config_data)
        except (yaml.YAMLError, Exception) as e:
            logger.error(f"加载配置文件失败 {config_path}: {e}")
            return None
    
    def _save_catalog_config(self, catalog_path: Path, config: CatalogConfig):
        """
        保存 Catalog 配置文件为 YAML 格式 (config.yaml)
        
        Args:
            catalog_path: Catalog 文件夹路径
            config: CatalogConfig 配置对象
        """
        config_path = self._get_config_path(catalog_path)
        config_dict = config.model_dump(mode="json")
        
        # 处理日期时间字段
        for key in ["created_at", "updated_at"]:
            if key in config_dict and config_dict[key] is not None:
                if isinstance(config_dict[key], datetime):
                    config_dict[key] = config_dict[key].isoformat()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    
    def _load_schema_config(self, schema_path: Path) -> Optional[Dict[str, Any]]:
        """
        加载 Schema 的配置文件 (schema.yaml)
        
        Args:
            schema_path: Schema 文件夹路径
            
        Returns:
            配置字典，不存在则返回 None
        """
        schema_config_path = schema_path / SCHEMA_CONFIG_FILE
        if not schema_config_path.exists():
            return None
        
        try:
            with open(schema_config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载 Schema 配置失败 {schema_config_path}: {e}")
            return None
    
    # ==================== Catalog 操作 ====================
    
    def discover_catalogs(self) -> List[Catalog]:
        """
        发现并加载所有 Catalog
        扫描 Catalogs 根目录，解析每个 Catalog 的 config.yaml
        
        Returns:
            Catalog 列表
        """
        catalogs = []
        
        if not self.catalogs_dir.exists():
            return catalogs
        
        for item in self.catalogs_dir.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            
            catalog = self._load_catalog(item)
            if catalog:
                catalogs.append(catalog)
        
        return catalogs
    
    def _load_catalog(self, catalog_path: Path) -> Optional[Catalog]:
        """
        加载单个 Catalog
        
        Args:
            catalog_path: Catalog 文件夹路径
            
        Returns:
            Catalog 对象
        """
        config = self._load_catalog_config(catalog_path)
        
        # 如果没有配置文件，创建默认配置
        if config is None:
            config = CatalogConfig(
                catalog_id=catalog_path.name,
                display_name=catalog_path.name,
                connections=[],
                allow_custom_schema=True,
                created_at=datetime.fromtimestamp(catalog_path.stat().st_ctime),
                updated_at=datetime.now(),
            )
            self._save_catalog_config(catalog_path, config)
        
        # 扫描所有 Schema
        all_schemas = self._scan_schemas(catalog_path, config.catalog_id)
        
        # 扫描所有 Agent
        all_agents = self._scan_agents(catalog_path, config.catalog_id)
        
        return Catalog(
            id=config.catalog_id,
            name=catalog_path.name,
            display_name=config.display_name,
            owner="admin",
            description=config.description,
            tags=config.tags,
            path=str(catalog_path),
            has_connections=len(config.connections) > 0,
            allow_custom_schema=config.allow_custom_schema,
            created_at=config.created_at or datetime.fromtimestamp(catalog_path.stat().st_ctime),
            updated_at=config.updated_at or datetime.now(),
            schemas=all_schemas,
            agents=all_agents,
            connections=config.connections,
        )
    
    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        """
        获取指定 Catalog
        
        Args:
            catalog_id: Catalog ID
            
        Returns:
            Catalog 对象，不存在返回 None
        """
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        return self._load_catalog(catalog_path)
    
    def create_catalog(self, catalog_create: CatalogCreate) -> Catalog:
        """
        创建新的 Catalog
        如果配置了连接，会自动同步数据库元数据
        
        Args:
            catalog_create: 创建参数
            
        Returns:
            新创建的 Catalog
        """
        catalog_path = self._get_catalog_path(catalog_create.name)
        
        if catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_create.name}' 已存在")
        
        # 创建文件夹结构
        catalog_path.mkdir(parents=True, exist_ok=True)
        self._get_agents_dir(catalog_path).mkdir(exist_ok=True)
        self._get_schemas_dir(catalog_path).mkdir(exist_ok=True)
        
        # 创建配置文件
        now = datetime.now()
        # 将 ConnectionConfig 对象转换为字典以避免 Pydantic 验证问题
        connections_data = [
            conn.model_dump() if hasattr(conn, 'model_dump') else conn.dict()
            for conn in catalog_create.connections
        ] if catalog_create.connections else []
        
        config = CatalogConfig(
            catalog_id=catalog_create.name,
            display_name=catalog_create.display_name or catalog_create.name,
            connections=connections_data,
            allow_custom_schema=catalog_create.allow_custom_schema,
            description=catalog_create.description,
            created_at=now,
            updated_at=now,
        )
        self._save_catalog_config(catalog_path, config)
        
        # 如果配置了连接，同步元数据
        if catalog_create.connections:
            sync_result = self._sync_connection_metadata(catalog_path, catalog_create.name, catalog_create.connections)
            if not sync_result.success:
                logger.warning(f"元数据同步失败: {sync_result.errors}")
            else:
                logger.info(f"元数据同步完成: {sync_result.schemas_synced} 个 Schema, {sync_result.tables_synced} 张表")
        
        return self._load_catalog(catalog_path)
    
    def update_catalog(self, catalog_id: str, catalog_update: CatalogUpdate) -> Optional[Catalog]:
        """
        更新 Catalog 信息
        如果连接配置发生变化，会重新同步元数据
        
        Args:
            catalog_id: Catalog ID
            catalog_update: 更新参数
            
        Returns:
            更新后的 Catalog 对象，不存在返回 None
        """
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        
        config = self._load_catalog_config(catalog_path)
        if config is None:
            config = CatalogConfig(
                catalog_id=catalog_id,
                display_name=catalog_id,
                connections=[],
                allow_custom_schema=True,
                created_at=datetime.fromtimestamp(catalog_path.stat().st_ctime),
                updated_at=datetime.now(),
            )
        
        old_connections = config.connections
        
        # 更新字段
        if catalog_update.display_name is not None:
            config.display_name = catalog_update.display_name
        if catalog_update.description is not None:
            config.description = catalog_update.description
        if catalog_update.tags is not None:
            config.tags = catalog_update.tags
        if catalog_update.allow_custom_schema is not None:
            config.allow_custom_schema = catalog_update.allow_custom_schema
        if catalog_update.connections is not None:
            config.connections = catalog_update.connections
        
        config.updated_at = datetime.now()
        self._save_catalog_config(catalog_path, config)
        
        # 如果连接配置发生变化，重新同步元数据
        if catalog_update.connections is not None:
            if self._connections_changed(old_connections, catalog_update.connections) and catalog_update.connections:
                logger.info(f"连接配置已更新，开始同步元数据...")
                sync_result = self._sync_connection_metadata(catalog_path, catalog_id, catalog_update.connections)
                if not sync_result.success:
                    logger.warning(f"元数据同步失败: {sync_result.errors}")
        
        return self._load_catalog(catalog_path)
    
    def delete_catalog(self, catalog_id: str) -> bool:
        """
        删除 Catalog
        
        Args:
            catalog_id: Catalog ID
            
        Returns:
            是否删除成功
        """
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return False
        
        shutil.rmtree(catalog_path)
        return True
    
    def _connections_changed(self, old: List[ConnectionConfig], new: List[ConnectionConfig]) -> bool:
        """比较连接配置是否发生变化"""
        if len(old) != len(new):
            return True
        old_dicts = [c.model_dump() for c in old]
        new_dicts = [c.model_dump() for c in new]
        return old_dicts != new_dicts
    
    # ==================== 元数据同步 ====================
    
    def _sync_connection_metadata(self, catalog_path: Path, catalog_id: str, connections: List[ConnectionConfig]) -> SyncResult:
        """
        同步连接的元数据到本地文件系统
        元数据会保存到 schemas/ 目录下
        """
        from app.services.metadata_sync_service import MetadataSyncService
        
        # 同步到 schemas 目录
        schemas_dir = self._get_schemas_dir(catalog_path)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        
        sync_service = MetadataSyncService(schemas_dir, catalog_id)
        return sync_service.sync_all_connections(connections)
    
    def sync_catalog_metadata(self, catalog_id: str) -> SyncResult:
        """
        手动触发 Catalog 的元数据同步
        """
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return SyncResult(success=False, errors=[f"Catalog '{catalog_id}' 不存在"])
        
        config = self._load_catalog_config(catalog_path)
        if not config:
            return SyncResult(success=False, errors=["无法加载 Catalog 配置"])
        
        if not config.connections:
            return SyncResult(success=True, warnings=["没有配置数据库连接"])
        
        return self._sync_connection_metadata(catalog_path, catalog_id, config.connections)
    
    # ==================== Schema 操作 ====================
    
    def _scan_schemas(self, catalog_path: Path, catalog_id: str) -> List[Schema]:
        """
        扫描本地 Schema（schemas/ 目录下的子文件夹）
        
        Args:
            catalog_path: Catalog 文件夹路径
            catalog_id: Catalog ID
            
        Returns:
            Schema 列表
        """
        schemas = []
        schemas_dir = self._get_schemas_dir(catalog_path)
        
        if not schemas_dir.exists():
            return schemas
        
        for item in schemas_dir.iterdir():
            if not item.is_dir() or item.name.startswith(".") or item.name == "__pycache__":
                continue
            
            schema_config = self._load_schema_config(item)
            
            if schema_config and schema_config.get("source") == "connection":
                # 连接同步的 Schema
                schema = Schema(
                    id=f"{catalog_id}_{item.name}",
                    name=item.name,
                    catalog_id=catalog_id,
                    owner="admin",
                    description=schema_config.get("description") or schema_config.get("comment"),
                    source=SchemaSource.CONNECTION,
                    connection_name=f"{schema_config.get('connection_type')}://{schema_config.get('connection_host')}:{schema_config.get('connection_port')}/{item.name}",
                    readonly=schema_config.get("readonly", True),
                    path=str(item),
                    created_at=datetime.fromisoformat(schema_config["synced_at"]) if schema_config.get("synced_at") else datetime.now(),
                )
            else:
                # 本地创建的 Schema
                schema = Schema(
                    id=f"{catalog_id}_{item.name}",
                    name=item.name,
                    catalog_id=catalog_id,
                    owner=schema_config.get("owner", "admin") if schema_config else "admin",
                    description=schema_config.get("description") or schema_config.get("comment") if schema_config else None,
                    source=SchemaSource.LOCAL,
                    connection_name=None,
                    readonly=False,
                    path=str(item),
                    created_at=datetime.fromtimestamp(item.stat().st_ctime),
                )
            schemas.append(schema)
        
        return schemas
    
    def get_schemas(self, catalog_id: str) -> List[Schema]:
        """获取 Catalog 下的所有 Schema"""
        catalog = self.get_catalog(catalog_id)
        return catalog.schemas if catalog else []
    
    def create_schema(self, catalog_id: str, schema_create: SchemaCreate) -> Schema:
        """
        在 Catalog 下创建新的 Schema
        会自动创建资产类型子目录（models, tables, functions, volumes）
        
        Args:
            catalog_id: Catalog ID
            schema_create: Schema 创建参数
            
        Returns:
            新创建的 Schema
        """
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        config = self._load_catalog_config(catalog_path)
        if config and not config.allow_custom_schema:
            raise ValueError(f"Catalog '{catalog_id}' 不允许创建自定义 Schema")
        
        schemas_dir = self._get_schemas_dir(catalog_path)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        
        schema_path = schemas_dir / schema_create.name
        if schema_path.exists():
            raise ValueError(f"Schema '{schema_create.name}' 已存在")
        
        # 创建 Schema 文件夹及子目录
        schema_path.mkdir(parents=True, exist_ok=True)
        for dir_name in ["models", "tables", "functions", "volumes"]:
            (schema_path / dir_name).mkdir(exist_ok=True)
        
        # 保存 Schema 配置到 schema.yaml
        now = datetime.now()
        schema_config = {
            "source": "local",
            "owner": schema_create.owner or "admin",
            "description": schema_create.description,
            "sync_remote_tables": False,
            "created_at": now.isoformat(),
        }
        with open(schema_path / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(schema_config, f, allow_unicode=True, sort_keys=False)
        
        return Schema(
            id=f"{catalog_id}_{schema_create.name}",
            name=schema_create.name,
            catalog_id=catalog_id,
            owner=schema_create.owner or "admin",
            description=schema_create.description,
            source=SchemaSource.LOCAL,
            readonly=False,
            path=str(schema_path),
            created_at=now,
        )
    
    def update_schema(self, catalog_id: str, schema_name: str, schema_update: SchemaUpdate) -> Optional[Schema]:
        """
        更新 Schema 信息（仅支持本地创建的 Schema）
        """
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        schema_config = self._load_schema_config(schema_path) or {}
        
        if schema_config.get("source") == "connection" or schema_config.get("readonly"):
            raise ValueError("无法修改外部连接同步的 Schema")
        
        if schema_update.description is not None:
            schema_config["description"] = schema_update.description
        
        with open(schema_path / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(schema_config, f, allow_unicode=True, sort_keys=False)
        
        return Schema(
            id=f"{catalog_id}_{schema_name}",
            name=schema_name,
            catalog_id=catalog_id,
            owner=schema_config.get("owner", "admin"),
            description=schema_config.get("description"),
            source=SchemaSource.LOCAL,
            connection_name=None,
            readonly=False,
            path=str(schema_path),
            created_at=datetime.fromtimestamp(schema_path.stat().st_ctime),
        )
    
    def delete_schema(self, catalog_id: str, schema_name: str) -> bool:
        """删除 Schema（仅支持本地创建的 Schema）"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        
        shutil.rmtree(schema_path)
        return True
    
    # ==================== Asset 操作 ====================
    
    def _detect_asset_type(self, path: Path) -> AssetType:
        """检测资产类型"""
        if path.is_dir():
            return AssetType.VOLUME
        
        suffix = path.suffix.lower()
        
        if suffix in [".parquet", ".csv", ".json", ".delta"]:
            return AssetType.TABLE
        if suffix in [".md", ".txt", ".rst"]:
            return AssetType.NOTE
        if suffix in [".yaml", ".yml"] or (suffix == ".json" and "agent" in path.stem.lower()):
            return AssetType.AGENT
        
        return AssetType.VOLUME
    
    def _get_asset_type_dir(self, asset_type: AssetType) -> str:
        """获取资产类型对应的目录名"""
        type_dirs = {
            AssetType.TABLE: "tables",
            AssetType.VOLUME: "volumes",
            AssetType.AGENT: "agents",
            AssetType.NOTE: "notes",
        }
        if isinstance(asset_type, str):
            return type_dirs.get(AssetType(asset_type), asset_type + "s")
        return type_dirs.get(asset_type, str(asset_type.value) + "s")
    
    def scan_assets(self, catalog_id: str, schema_name: str) -> List[Asset]:
        """
        扫描 Schema 下的所有资产
        
        Args:
            catalog_id: Catalog ID
            schema_name: Schema 名称
            
        Returns:
            Asset 列表
        """
        assets = []
        schema_path = self._get_schema_path(catalog_id, schema_name)
        
        if not schema_path:
            return assets
        
        schema_config = self._load_schema_config(schema_path)
        is_connection_schema = schema_config and schema_config.get("source") == "connection"
        
        # 扫描资产类型子目录
        for asset_type, dir_name in ASSET_TYPE_DIRS.items():
            type_dir = schema_path / dir_name
            if type_dir.exists() and type_dir.is_dir():
                assets.extend(self._scan_asset_type_dir(catalog_id, schema_name, type_dir, asset_type, is_connection_schema))
        
        # 扫描 functions 目录（作为资产类型）
        functions_dir = schema_path / FUNCTIONS_DIR
        if functions_dir.exists() and functions_dir.is_dir():
            assets.extend(self._scan_asset_type_dir(catalog_id, schema_name, functions_dir, AssetType.AGENT, is_connection_schema))
        
        return assets
    
    def _scan_asset_type_dir(self, catalog_id: str, schema_name: str, type_dir: Path, asset_type: AssetType, is_connection_schema: bool) -> List[Asset]:
        """扫描特定资产类型目录下的所有资产"""
        assets = []
        
        for item in type_dir.iterdir():
            if item.name.startswith("."):
                continue
            
            if asset_type == AssetType.TABLE and item.suffix == ".yaml":
                table_meta = self._load_table_metadata(item)
                if table_meta:
                    assets.append(self._create_table_asset(catalog_id, schema_name, item, table_meta))
            elif item.is_file() and item.suffix == ".yaml":
                asset_meta = self._load_asset_metadata(item)
                assets.append(Asset(
                    id=f"{catalog_id}_{schema_name}_{item.stem}",
                    name=item.stem,
                    schema_id=f"{catalog_id}_{schema_name}",
                    asset_type=asset_type,
                    path=str(item),
                    metadata={
                        "is_directory": False,
                        "extension": ".yaml",
                        "source": "connection" if is_connection_schema else "local",
                        **(asset_meta or {}),
                    },
                    created_at=datetime.fromtimestamp(item.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(item.stat().st_mtime),
                ))
            elif item.is_dir():
                assets.append(self._create_generic_asset(catalog_id, schema_name, item, asset_type))
            else:
                assets.append(self._create_generic_asset(catalog_id, schema_name, item, asset_type))
        
        return assets
    
    def _create_table_asset(self, catalog_id: str, schema_name: str, item: Path, table_meta: Dict[str, Any]) -> Asset:
        """创建表类型的 Asset"""
        columns = table_meta.get("columns", [])
        return Asset(
            id=f"{catalog_id}_{schema_name}_{table_meta.get('name', item.stem)}",
            name=table_meta.get("name", item.stem),
            schema_id=f"{catalog_id}_{schema_name}",
            asset_type=AssetType.TABLE,
            path=str(item),
            metadata={
                "is_directory": False,
                "extension": ".yaml",
                "source": "connection" if table_meta.get("source") == "connection" else "local",
                "table_type": table_meta.get("table_type"),
                "engine": table_meta.get("engine"),
                "comment": table_meta.get("comment"),
                "description": table_meta.get("comment") or table_meta.get("description"),
                "format": table_meta.get("format", "parquet"),
                "row_count": table_meta.get("row_count"),
                "column_count": len(columns),
                "columns": columns,
                "primary_keys": table_meta.get("primary_keys", []),
            },
            created_at=datetime.fromisoformat(table_meta["create_time"]) if table_meta.get("create_time") else datetime.now(),
            updated_at=datetime.fromisoformat(table_meta["update_time"]) if table_meta.get("update_time") else None,
        )
    
    def _create_generic_asset(self, catalog_id: str, schema_name: str, item: Path, asset_type: AssetType) -> Asset:
        """创建通用类型的 Asset"""
        return Asset(
            id=f"{catalog_id}_{schema_name}_{item.name}",
            name=item.stem if item.is_file() else item.name,
            schema_id=f"{catalog_id}_{schema_name}",
            asset_type=asset_type,
            path=str(item),
            metadata={
                "is_directory": item.is_dir(),
                "extension": item.suffix if item.is_file() else None,
                "size": item.stat().st_size if item.is_file() else None,
            },
            created_at=datetime.fromtimestamp(item.stat().st_ctime),
            updated_at=datetime.fromtimestamp(item.stat().st_mtime),
        )
    
    def _load_asset_metadata(self, asset_path: Path) -> Optional[Dict[str, Any]]:
        """加载资产元数据文件"""
        try:
            with open(asset_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载资产元数据失败 {asset_path}: {e}")
            return None
    
    def _load_table_metadata(self, table_path: Path) -> Optional[Dict[str, Any]]:
        """加载表元数据文件"""
        try:
            with open(table_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载表元数据失败 {table_path}: {e}")
            return None
    
    def create_asset(self, catalog_id: str, schema_name: str, asset_create: AssetCreate) -> Asset:
        """
        在 Schema 下创建新的资产
        会在对应的资产类型目录下生成 {name}.yaml 元数据文件
        """
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise FileNotFoundError(f"Schema '{schema_name}' 不存在")
        
        schema_config = self._load_schema_config(schema_path)
        if schema_config and (schema_config.get("source") == "connection" or schema_config.get("readonly")):
            raise ValueError("无法在只读 Schema 中创建资产")
        
        asset_type_dir = self._get_asset_type_dir(asset_create.asset_type)
        type_dir_path = schema_path / asset_type_dir
        type_dir_path.mkdir(parents=True, exist_ok=True)
        
        asset_meta_path = type_dir_path / f"{asset_create.name}.yaml"
        if asset_meta_path.exists():
            raise ValueError(f"资产 '{asset_create.name}' 已存在")
        
        now = datetime.now()
        asset_meta = {
            "name": asset_create.name,
            "asset_type": asset_create.asset_type.value if hasattr(asset_create.asset_type, 'value') else asset_create.asset_type,
            "description": asset_create.description,
            "source": "local",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        # 根据不同资产类型添加特有字段
        if asset_create.asset_type == AssetType.VOLUME or asset_create.asset_type == "volume":
            asset_meta["volume_type"] = asset_create.volume_type or "local"
            if asset_create.volume_type == "local":
                asset_meta["storage_location"] = asset_create.storage_location
                if asset_create.storage_location:
                    storage_path = Path(asset_create.storage_location)
                    if not storage_path.exists():
                        raise ValueError(f"存储路径 '{asset_create.storage_location}' 不存在")
                    asset_meta["file_count"] = len(list(storage_path.iterdir())) if storage_path.is_dir() else 0
            elif asset_create.volume_type == "s3":
                if not all([asset_create.s3_endpoint, asset_create.s3_bucket, asset_create.s3_access_key, asset_create.s3_secret_key]):
                    raise ValueError("S3 配置不完整")
                asset_meta.update({
                    "s3_endpoint": asset_create.s3_endpoint,
                    "s3_bucket": asset_create.s3_bucket,
                    "s3_access_key": asset_create.s3_access_key,
                    "s3_secret_key": asset_create.s3_secret_key,
                })
        elif asset_create.asset_type == AssetType.TABLE or asset_create.asset_type == "table":
            asset_meta["format"] = asset_create.format
            asset_meta["columns"] = []
        
        with open(asset_meta_path, "w", encoding="utf-8") as f:
            yaml.dump(asset_meta, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        
        logger.info(f"创建资产: {catalog_id}/{schema_name}/{asset_type_dir}/{asset_create.name}")
        
        return Asset(
            id=f"{catalog_id}_{schema_name}_{asset_create.name}",
            name=asset_create.name,
            schema_id=f"{catalog_id}_{schema_name}",
            asset_type=asset_create.asset_type,
            path=str(asset_meta_path),
            metadata={
                "description": asset_create.description,
                "source": "local",
                **({k: v for k, v in asset_meta.items() if k not in ["name", "asset_type", "created_at", "updated_at"]}),
            },
            created_at=now,
            updated_at=now,
        )
    
    def delete_asset(self, catalog_id: str, schema_name: str, asset_name: str) -> bool:
        """删除指定资产"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        
        all_type_dirs = list(ASSET_TYPE_DIRS.values()) + [FUNCTIONS_DIR]
        
        for type_dir in all_type_dirs:
            type_dir_path = schema_path / type_dir
            if not type_dir_path.exists():
                continue
            
            asset_meta_path = type_dir_path / f"{asset_name}.yaml"
            if asset_meta_path.exists():
                asset_meta_path.unlink()
                logger.info(f"删除资产: {catalog_id}/{schema_name}/{type_dir}/{asset_name}")
                return True
        
        return False
    
    def preview_table_data(self, catalog_id: str, schema_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        预览表数据（仅支持外部连接的表）
        """
        from app.services.connectors import ConnectorFactory
        
        catalog = self.get_catalog(catalog_id)
        if not catalog:
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        if not catalog.connections:
            raise ValueError("该 Catalog 没有配置数据库连接，无法预览数据")
        
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise ValueError(f"Schema '{schema_name}' 不存在")
        
        schema_config = self._load_schema_config(schema_path)
        if not schema_config or schema_config.get("source") != "connection":
            raise ValueError("只有外部连接的 Schema 支持数据预览")
        
        connection = None
        for conn in catalog.connections:
            if conn.db_name == schema_name or not conn.db_name:
                connection = conn
                break
        
        if not connection:
            raise ValueError("未找到匹配的数据库连接")
        
        connector = ConnectorFactory.create(connection)
        if not connector:
            raise ValueError(f"不支持的连接类型: {connection.type}")
        
        try:
            if not connector.connect():
                raise ValueError("无法连接到数据库")
            return connector.preview_data(schema_name, table_name, limit, offset)
        finally:
            connector.disconnect()
    
    # ==================== Agent 操作 ====================
    
    def _scan_agents(self, catalog_path: Path, catalog_id: str) -> List[Agent]:
        """扫描 Catalog 下的所有 Agent"""
        agents = []
        agents_dir = self._get_agents_dir(catalog_path)
        
        if not agents_dir.exists():
            return agents
        
        for item in agents_dir.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue
            
            agent = self._load_agent(catalog_id, item)
            if agent:
                agents.append(agent)
        
        return agents
    
    def _load_agent(self, catalog_id: str, agent_path: Path) -> Optional[Agent]:
        """加载单个 Agent"""
        agent_config_path = agent_path / AGENT_CONFIG_FILE
        
        agent_config = {}
        if agent_config_path.exists():
            try:
                with open(agent_config_path, "r", encoding="utf-8") as f:
                    agent_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"加载 Agent 配置失败 {agent_config_path}: {e}")
        
        # 扫描 skills 目录
        skills = []
        skills_dir = agent_path / "skills"
        if skills_dir.exists():
            for item in skills_dir.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    skills.append(item.name)
        
        # 扫描 prompts 目录
        prompts = []
        prompts_dir = agent_path / "prompts"
        if prompts_dir.exists():
            for item in prompts_dir.iterdir():
                if item.is_file() and item.suffix.lower() in [".md", ".markdown"] and not item.name.startswith("."):
                    prompts.append(item.name)
        
        # 获取已启用的 skills 和 prompts 列表
        enabled_skills = agent_config.get("enabled_skills", [])
        enabled_prompts = agent_config.get("enabled_prompts", [])
        
        return Agent(
            id=f"{catalog_id}_agent_{agent_path.name}",
            name=agent_path.name,
            catalog_id=catalog_id,
            description=agent_config.get("description"),
            path=str(agent_path),
            system_prompt=agent_config.get("system_prompt"),
            model_reference=agent_config.get("model_reference"),
            skills=skills,
            prompts=prompts,
            enabled_skills=enabled_skills,
            enabled_prompts=enabled_prompts,
            created_at=datetime.fromisoformat(agent_config["created_at"]) if agent_config.get("created_at") else datetime.fromtimestamp(agent_path.stat().st_ctime),
            updated_at=datetime.fromisoformat(agent_config["updated_at"]) if agent_config.get("updated_at") else None,
        )
    
    def list_agents(self, catalog_id: str) -> List[Agent]:
        """获取 Catalog 下的所有 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return []
        return self._scan_agents(catalog_path, catalog_id)
    
    def get_agent(self, catalog_id: str, agent_name: str) -> Optional[Agent]:
        """获取指定 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        
        if not agent_path.exists():
            return None
        
        return self._load_agent(catalog_id, agent_path)
    
    def create_agent(self, catalog_id: str, agent_create: AgentCreate) -> Agent:
        """在 Catalog 下创建新的 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        agents_dir = self._get_agents_dir(catalog_path)
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_path = agents_dir / agent_create.name
        if agent_path.exists():
            raise ValueError(f"Agent '{agent_create.name}' 已存在")
        
        # 创建 Agent 文件夹及子目录
        agent_path.mkdir(parents=True, exist_ok=True)
        (agent_path / "skills").mkdir(exist_ok=True)
        (agent_path / "prompts").mkdir(exist_ok=True)
        
        # 保存 Agent 配置到 agent.yaml
        now = datetime.now()
        agent_config = {
            "description": agent_create.description,
            "system_prompt": agent_create.system_prompt,
            "model_reference": agent_create.model_reference,
            "enabled_skills": [],
            "enabled_prompts": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        with open(agent_path / AGENT_CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(agent_config, f, allow_unicode=True, sort_keys=False)
        
        return Agent(
            id=f"{catalog_id}_agent_{agent_create.name}",
            name=agent_create.name,
            catalog_id=catalog_id,
            description=agent_create.description,
            path=str(agent_path),
            system_prompt=agent_create.system_prompt,
            model_reference=agent_create.model_reference,
            skills=[],
            prompts=[],
            enabled_skills=[],
            enabled_prompts=[],
            created_at=now,
            updated_at=now,
        )
    
    def update_agent(self, catalog_id: str, agent_name: str, agent_update: AgentUpdate) -> Optional[Agent]:
        """更新 Agent 信息"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        
        if not agent_path.exists():
            return None
        
        agent_config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    agent_config = yaml.safe_load(f) or {}
            except Exception:
                pass
        
        if agent_update.description is not None:
            agent_config["description"] = agent_update.description
        if agent_update.system_prompt is not None:
            agent_config["system_prompt"] = agent_update.system_prompt
        if agent_update.model_reference is not None:
            agent_config["model_reference"] = agent_update.model_reference
        if agent_update.enabled_skills is not None:
            agent_config["enabled_skills"] = agent_update.enabled_skills
        if agent_update.enabled_prompts is not None:
            agent_config["enabled_prompts"] = agent_update.enabled_prompts
        
        agent_config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(agent_config, f, allow_unicode=True, sort_keys=False)
        
        return self._load_agent(catalog_id, agent_path)
    
    def delete_agent(self, catalog_id: str, agent_name: str) -> bool:
        """删除 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        
        if not agent_path.exists():
            return False
        
        shutil.rmtree(agent_path)
        return True
    
    # ==================== Agent Prompts 管理 ====================
    
    def _get_prompt_meta_path(self, prompts_dir: Path, prompt_name: str) -> Path:
        """获取 Prompt 元数据文件路径"""
        base_name = prompt_name.replace(".md", "")
        return prompts_dir / f".{base_name}.meta.yaml"
    
    def _load_prompt_meta(self, meta_path: Path) -> Dict[str, Any]:
        """加载 Prompt 元数据（不再包含 enabled 字段）"""
        if not meta_path.exists():
            return {}
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    
    def _save_prompt_meta(self, meta_path: Path, meta: Dict[str, Any]):
        """保存 Prompt 元数据"""
        with open(meta_path, "w", encoding="utf-8") as f:
            yaml.dump(meta, f, allow_unicode=True, sort_keys=False)
    
    def _get_agent_enabled_prompts(self, catalog_id: str, agent_name: str) -> List[str]:
        """获取 Agent 已启用的 prompts 列表"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        
        if not config_path.exists():
            return []
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f) or {}
            return agent_config.get("enabled_prompts", [])
        except Exception:
            return []
    
    def list_agent_prompts(self, catalog_id: str, agent_name: str) -> Optional[List[Prompt]]:
        """获取 Agent 所有 Prompts 列表"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        if not prompts_dir.exists():
            return None
        
        # 获取已启用的 prompts 列表
        enabled_prompts = self._get_agent_enabled_prompts(catalog_id, agent_name)
        
        prompts = []
        for item in prompts_dir.iterdir():
            if item.is_file() and item.suffix.lower() in [".md", ".markdown"] and not item.name.startswith("."):
                meta_path = self._get_prompt_meta_path(prompts_dir, item.name)
                meta = self._load_prompt_meta(meta_path)
                
                with open(item, "r", encoding="utf-8") as f:
                    content = f.read()
                
                stat = item.stat()
                # 从 agent.yaml 的 enabled_prompts 判断是否启用
                is_enabled = item.name in enabled_prompts
                
                prompts.append(Prompt(
                    name=item.name,
                    content=content,
                    enabled=is_enabled,
                    path=str(item),
                    created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else datetime.fromtimestamp(stat.st_ctime),
                    updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else datetime.fromtimestamp(stat.st_mtime),
                ))
        
        return prompts
    
    def get_agent_prompt_detail(self, catalog_id: str, agent_name: str, prompt_name: str) -> Optional[Prompt]:
        """获取 Agent Prompt 详情（包含元数据）"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        # 尝试查找文件
        prompt_path = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            path = prompts_dir / name
            if path.exists():
                prompt_path = path
                break
        
        if not prompt_path:
            return None
        
        meta_path = self._get_prompt_meta_path(prompts_dir, prompt_path.name)
        meta = self._load_prompt_meta(meta_path)
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 从 agent.yaml 的 enabled_prompts 判断是否启用
        enabled_prompts = self._get_agent_enabled_prompts(catalog_id, agent_name)
        is_enabled = prompt_path.name in enabled_prompts
        
        stat = prompt_path.stat()
        return Prompt(
            name=prompt_path.name,
            content=content,
            enabled=is_enabled,
            path=str(prompt_path),
            created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else datetime.fromtimestamp(stat.st_ctime),
            updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else datetime.fromtimestamp(stat.st_mtime),
        )
    
    def create_agent_prompt(self, catalog_id: str, agent_name: str, prompt_create: PromptCreate) -> bool:
        """创建 Agent Prompt"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        if not prompts_dir.exists():
            return False
        
        prompt_name = prompt_create.name
        if not prompt_name.endswith(".md"):
            prompt_name = f"{prompt_name}.md"
        
        prompt_path = prompts_dir / prompt_name
        if prompt_path.exists():
            raise ValueError(f"Prompt '{prompt_create.name}' 已存在")
        
        # 写入内容文件
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_create.content)
        
        # 写入元数据文件（不再包含 enabled 字段）
        now = datetime.now()
        meta = {
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        meta_path = self._get_prompt_meta_path(prompts_dir, prompt_name)
        self._save_prompt_meta(meta_path, meta)
        
        return True
    
    def update_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str, prompt_update: PromptUpdate) -> bool:
        """更新 Agent Prompt（只更新内容）"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        # 查找文件
        prompt_path = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            path = prompts_dir / name
            if path.exists():
                prompt_path = path
                break
        
        if not prompt_path:
            return False
        
        # 更新内容
        if prompt_update.content is not None:
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt_update.content)
        
        # 更新元数据时间
        meta_path = self._get_prompt_meta_path(prompts_dir, prompt_path.name)
        meta = self._load_prompt_meta(meta_path)
        meta["updated_at"] = datetime.now().isoformat()
        self._save_prompt_meta(meta_path, meta)
        
        return True
    
    def toggle_prompt_enabled(self, catalog_id: str, agent_name: str, prompt_name: str, enabled: bool) -> bool:
        """切换 Prompt 启用状态（在 agent.yaml 的 enabled_prompts 中添加/移除）"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        
        if not config_path.exists():
            return False
        
        # 确保 prompt 文件存在
        prompts_dir = agent_path / "prompts"
        actual_prompt_name = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            if (prompts_dir / name).exists():
                actual_prompt_name = name
                break
        
        if not actual_prompt_name:
            return False
        
        # 读取 agent 配置
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f) or {}
        except Exception:
            agent_config = {}
        
        # 获取/初始化 enabled_prompts 列表
        enabled_prompts = agent_config.get("enabled_prompts", [])
        
        if enabled:
            # 添加到列表
            if actual_prompt_name not in enabled_prompts:
                enabled_prompts.append(actual_prompt_name)
        else:
            # 从列表移除
            if actual_prompt_name in enabled_prompts:
                enabled_prompts.remove(actual_prompt_name)
        
        # 保存更新后的配置
        agent_config["enabled_prompts"] = enabled_prompts
        agent_config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(agent_config, f, allow_unicode=True, sort_keys=False)
        
        return True
    
    def toggle_skill_enabled(self, catalog_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        """切换 Skill 启用状态（在 agent.yaml 的 enabled_skills 中添加/移除）"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        
        if not config_path.exists():
            return False
        
        # 确保 skill 文件存在
        skills_dir = agent_path / "skills"
        if not (skills_dir / skill_name).exists():
            return False
        
        # 读取 agent 配置
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f) or {}
        except Exception:
            agent_config = {}
        
        # 获取/初始化 enabled_skills 列表
        enabled_skills = agent_config.get("enabled_skills", [])
        
        if enabled:
            # 添加到列表
            if skill_name not in enabled_skills:
                enabled_skills.append(skill_name)
        else:
            # 从列表移除
            if skill_name in enabled_skills:
                enabled_skills.remove(skill_name)
        
        # 保存更新后的配置
        agent_config["enabled_skills"] = enabled_skills
        agent_config["updated_at"] = datetime.now().isoformat()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(agent_config, f, allow_unicode=True, sort_keys=False)
        
        return True
        
        return True
    
    def add_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str, content: str) -> bool:
        """添加 Agent Prompt（简化版，保持向后兼容）"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        if not prompts_dir.exists():
            return False
        
        if not prompt_name.endswith(".md"):
            prompt_name = f"{prompt_name}.md"
        
        with open(prompts_dir / prompt_name, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    
    def get_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> Optional[str]:
        """获取 Agent Prompt 内容（简化版，保持向后兼容）"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        for name in [prompt_name, f"{prompt_name}.md"]:
            prompt_path = prompts_dir / name
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
        
        return None
    
    def delete_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> bool:
        """删除 Agent Prompt"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        deleted = False
        for name in [prompt_name, f"{prompt_name}.md"]:
            prompt_path = prompts_dir / name
            if prompt_path.exists():
                prompt_path.unlink()
                deleted = True
                # 删除元数据文件
                meta_path = self._get_prompt_meta_path(prompts_dir, name)
                if meta_path.exists():
                    meta_path.unlink()
                break
        
        return deleted
    
    # ==================== Agent Skills 管理 ====================
    
    def add_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str, content: str) -> bool:
        """添加 Agent Skill 文件"""
        catalog_path = self._get_catalog_path(catalog_id)
        skills_dir = self._get_agents_dir(catalog_path) / agent_name / "skills"
        
        if not skills_dir.exists():
            return False
        
        with open(skills_dir / skill_name, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    
    def get_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> Optional[str]:
        """获取 Agent Skill 内容"""
        catalog_path = self._get_catalog_path(catalog_id)
        skill_path = self._get_agents_dir(catalog_path) / agent_name / "skills" / skill_name
        
        if not skill_path.exists():
            return None
        
        with open(skill_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def delete_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> bool:
        """删除 Agent Skill"""
        catalog_path = self._get_catalog_path(catalog_id)
        skill_path = self._get_agents_dir(catalog_path) / agent_name / "skills" / skill_name
        
        if not skill_path.exists():
            return False
        
        skill_path.unlink()
        return True
    
    # ==================== Model 管理（Schema 级别） ====================
    
    def scan_schema_models(self, catalog_id: str, schema_name: str) -> List[Model]:
        """扫描 Schema 下的所有 Model"""
        models = []
        schema_path = self._get_schema_path(catalog_id, schema_name)
        
        if not schema_path:
            return models
        
        models_dir = schema_path / "models"
        if not models_dir.exists():
            return models
        
        schema_id = f"{catalog_id}_{schema_name}"
        
        for item in models_dir.iterdir():
            if item.is_file() and item.suffix in [".yaml", ".yml"]:
                model = self._load_schema_model(schema_id, item)
                if model:
                    models.append(model)
        
        return models
    
    def _load_schema_model(self, schema_id: str, model_path: Path) -> Optional[Model]:
        """加载单个 Model 配置"""
        try:
            with open(model_path, "r", encoding="utf-8") as f:
                model_meta = yaml.safe_load(f) or {}
            
            model_name = model_path.stem
            created_at = model_meta.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            else:
                created_at = datetime.fromtimestamp(model_path.stat().st_ctime)
            
            updated_at = model_meta.get("updated_at")
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)
            
            return Model(
                id=f"{schema_id}_model_{model_name}",
                name=model_name,
                schema_id=schema_id,
                description=model_meta.get("description"),
                model_type=model_meta.get("model_type", "endpoint"),
                local_provider=model_meta.get("local_provider"),
                local_source=model_meta.get("local_source"),
                volume_reference=model_meta.get("volume_reference"),
                huggingface_repo=model_meta.get("huggingface_repo"),
                huggingface_filename=model_meta.get("huggingface_filename"),
                endpoint_provider=model_meta.get("endpoint_provider"),
                api_base_url=model_meta.get("api_base_url"),
                api_key=model_meta.get("api_key"),
                model_id=model_meta.get("model_id"),
                path=str(model_path),
                created_at=created_at,
                updated_at=updated_at,
            )
        except Exception as e:
            logger.error(f"加载 Model 失败: {model_path}, 错误: {e}")
            return None
    
    def list_models(self, catalog_id: str, schema_name: str) -> List[Model]:
        """获取 Schema 下的所有 Model"""
        return self.scan_schema_models(catalog_id, schema_name)
    
    def get_model(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[Model]:
        """获取指定 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        model_path = schema_path / "models" / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        
        return self._load_schema_model(f"{catalog_id}_{schema_name}", model_path)
    
    def create_model(self, catalog_id: str, schema_name: str, model_create: ModelCreate) -> Model:
        """在 Schema 下创建新的 Model"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise ValueError(f"Schema '{schema_name}' 不存在")
        
        models_dir = schema_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / f"{model_create.name}.yaml"
        if model_path.exists():
            raise ValueError(f"Model '{model_create.name}' 已存在")
        
        now = datetime.now()
        model_meta = {
            "description": model_create.description,
            "model_type": model_create.model_type,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        if model_create.model_type == "local":
            model_meta["local_provider"] = model_create.local_provider
            model_meta["local_source"] = model_create.local_source
            if model_create.local_source == "volume":
                model_meta["volume_reference"] = model_create.volume_reference
            elif model_create.local_source == "huggingface":
                model_meta["huggingface_repo"] = model_create.huggingface_repo
                model_meta["huggingface_filename"] = model_create.huggingface_filename
        else:
            model_meta["endpoint_provider"] = model_create.endpoint_provider
            model_meta["api_base_url"] = model_create.api_base_url
            model_meta["api_key"] = model_create.api_key
            model_meta["model_id"] = model_create.model_id
        
        with open(model_path, "w", encoding="utf-8") as f:
            yaml.dump(model_meta, f, allow_unicode=True, sort_keys=False)
        
        schema_id = f"{catalog_id}_{schema_name}"
        
        return Model(
            id=f"{schema_id}_model_{model_create.name}",
            name=model_create.name,
            schema_id=schema_id,
            description=model_create.description,
            model_type=model_create.model_type,
            local_provider=model_create.local_provider,
            local_source=model_create.local_source,
            volume_reference=model_create.volume_reference,
            huggingface_repo=model_create.huggingface_repo,
            huggingface_filename=model_create.huggingface_filename,
            endpoint_provider=model_create.endpoint_provider,
            api_base_url=model_create.api_base_url,
            api_key=model_create.api_key,
            model_id=model_create.model_id,
            path=str(model_path),
            created_at=now,
            updated_at=now,
        )
    
    def update_model(self, catalog_id: str, schema_name: str, model_name: str, model_update: ModelUpdate) -> Optional[Model]:
        """更新 Model 信息"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        model_path = schema_path / "models" / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        
        model_meta = {}
        try:
            with open(model_path, "r", encoding="utf-8") as f:
                model_meta = yaml.safe_load(f) or {}
        except Exception:
            pass
        
        if model_update.description is not None:
            model_meta["description"] = model_update.description
        if model_update.api_key is not None:
            model_meta["api_key"] = model_update.api_key
        if model_update.api_base_url is not None:
            model_meta["api_base_url"] = model_update.api_base_url
        if model_update.model_id is not None:
            model_meta["model_id"] = model_update.model_id
        
        model_meta["updated_at"] = datetime.now().isoformat()
        
        with open(model_path, "w", encoding="utf-8") as f:
            yaml.dump(model_meta, f, allow_unicode=True, sort_keys=False)
        
        return self._load_schema_model(f"{catalog_id}_{schema_name}", model_path)
    
    def delete_model(self, catalog_id: str, schema_name: str, model_name: str) -> bool:
        """删除 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        
        model_path = schema_path / "models" / f"{model_name}.yaml"
        if not model_path.exists():
            return False
        
        model_path.unlink()
        return True
    
    # ==================== Catalog 导航树 ====================
    
    def get_catalog_tree(self) -> List[CatalogTreeNode]:
        """获取完整的 Catalog 导航树"""
        catalogs = self.discover_catalogs()
        tree = []
        
        for catalog in catalogs:
            catalog_node = CatalogTreeNode(
                id=catalog.id,
                name=catalog.name,
                display_name=catalog.display_name,
                node_type="catalog",
                icon="database",
                readonly=False,
                metadata={
                    "has_connections": catalog.has_connections,
                    "allow_custom_schema": catalog.allow_custom_schema,
                },
            )
            
            # 添加 Agent 子节点
            for agent in catalog.agents:
                agent_node = self._create_agent_tree_node(catalog.id, agent)
                catalog_node.children.append(agent_node)
            
            # 添加 Schema 子节点
            for schema in catalog.schemas:
                schema_node = self._create_schema_tree_node(catalog.id, schema)
                catalog_node.children.append(schema_node)
            
            tree.append(catalog_node)
        
        return tree
    
    def _create_agent_tree_node(self, catalog_id: str, agent: Agent) -> CatalogTreeNode:
        """创建 Agent 树节点"""
        agent_node = CatalogTreeNode(
            id=agent.id,
            name=agent.name,
            display_name=agent.name,
            node_type="agent",
            icon="bot",
            readonly=False,
            metadata={
                "catalog_id": catalog_id,
                "description": agent.description,
                "skills_count": len(agent.skills),
                "prompts_count": len(agent.prompts),
            },
        )
        
        # Skills 文件夹节点
        skills_node = CatalogTreeNode(
            id=f"{agent.id}_skills",
            name="skills",
            display_name="Skills",
            node_type="folder",
            icon="folder",
            readonly=False,
            metadata={"agent_id": agent.id, "catalog_id": catalog_id},
        )
        for skill in agent.skills:
            skills_node.children.append(CatalogTreeNode(
                id=f"{agent.id}_skill_{skill}",
                name=skill,
                display_name=skill,
                node_type="skill",
                icon="code",
                readonly=False,
                metadata={"agent_id": agent.id, "catalog_id": catalog_id, "agent_name": agent.name},
            ))
        agent_node.children.append(skills_node)
        
        # Prompts 文件夹节点
        prompts_node = CatalogTreeNode(
            id=f"{agent.id}_prompts",
            name="prompts",
            display_name="Prompts",
            node_type="folder",
            icon="folder",
            readonly=False,
            metadata={"agent_id": agent.id, "catalog_id": catalog_id},
        )
        for prompt in agent.prompts:
            prompts_node.children.append(CatalogTreeNode(
                id=f"{agent.id}_prompt_{prompt}",
                name=prompt,
                display_name=prompt.replace(".md", ""),
                node_type="prompt",
                icon="file-text",
                readonly=False,
                metadata={"agent_id": agent.id, "catalog_id": catalog_id, "agent_name": agent.name},
            ))
        agent_node.children.append(prompts_node)
        
        return agent_node
    
    def _create_schema_tree_node(self, catalog_id: str, schema: Schema) -> CatalogTreeNode:
        """创建 Schema 树节点"""
        schema_node = CatalogTreeNode(
            id=schema.id,
            name=schema.name,
            display_name=schema.name,
            node_type="schema",
            icon="folder" if schema.source == SchemaSource.LOCAL else "cloud",
            readonly=schema.readonly,
            source=schema.source.value if hasattr(schema.source, 'value') else schema.source,
            metadata={"catalog_id": catalog_id, "connection_name": schema.connection_name},
        )
        
        # 扫描资产
        if schema.path:
            assets = self.scan_assets(catalog_id, schema.name)
            for asset in assets:
                asset_node = CatalogTreeNode(
                    id=asset.id,
                    name=asset.name,
                    display_name=asset.name,
                    node_type=asset.asset_type.value if hasattr(asset.asset_type, 'value') else asset.asset_type,
                    icon=self._get_asset_icon(asset.asset_type),
                    readonly=schema.readonly,
                    metadata={**asset.metadata, "catalog_id": catalog_id, "schema_name": schema.name},
                )
                schema_node.children.append(asset_node)
            
            # 扫描 Models
            models = self.scan_schema_models(catalog_id, schema.name)
            for model in models:
                model_node = CatalogTreeNode(
                    id=model.id,
                    name=model.name,
                    display_name=model.name,
                    node_type="model",
                    icon="cpu",
                    readonly=schema.readonly,
                    metadata={
                        "catalog_id": catalog_id,
                        "schema_name": schema.name,
                        "description": model.description,
                        "model_type": model.model_type,
                        "endpoint_provider": model.endpoint_provider,
                        "local_provider": model.local_provider,
                    },
                )
                schema_node.children.append(model_node)
        
        return schema_node
    
    def _get_asset_icon(self, asset_type: AssetType) -> str:
        """获取资产图标"""
        icon_map = {
            AssetType.TABLE: "table",
            AssetType.VOLUME: "folder-open",
            AssetType.AGENT: "robot",
            AssetType.NOTE: "file-text",
        }
        return icon_map.get(asset_type, "file")


# 全局服务实例
catalog_service = CatalogService()
