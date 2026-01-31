"""
Catalog 服务层
实现基于文件系统的 Catalog 管理

设计原则：
1. 所有实体的基础属性统一存储在 yaml 文件的 baseinfo 节下
2. 各实体特有配置与 baseinfo 同级

baseinfo 标准字段：
- name: 名称
- display_name: 展示名称
- description: 描述
- tags: 标签列表
- owner: 所有者
- created_at: 创建时间
- updated_at: 更新时间
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
)
from app.models.catalog import (
    Catalog,
    CatalogCreate,
    CatalogUpdate,
    CatalogTreeNode,
    ConnectionConfig,
    Schema,
    SchemaCreate,
    SchemaUpdate,
    SchemaType,
    Asset,
    AssetCreate,
    AssetType,
    EntityType,
    Agent,
    AgentCreate,
    AgentUpdate,
    AgentLLMConfig,
    AgentInstruction,
    AgentRouting,
    AgentCapabilities,
    AgentGovernance,
    AgentNativeSkill,
    AgentPromptTemplate,
    AgentMCPTool,
    AgentHumanInTheLoop,
    Model,
    ModelCreate,
    ModelUpdate,
    Prompt,
    PromptCreate,
    PromptUpdate,
)
from app.models.metadata import SyncResult

logger = logging.getLogger(__name__)

# 资产类型目录映射
ASSET_TYPE_DIRS = {
    AssetType.TABLE: TABLES_DIR,
    AssetType.VOLUME: VOLUMES_DIR,
    AssetType.AGENT: AGENTS_DIR,
    AssetType.NOTE: NOTES_DIR,
}


class CatalogService:
    """Catalog 服务类"""
    
    def __init__(self):
        self.catalogs_dir = settings.CATALOGS_DIR
        self._ensure_catalogs_dir()
    
    def _ensure_catalogs_dir(self):
        """确保 Catalogs 目录存在"""
        self.catalogs_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== 工具方法 ====================
    
    def _get_catalog_path(self, catalog_name: str) -> Path:
        return self.catalogs_dir / catalog_name
    
    def _get_config_path(self, catalog_path: Path) -> Path:
        return catalog_path / CATALOG_CONFIG_FILE
    
    def _get_agents_dir(self, catalog_path: Path) -> Path:
        return catalog_path / AGENTS_DIR
    
    def _get_schemas_dir(self, catalog_path: Path) -> Path:
        return catalog_path / SCHEMAS_DIR
    
    def _get_schema_path(self, catalog_id: str, schema_name: str) -> Optional[Path]:
        catalog_path = self._get_catalog_path(catalog_id)
        schema_path = self._get_schemas_dir(catalog_path) / schema_name
        return schema_path if schema_path.exists() else None
    
    def _now_iso(self) -> str:
        return datetime.now().isoformat()
    
    def _load_yaml(self, path: Path) -> Optional[Dict[str, Any]]:
        """加载 YAML 文件"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载 YAML 失败 {path}: {e}")
            return None
    
    def _save_yaml(self, path: Path, data: Dict[str, Any]):
        """保存 YAML 文件"""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    
    def _read_file(self, path: Path) -> Optional[str]:
        """读取文件内容"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {path}: {e}")
            return None
    
    def _create_baseinfo(self, name: str, display_name: str = None, description: str = None, 
                         tags: List[str] = None, owner: str = "admin") -> Dict[str, Any]:
        """创建标准 baseinfo 字典"""
        now = self._now_iso()
        return {
            "name": name,
            "display_name": display_name or name,
            "description": description or "",
            "tags": tags or [],
            "owner": owner,
            "created_at": now,
            "updated_at": now,
        }
    
    def _extract_baseinfo(self, config: Dict[str, Any], path: Path = None) -> Dict[str, Any]:
        """从配置中提取 baseinfo，兼容新旧格式"""
        baseinfo = config.get("baseinfo", {})
        # 如果没有 baseinfo 节，尝试从顶层提取
        if not baseinfo:
            baseinfo = {
                "name": config.get("name") or config.get("catalog_id") or (path.name if path else ""),
                "display_name": config.get("display_name") or config.get("name") or (path.name if path else ""),
                "description": config.get("description") or config.get("comment") or "",
                "tags": config.get("tags", []),
                "owner": config.get("owner", "admin"),
                "created_at": config.get("created_at"),
                "updated_at": config.get("updated_at"),
            }
        return baseinfo
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """解析日期时间"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None
    
    # ==================== Catalog 操作 ====================
    
    def discover_catalogs(self) -> List[Catalog]:
        """发现所有 Catalog"""
        catalogs = []
        if not self.catalogs_dir.exists():
            return catalogs
        
        for item in self.catalogs_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                catalog = self._load_catalog(item)
                if catalog:
                    catalogs.append(catalog)
        return catalogs
    
    def _load_catalog(self, catalog_path: Path) -> Optional[Catalog]:
        """加载 Catalog"""
        config = self._load_yaml(self._get_config_path(catalog_path))
        
        if config is None:
            # 创建默认配置
            baseinfo = self._create_baseinfo(catalog_path.name)
            config = {"baseinfo": baseinfo}
            self._save_yaml(self._get_config_path(catalog_path), config)
        
        baseinfo = self._extract_baseinfo(config, catalog_path)
        
        return Catalog(
            id=baseinfo.get("name") or catalog_path.name,
            name=catalog_path.name,
            display_name=baseinfo.get("display_name") or catalog_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            entity_type=EntityType.CATALOG,
            path=str(catalog_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            schemas=self._scan_schemas(catalog_path, catalog_path.name),
            agents=self._scan_agents(catalog_path, catalog_path.name),
        )
    
    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        """获取 Catalog"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        return self._load_catalog(catalog_path)
    
    def create_catalog(self, catalog_create: CatalogCreate) -> Catalog:
        """创建 Catalog"""
        catalog_path = self._get_catalog_path(catalog_create.name)
        if catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_create.name}' 已存在")
        
        # 创建目录
        catalog_path.mkdir(parents=True, exist_ok=True)
        self._get_agents_dir(catalog_path).mkdir(exist_ok=True)
        self._get_schemas_dir(catalog_path).mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(
            catalog_create.name,
            catalog_create.display_name,
            catalog_create.description,
            catalog_create.tags,
            catalog_create.owner or "admin",
        )
        self._save_yaml(self._get_config_path(catalog_path), {"baseinfo": baseinfo})
        
        return self._load_catalog(catalog_path)
    
    def update_catalog(self, catalog_id: str, update: CatalogUpdate) -> Optional[Catalog]:
        """更新 Catalog"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        
        config = self._load_yaml(self._get_config_path(catalog_path)) or {}
        baseinfo = self._extract_baseinfo(config, catalog_path)
        
        if update.display_name is not None:
            baseinfo["display_name"] = update.display_name
        if update.description is not None:
            baseinfo["description"] = update.description
        if update.tags is not None:
            baseinfo["tags"] = update.tags
        baseinfo["updated_at"] = self._now_iso()
        
        config["baseinfo"] = baseinfo
        self._save_yaml(self._get_config_path(catalog_path), config)
        
        return self._load_catalog(catalog_path)
    
    def delete_catalog(self, catalog_id: str) -> bool:
        """删除 Catalog"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return False
        shutil.rmtree(catalog_path)
        return True
    
    # ==================== Schema 操作 ====================
    
    def _scan_schemas(self, catalog_path: Path, catalog_id: str) -> List[Schema]:
        """扫描 Schema"""
        schemas = []
        schemas_dir = self._get_schemas_dir(catalog_path)
        
        if not schemas_dir.exists():
            return schemas
        
        for item in schemas_dir.iterdir():
            if item.is_dir() and not item.name.startswith(".") and item.name != "__pycache__":
                schema = self._load_schema(catalog_id, item)
                if schema:
                    schemas.append(schema)
        return schemas
    
    def _load_schema(self, catalog_id: str, schema_path: Path) -> Optional[Schema]:
        """加载 Schema"""
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE) or {}
        baseinfo = self._extract_baseinfo(config, schema_path)
        
        # 解析连接配置
        connection = None
        if config.get("connection"):
            connection = ConnectionConfig(**config["connection"])
        
        schema_type = config.get("schema_type", "local")
        
        return Schema(
            id=f"{catalog_id}_{schema_path.name}",
            name=schema_path.name,
            display_name=baseinfo.get("display_name") or schema_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            catalog_id=catalog_id,
            entity_type=EntityType.SCHEMA,
            schema_type=schema_type,
            connection=connection,
            path=str(schema_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            synced_at=self._parse_datetime(config.get("synced_at")),
        )
    
    def get_schemas(self, catalog_id: str) -> List[Schema]:
        """获取 Schema 列表"""
        catalog = self.get_catalog(catalog_id)
        return catalog.schemas if catalog else []
    
    def get_schema_config_content(self, catalog_id: str, schema_name: str) -> Optional[str]:
        """获取 Schema 配置内容"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        return self._read_file(schema_path / SCHEMA_CONFIG_FILE)
    
    def create_schema(self, catalog_id: str, schema_create: SchemaCreate) -> Schema:
        """创建 Schema"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        schema_type = schema_create.schema_type or "local"
        if schema_type == "external" and not schema_create.connection:
            raise ValueError("External 类型必须配置数据库连接")
        
        connection = schema_create.connection if schema_type == "external" else None
        
        schemas_dir = self._get_schemas_dir(catalog_path)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        
        schema_path = schemas_dir / schema_create.name
        if schema_path.exists():
            raise ValueError(f"Schema '{schema_create.name}' 已存在")
        
        # 创建目录结构
        schema_path.mkdir(parents=True, exist_ok=True)
        for dir_name in ["models", "tables", "functions", "volumes"]:
            (schema_path / dir_name).mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(
            schema_create.name,
            schema_create.display_name,
            schema_create.description,
            schema_create.tags,
            schema_create.owner or "admin",
        )
        
        config = {
            "baseinfo": baseinfo,
            "schema_type": schema_type,
        }
        
        if connection:
            config["connection"] = connection.model_dump()
        
        self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        
        # 同步外部元数据
        if connection:
            sync_result = self._sync_schema_metadata(schema_path, catalog_id, schema_create.name, connection)
            if sync_result.success:
                config["synced_at"] = self._now_iso()
                self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        
        return self._load_schema(catalog_id, schema_path)
    
    def update_schema(self, catalog_id: str, schema_name: str, update: SchemaUpdate) -> Optional[Schema]:
        """更新 Schema"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE) or {}
        baseinfo = self._extract_baseinfo(config, schema_path)
        
        if update.display_name is not None:
            baseinfo["display_name"] = update.display_name
        if update.description is not None:
            baseinfo["description"] = update.description
        if update.tags is not None:
            baseinfo["tags"] = update.tags
        baseinfo["updated_at"] = self._now_iso()
        
        if update.connection is not None and config.get("schema_type") == "external":
            config["connection"] = update.connection.model_dump()
        
        config["baseinfo"] = baseinfo
        self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        
        return self._load_schema(catalog_id, schema_path)
    
    def delete_schema(self, catalog_id: str, schema_name: str) -> bool:
        """删除 Schema"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        shutil.rmtree(schema_path)
        return True
    
    def _sync_schema_metadata(self, schema_path: Path, catalog_id: str, schema_name: str, 
                              connection: ConnectionConfig) -> SyncResult:
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
        result = self._sync_schema_metadata(schema_path, catalog_id, schema_name, connection)
        
        if result.success:
            config["synced_at"] = self._now_iso()
            self._save_yaml(schema_path / SCHEMA_CONFIG_FILE, config)
        
        return result
    
    # ==================== Asset 操作 ====================
    
    def _get_asset_type_dir(self, asset_type: AssetType) -> str:
        """获取资产类型目录"""
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
        """扫描 Schema 下的资产"""
        assets = []
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return assets
        
        config = self._load_yaml(schema_path / SCHEMA_CONFIG_FILE)
        is_external = config and config.get("schema_type") == "external"
        
        for asset_type, dir_name in ASSET_TYPE_DIRS.items():
            type_dir = schema_path / dir_name
            if type_dir.exists() and type_dir.is_dir():
                assets.extend(self._scan_asset_dir(catalog_id, schema_name, type_dir, asset_type, is_external))
        
        functions_dir = schema_path / FUNCTIONS_DIR
        if functions_dir.exists():
            assets.extend(self._scan_asset_dir(catalog_id, schema_name, functions_dir, AssetType.AGENT, is_external))
        
        return assets
    
    def _scan_asset_dir(self, catalog_id: str, schema_name: str, type_dir: Path, 
                        asset_type: AssetType, is_external: bool) -> List[Asset]:
        """扫描资产目录"""
        assets = []
        
        for item in type_dir.iterdir():
            if item.name.startswith("."):
                continue
            
            if item.suffix == ".yaml":
                asset_config = self._load_yaml(item) or {}
                baseinfo = self._extract_baseinfo(asset_config, item)
                
                metadata = {k: v for k, v in asset_config.items() if k not in ["baseinfo", "name", "created_at", "updated_at"]}
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
            if asset_file.exists():
                return self._read_file(asset_file)
        return None
    
    def create_asset(self, catalog_id: str, schema_name: str, asset_create: AssetCreate) -> Asset:
        """创建 Asset"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise FileNotFoundError(f"Schema '{schema_name}' 不存在")
        
        type_dir = schema_path / self._get_asset_type_dir(asset_create.asset_type)
        type_dir.mkdir(parents=True, exist_ok=True)
        
        asset_path = type_dir / f"{asset_create.name}.yaml"
        if asset_path.exists():
            raise ValueError(f"资产 '{asset_create.name}' 已存在")
        
        baseinfo = self._create_baseinfo(
            asset_create.name,
            asset_create.display_name,
            asset_create.description,
            asset_create.tags,
            asset_create.owner or "admin",
        )
        
        asset_config = {
            "baseinfo": baseinfo,
            "asset_type": asset_create.asset_type.value if hasattr(asset_create.asset_type, 'value') else asset_create.asset_type,
            "source": "local",
        }
        
        # 添加类型特有字段
        if asset_create.asset_type == AssetType.VOLUME or asset_create.asset_type == "volume":
            asset_config["volume_type"] = asset_create.volume_type or "local"
            if asset_create.volume_type == "local":
                asset_config["storage_location"] = asset_create.storage_location
            elif asset_create.volume_type == "s3":
                asset_config.update({
                    "s3_endpoint": asset_create.s3_endpoint,
                    "s3_bucket": asset_create.s3_bucket,
                    "s3_access_key": asset_create.s3_access_key,
                    "s3_secret_key": asset_create.s3_secret_key,
                })
        elif asset_create.asset_type == AssetType.TABLE or asset_create.asset_type == "table":
            asset_config["format"] = asset_create.format
            asset_config["columns"] = []
        
        self._save_yaml(asset_path, asset_config)
        
        return Asset(
            id=f"{catalog_id}_{schema_name}_{asset_create.name}",
            name=asset_create.name,
            display_name=baseinfo["display_name"],
            description=baseinfo["description"],
            tags=baseinfo["tags"],
            schema_id=f"{catalog_id}_{schema_name}",
            asset_type=asset_create.asset_type,
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
    
    def preview_table_data(self, catalog_id: str, schema_name: str, table_name: str, 
                           limit: int = 100, offset: int = 0) -> Dict[str, Any]:
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
    
    # ==================== Agent 操作 ====================
    
    def _scan_agents(self, catalog_path: Path, catalog_id: str) -> List[Agent]:
        """扫描 Agent"""
        agents = []
        agents_dir = self._get_agents_dir(catalog_path)
        
        if not agents_dir.exists():
            return agents
        
        for item in agents_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                agent = self._load_agent(catalog_id, item)
                if agent:
                    agents.append(agent)
        return agents
    
    def _load_agent(self, catalog_id: str, agent_path: Path) -> Optional[Agent]:
        """加载 Agent"""
        config = self._load_yaml(agent_path / AGENT_CONFIG_FILE) or {}
        baseinfo = self._extract_baseinfo(config, agent_path)
        
        # 兼容 metadata 节
        if config.get("metadata"):
            meta = config["metadata"]
            if not baseinfo.get("display_name") or baseinfo["display_name"] == agent_path.name:
                baseinfo["display_name"] = meta.get("name") or meta.get("display_name") or agent_path.name
            if not baseinfo.get("description"):
                baseinfo["description"] = meta.get("description")
        
        # 扫描 skills 目录（每个 skill 是一个子目录）
        skills = []
        skills_dir = agent_path / "skills"
        if skills_dir.exists():
            skills = [f.name for f in skills_dir.iterdir() if f.is_dir() and not f.name.startswith(".")]
        
        # 扫描 prompts 目录
        prompts = []
        prompts_dir = agent_path / "prompts"
        if prompts_dir.exists():
            prompts = [f.name for f in prompts_dir.iterdir() 
                       if f.is_file() and f.suffix.lower() in [".md", ".markdown"] and not f.name.startswith(".")]
        
        # 解析 llm_config
        llm_config = None
        if config.get("llm_config"):
            lc = config["llm_config"]
            llm_config = AgentLLMConfig(
                llm_model=lc.get("llm_model"),
                temperature=lc.get("temperature", 0.2),
                max_tokens=lc.get("max_tokens", 2000),
                response_format=lc.get("response_format", "text"),
            )
        
        # 解析 instruction
        instruction = None
        if config.get("instruction"):
            inst = config["instruction"]
            user_prompts = [AgentPromptTemplate(name=p.get("name") if isinstance(p, dict) else p) 
                           for p in inst.get("user_prompt_templates", [])]
            instruction = AgentInstruction(
                system_prompt=inst.get("system_prompt"),
                user_prompt_template=inst.get("user_prompt_template"),
                user_prompt_templates=user_prompts,
            )
        
        # 解析 routing
        routing = None
        if config.get("routing"):
            r = config["routing"]
            routing = AgentRouting(
                trigger_keywords=r.get("trigger_keywords", []),
                required_context_keys=r.get("required_context_keys", []),
                next_possible_agents=r.get("next_possible_agents", []),
            )
        
        # 解析 capabilities
        capabilities = None
        if config.get("capabilities"):
            c = config["capabilities"]
            native_skills = [AgentNativeSkill(name=s.get("name") if isinstance(s, dict) else s) 
                           for s in c.get("native_skills", [])]
            mcp_tools = [AgentMCPTool(server_id=t.get("server_id", ""), tools=t.get("tools", []))
                        for t in c.get("mcp_tools", [])]
            capabilities = AgentCapabilities(native_skills=native_skills, mcp_tools=mcp_tools)
        
        # 解析 governance
        governance = None
        if config.get("governance"):
            g = config["governance"]
            hitl = None
            if g.get("human_in_the_loop"):
                hitl = AgentHumanInTheLoop(trigger=g["human_in_the_loop"].get("trigger"))
            governance = AgentGovernance(
                human_in_the_loop=hitl,
                termination_criteria=g.get("termination_criteria"),
            )
        
        return Agent(
            id=f"{catalog_id}_agent_{agent_path.name}",
            name=agent_path.name,
            display_name=baseinfo.get("display_name") or agent_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            catalog_id=catalog_id,
            entity_type=EntityType.AGENT,
            path=str(agent_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            llm_config=llm_config,
            instruction=instruction,
            routing=routing,
            capabilities=capabilities,
            governance=governance,
            skills=skills,
            prompts=prompts,
        )
    
    def list_agents(self, catalog_id: str) -> List[Agent]:
        """获取 Agent 列表"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return []
        return self._scan_agents(catalog_path, catalog_id)
    
    def get_agent(self, catalog_id: str, agent_name: str) -> Optional[Agent]:
        """获取 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        if not agent_path.exists():
            return None
        return self._load_agent(catalog_id, agent_path)
    
    def get_agent_config_content(self, catalog_id: str, agent_name: str) -> Optional[str]:
        """获取 Agent 配置内容"""
        catalog_path = self._get_catalog_path(catalog_id)
        config_path = self._get_agents_dir(catalog_path) / agent_name / AGENT_CONFIG_FILE
        return self._read_file(config_path)
    
    def create_agent(self, catalog_id: str, agent_create: AgentCreate) -> Agent:
        """创建 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        if not catalog_path.exists():
            raise ValueError(f"Catalog '{catalog_id}' 不存在")
        
        agents_dir = self._get_agents_dir(catalog_path)
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_path = agents_dir / agent_create.name
        if agent_path.exists():
            raise ValueError(f"Agent '{agent_create.name}' 已存在")
        
        # 创建目录结构
        agent_path.mkdir(parents=True, exist_ok=True)
        (agent_path / "skills").mkdir(exist_ok=True)
        (agent_path / "prompts").mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(
            agent_create.name,
            agent_create.display_name,
            agent_create.description,
            agent_create.tags,
            agent_create.owner or "admin",
        )
        
        config = {
            "baseinfo": baseinfo,
            "llm_config": {
                "llm_model": "",
                "temperature": 0.2,
                "max_tokens": 2000,
                "response_format": "text",
            },
            "instruction": {
                "system_prompt": "",
                "user_prompt_template": "",
                "user_prompt_templates": [],
            },
            "routing": {
                "trigger_keywords": [],
                "required_context_keys": [],
                "next_possible_agents": [],
            },
            "capabilities": {
                "native_skills": [],
                "mcp_tools": [],
            },
            "governance": {
                "human_in_the_loop": {"trigger": "on_error"},
                "termination_criteria": "",
            },
        }
        
        self._save_yaml(agent_path / AGENT_CONFIG_FILE, config)
        
        return self._load_agent(catalog_id, agent_path)
    
    def update_agent(self, catalog_id: str, agent_name: str, update: AgentUpdate) -> Optional[Agent]:
        """更新 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        
        if not agent_path.exists():
            return None
        
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, agent_path)
        
        # 更新 baseinfo
        if update.display_name is not None:
            baseinfo["display_name"] = update.display_name
        if update.description is not None:
            baseinfo["description"] = update.description
        if update.tags is not None:
            baseinfo["tags"] = update.tags
        baseinfo["updated_at"] = self._now_iso()
        config["baseinfo"] = baseinfo
        
        # 更新 llm_config
        if update.llm_config is not None:
            lc = config.get("llm_config", {})
            if update.llm_config.llm_model is not None:
                lc["llm_model"] = update.llm_config.llm_model
            if update.llm_config.temperature is not None:
                lc["temperature"] = update.llm_config.temperature
            if update.llm_config.max_tokens is not None:
                lc["max_tokens"] = update.llm_config.max_tokens
            if update.llm_config.response_format is not None:
                lc["response_format"] = update.llm_config.response_format
            config["llm_config"] = lc
        
        # 更新 instruction
        if update.instruction is not None:
            inst = config.get("instruction", {})
            if update.instruction.system_prompt is not None:
                inst["system_prompt"] = update.instruction.system_prompt
            if update.instruction.user_prompt_template is not None:
                inst["user_prompt_template"] = update.instruction.user_prompt_template
            if update.instruction.user_prompt_templates is not None:
                inst["user_prompt_templates"] = [{"name": p.name} for p in update.instruction.user_prompt_templates]
            config["instruction"] = inst
        
        # 更新 routing
        if update.routing is not None:
            r = config.get("routing", {})
            if update.routing.trigger_keywords is not None:
                r["trigger_keywords"] = update.routing.trigger_keywords
            if update.routing.required_context_keys is not None:
                r["required_context_keys"] = update.routing.required_context_keys
            if update.routing.next_possible_agents is not None:
                r["next_possible_agents"] = update.routing.next_possible_agents
            config["routing"] = r
        
        # 更新 capabilities
        if update.capabilities is not None:
            c = config.get("capabilities", {})
            if update.capabilities.native_skills is not None:
                c["native_skills"] = [{"name": s.name} for s in update.capabilities.native_skills]
            if update.capabilities.mcp_tools is not None:
                c["mcp_tools"] = [{"server_id": t.server_id, "tools": t.tools} for t in update.capabilities.mcp_tools]
            config["capabilities"] = c
        
        # 更新 governance
        if update.governance is not None:
            g = config.get("governance", {})
            if update.governance.human_in_the_loop is not None:
                g["human_in_the_loop"] = {"trigger": update.governance.human_in_the_loop.trigger}
            if update.governance.termination_criteria is not None:
                g["termination_criteria"] = update.governance.termination_criteria
            config["governance"] = g
        
        self._save_yaml(config_path, config)
        
        return self._load_agent(catalog_id, agent_path)
    
    def delete_agent(self, catalog_id: str, agent_name: str) -> bool:
        """删除 Agent"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        if not agent_path.exists():
            return False
        shutil.rmtree(agent_path)
        return True
    
    # ==================== Prompt 操作 ====================
    
    def _get_enabled_prompts(self, catalog_id: str, agent_name: str) -> List[str]:
        """获取启用的 prompts"""
        catalog_path = self._get_catalog_path(catalog_id)
        config_path = self._get_agents_dir(catalog_path) / agent_name / AGENT_CONFIG_FILE
        config = self._load_yaml(config_path) or {}
        
        templates = config.get("instruction", {}).get("user_prompt_templates", [])
        return [p.get("name") if isinstance(p, dict) else p for p in templates]
    
    def list_agent_prompts(self, catalog_id: str, agent_name: str) -> Optional[List[Prompt]]:
        """获取 Agent prompts 列表"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        if not prompts_dir.exists():
            return None
        
        enabled = self._get_enabled_prompts(catalog_id, agent_name)
        prompts = []
        
        for item in prompts_dir.iterdir():
            if item.is_file() and item.suffix.lower() in [".md", ".markdown"] and not item.name.startswith("."):
                content = self._read_file(item) or ""
                meta_path = prompts_dir / f".{item.stem}.meta.yaml"
                meta = self._load_yaml(meta_path) or {}
                
                prompts.append(Prompt(
                    name=item.name,
                    display_name=meta.get("display_name") or item.stem,
                    description=meta.get("description"),
                    tags=meta.get("tags", []),
                    entity_type=EntityType.PROMPT,
                    content=content,
                    enabled=item.name in enabled,
                    path=str(item),
                    created_at=self._parse_datetime(meta.get("created_at")),
                    updated_at=self._parse_datetime(meta.get("updated_at")),
                ))
        
        return prompts
    
    def get_agent_prompt_detail(self, catalog_id: str, agent_name: str, prompt_name: str) -> Optional[Prompt]:
        """获取 Prompt 详情"""
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
            return None
        
        content = self._read_file(prompt_path) or ""
        meta_path = prompts_dir / f".{prompt_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}
        enabled = self._get_enabled_prompts(catalog_id, agent_name)
        
        return Prompt(
            name=prompt_path.name,
            display_name=meta.get("display_name") or prompt_path.stem,
            description=meta.get("description"),
            tags=meta.get("tags", []),
            entity_type=EntityType.PROMPT,
            content=content,
            enabled=prompt_path.name in enabled,
            path=str(prompt_path),
            created_at=self._parse_datetime(meta.get("created_at")),
            updated_at=self._parse_datetime(meta.get("updated_at")),
        )
    
    def create_agent_prompt(self, catalog_id: str, agent_name: str, prompt_create: PromptCreate) -> bool:
        """创建 Prompt"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        if not prompts_dir.exists():
            return False
        
        name = prompt_create.name if prompt_create.name.endswith(".md") else f"{prompt_create.name}.md"
        prompt_path = prompts_dir / name
        
        if prompt_path.exists():
            raise ValueError(f"Prompt '{prompt_create.name}' 已存在")
        
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt_create.content)
        
        meta = {"created_at": self._now_iso(), "updated_at": self._now_iso()}
        self._save_yaml(prompts_dir / f".{prompt_path.stem}.meta.yaml", meta)
        
        return True
    
    def update_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str, 
                            update: PromptUpdate) -> bool:
        """更新 Prompt"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        prompt_path = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            path = prompts_dir / name
            if path.exists():
                prompt_path = path
                break
        
        if not prompt_path:
            return False
        
        if update.content is not None:
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(update.content)
        
        meta_path = prompts_dir / f".{prompt_path.stem}.meta.yaml"
        meta = self._load_yaml(meta_path) or {}
        meta["updated_at"] = self._now_iso()
        self._save_yaml(meta_path, meta)
        
        return True
    
    def toggle_prompt_enabled(self, catalog_id: str, agent_name: str, prompt_name: str, enabled: bool) -> bool:
        """切换 Prompt 启用状态"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        prompts_dir = agent_path / "prompts"
        
        if not config_path.exists():
            return False
        
        # 查找实际文件名
        actual_name = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            if (prompts_dir / name).exists():
                actual_name = name
                break
        
        if not actual_name:
            return False
        
        config = self._load_yaml(config_path) or {}
        if "instruction" not in config:
            config["instruction"] = {}
        
        templates = config["instruction"].get("user_prompt_templates", [])
        names = [p.get("name") if isinstance(p, dict) else p for p in templates]
        
        if enabled and actual_name not in names:
            templates.append({"name": actual_name})
        elif not enabled:
            templates = [p for p in templates if (p.get("name") if isinstance(p, dict) else p) != actual_name]
        
        config["instruction"]["user_prompt_templates"] = templates
        config["baseinfo"] = self._extract_baseinfo(config, agent_path)
        config["baseinfo"]["updated_at"] = self._now_iso()
        
        self._save_yaml(config_path, config)
        return True
    
    def delete_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> bool:
        """删除 Prompt"""
        catalog_path = self._get_catalog_path(catalog_id)
        prompts_dir = self._get_agents_dir(catalog_path) / agent_name / "prompts"
        
        prompt_path = None
        for name in [prompt_name, f"{prompt_name}.md"]:
            path = prompts_dir / name
            if path.exists():
                prompt_path = path
                break
        
        if not prompt_path:
            return False
        
        prompt_path.unlink()
        meta_path = prompts_dir / f".{prompt_path.stem}.meta.yaml"
        if meta_path.exists():
            meta_path.unlink()
        
        return True
    
    # ==================== Skill 操作 ====================
    
    def get_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取 Skill 内容和路径"""
        catalog_path = self._get_catalog_path(catalog_id)
        skill_path = self._get_agents_dir(catalog_path) / agent_name / "skills" / skill_name
        
        # skill_path 是一个目录，需要读取其中的 SKILL.md 文件
        if not skill_path.exists() or not skill_path.is_dir():
            return None
        
        skill_md_path = skill_path / "SKILL.md"
        content = self._read_file(skill_md_path)
        if content is None:
            content = ""  # SKILL.md 可能不存在，返回空内容
        
        return {
            "content": content,
            "path": str(skill_path)
        }
    
    def delete_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> bool:
        """删除 Skill（整个目录）"""
        import shutil
        catalog_path = self._get_catalog_path(catalog_id)
        skill_path = self._get_agents_dir(catalog_path) / agent_name / "skills" / skill_name
        
        if not skill_path.exists():
            return False
        
        if skill_path.is_dir():
            shutil.rmtree(skill_path)
        else:
            skill_path.unlink()
        return True
    
    def toggle_skill_enabled(self, catalog_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        """切换 Skill 启用状态"""
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        config_path = agent_path / AGENT_CONFIG_FILE
        skills_dir = agent_path / "skills"
        
        if not config_path.exists() or not (skills_dir / skill_name).exists():
            return False
        
        config = self._load_yaml(config_path) or {}
        if "capabilities" not in config:
            config["capabilities"] = {}
        
        skills = config["capabilities"].get("native_skills", [])
        names = [s.get("name") if isinstance(s, dict) else s for s in skills]
        
        if enabled and skill_name not in names:
            skills.append({"name": skill_name})
        elif not enabled:
            skills = [s for s in skills if (s.get("name") if isinstance(s, dict) else s) != skill_name]
        
        config["capabilities"]["native_skills"] = skills
        config["baseinfo"] = self._extract_baseinfo(config, agent_path)
        config["baseinfo"]["updated_at"] = self._now_iso()
        
        self._save_yaml(config_path, config)
        return True
    
    def _parse_skill_md_frontmatter(self, skill_md_path: Path) -> Dict[str, str]:
        """
        解析 SKILL.md 文件的 YAML frontmatter
        
        SKILL.md 格式示例:
        ---
        name: skill-creator
        description: Guide for creating effective skills...
        ---
        
        Args:
            skill_md_path: SKILL.md 文件路径
        
        Returns:
            Dict 包含 name, description 等字段，解析失败返回空字典
        """
        import re
        
        try:
            content = skill_md_path.read_text(encoding='utf-8')
            
            # 匹配 YAML frontmatter: 以 --- 开头和结尾的块
            frontmatter_pattern = r'^---\s*\n(.*?)\n---'
            match = re.match(frontmatter_pattern, content, re.DOTALL)
            
            if not match:
                logger.warning(f"SKILL.md 未找到有效的 frontmatter: {skill_md_path}")
                return {}
            
            frontmatter_text = match.group(1)
            
            # 解析 YAML frontmatter
            result = {}
            for line in frontmatter_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    # 只分割第一个冒号，保留 description 中可能包含的冒号
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        result[key] = value
            
            logger.info(f"解析 SKILL.md frontmatter: {result}")
            return result
            
        except Exception as e:
            logger.error(f"解析 SKILL.md 失败: {e}")
            return {}

    def import_skill_from_zip(self, catalog_id: str, agent_name: str, zip_file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        """
        从 zip 文件导入 Skill
        
        本地桌面应用场景：直接从本地路径复制并解压 zip 文件到 skills 目录
        
        要求：
        - zip 包解压后必须包含 SKILL.md 文件
        - SKILL.md 必须包含 YAML frontmatter，格式如：
          ---
          name: skill-name
          description: Skill description...
          ---
        
        Args:
            catalog_id: Catalog ID
            agent_name: Agent 名称
            zip_file_path: 本地 zip 文件路径
            original_filename: 原始文件名（备用）
        
        Returns:
            Dict 包含 success, skill_name, message 等字段
        """
        import zipfile
        import tempfile
        
        # 确保 zip_file_path 是 Path 对象
        zip_file_path = Path(zip_file_path)
        
        catalog_path = self._get_catalog_path(catalog_id)
        agent_path = self._get_agents_dir(catalog_path) / agent_name
        skills_dir = agent_path / "skills"
        
        if not agent_path.exists():
            return {"success": False, "message": f"Agent '{agent_name}' 不存在"}
        
        # 确保 skills 目录存在
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 验证源 zip 文件存在且有效
            if not zip_file_path.exists():
                return {"success": False, "message": f"zip 文件不存在: {zip_file_path}"}
            
            if not zipfile.is_zipfile(str(zip_file_path)):
                return {"success": False, "message": "无效的 zip 文件"}
            
            # 先解压到临时目录进行验证
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                with zipfile.ZipFile(str(zip_file_path), 'r') as zip_ref:
                    namelist = zip_ref.namelist()
                    
                    if not namelist:
                        return {"success": False, "message": "zip 文件为空"}
                    
                    logger.info(f"ZIP 文件内容: {namelist[:10]}...")
                    
                    # 解压到临时目录
                    zip_ref.extractall(temp_path)
                
                # 检查解压后的结构，找到实际内容目录
                # 获取所有顶级项（忽略 __MACOSX 等）
                top_level_items = [
                    item for item in temp_path.iterdir()
                    if not item.name.startswith('__MACOSX') and not item.name.startswith('._')
                ]
                
                logger.info(f"顶级目录/文件: {[item.name for item in top_level_items]}")
                
                # 确定实际内容目录
                if len(top_level_items) == 1 and top_level_items[0].is_dir():
                    # 单一根目录，内容在其中
                    content_dir = top_level_items[0]
                else:
                    # 多个顶级项或直接是文件，临时目录就是内容目录
                    content_dir = temp_path
                
                # 查找 SKILL.md 文件
                skill_md_path = content_dir / "SKILL.md"
                if not skill_md_path.exists():
                    # 尝试不区分大小写查找
                    skill_md_candidates = [
                        f for f in content_dir.iterdir() 
                        if f.name.upper() == "SKILL.MD"
                    ]
                    if skill_md_candidates:
                        skill_md_path = skill_md_candidates[0]
                    else:
                        return {
                            "success": False, 
                            "message": "无效的 Skill 包：缺少 SKILL.md 文件"
                        }
                
                # 解析 SKILL.md 获取 name 和 description
                frontmatter = self._parse_skill_md_frontmatter(skill_md_path)
                
                if not frontmatter.get('name'):
                    return {
                        "success": False,
                        "message": "无效的 SKILL.md：缺少 name 字段"
                    }
                
                # 从 frontmatter 获取 skill 名称
                skill_name = frontmatter['name']
                skill_description = frontmatter.get('description', f"从 zip 包导入的 Skill")
                
                logger.info(f"从 SKILL.md 解析: name={skill_name}, description={skill_description[:50]}...")
                
                # 检查是否已存在同名 skill
                skill_path = skills_dir / skill_name
                if skill_path.exists():
                    return {
                        "success": False, 
                        "message": f"Skill '{skill_name}' 已存在",
                        "skill_name": skill_name
                    }
                
                # 创建 skill 目录
                skill_path.mkdir(parents=True, exist_ok=True)
                
                # 移动内容到 skill 目录（排除 macOS 资源文件）
                for item in content_dir.iterdir():
                    if item.name.startswith('__MACOSX') or item.name.startswith('._'):
                        continue
                    dest = skill_path / item.name
                    shutil.move(str(item), str(dest))
                
                # 生成 skill 的 yaml 配置文件
                skill_config_path = skill_path / f"{skill_name}.yaml"
                skill_config = {
                    "baseinfo": self._create_baseinfo(
                        name=skill_name,
                        display_name=skill_name,
                        description=skill_description,
                    ),
                    "source": "local_import",
                    "import_file": original_filename or zip_file_path.name,
                }
                self._save_yaml(skill_config_path, skill_config)
                
                # 列出最终目录内容用于调试
                final_contents = list(skill_path.iterdir()) if skill_path.exists() else []
                logger.info(f"Skill 目录内容: {[f.name for f in final_contents]}")
                
                return {
                    "success": True,
                    "skill_name": skill_name,
                    "description": skill_description,
                    "message": f"Skill '{skill_name}' 导入成功",
                    "path": str(skill_path)
                }
            
        except zipfile.BadZipFile:
            return {"success": False, "message": "损坏的 zip 文件"}
        except Exception as e:
            logger.error(f"导入 Skill 失败: {e}", exc_info=True)
            # 清理可能创建的目录
            skill_path = skills_dir / skill_name if 'skill_name' in locals() else None
            if skill_path and skill_path.exists():
                shutil.rmtree(skill_path)
            return {"success": False, "message": f"导入失败: {str(e)}"}
    
    # ==================== Model 操作 ====================
    
    def list_models(self, catalog_id: str, schema_name: str) -> List[Model]:
        """获取 Model 列表"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return []
        
        models = []
        models_dir = schema_path / MODELS_DIR
        
        if not models_dir.exists():
            return models
        
        for item in models_dir.iterdir():
            if item.is_file() and item.suffix == ".yaml" and not item.name.startswith("."):
                model = self._load_model(catalog_id, schema_name, item)
                if model:
                    models.append(model)
        
        return models
    
    def _load_model(self, catalog_id: str, schema_name: str, model_path: Path) -> Optional[Model]:
        """加载 Model"""
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path)
        
        return Model(
            id=f"{catalog_id}_{schema_name}_model_{model_path.stem}",
            name=model_path.stem,
            display_name=baseinfo.get("display_name") or model_path.stem,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            schema_id=f"{catalog_id}_{schema_name}",
            entity_type=EntityType.MODEL,
            path=str(model_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            model_type=config.get("model_type", "endpoint"),
            local_provider=config.get("local_provider"),
            local_source=config.get("local_source"),
            volume_reference=config.get("volume_reference"),
            huggingface_repo=config.get("huggingface_repo"),
            huggingface_filename=config.get("huggingface_filename"),
            endpoint_provider=config.get("endpoint_provider"),
            api_base_url=config.get("api_base_url"),
            api_key=config.get("api_key"),
            model_id=config.get("model_id"),
        )
    
    def get_model(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[Model]:
        """获取 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        model_path = schema_path / MODELS_DIR / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        
        return self._load_model(catalog_id, schema_name, model_path)
    
    def get_model_config_content(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[str]:
        """获取 Model 配置内容"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        model_path = schema_path / MODELS_DIR / f"{model_name}.yaml"
        return self._read_file(model_path)
    
    def create_model(self, catalog_id: str, schema_name: str, model_create: ModelCreate) -> Model:
        """创建 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            raise ValueError(f"Schema '{schema_name}' 不存在")
        
        models_dir = schema_path / MODELS_DIR
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / f"{model_create.name}.yaml"
        if model_path.exists():
            raise ValueError(f"Model '{model_create.name}' 已存在")
        
        baseinfo = self._create_baseinfo(
            model_create.name,
            model_create.display_name,
            model_create.description,
            model_create.tags,
            model_create.owner or "admin",
        )
        
        config = {
            "baseinfo": baseinfo,
            "model_type": model_create.model_type.value if hasattr(model_create.model_type, 'value') else model_create.model_type,
        }
        
        # 本地模型字段
        if model_create.local_provider:
            config["local_provider"] = model_create.local_provider.value if hasattr(model_create.local_provider, 'value') else model_create.local_provider
        if model_create.local_source:
            config["local_source"] = model_create.local_source.value if hasattr(model_create.local_source, 'value') else model_create.local_source
        if model_create.volume_reference:
            config["volume_reference"] = model_create.volume_reference
        if model_create.huggingface_repo:
            config["huggingface_repo"] = model_create.huggingface_repo
        if model_create.huggingface_filename:
            config["huggingface_filename"] = model_create.huggingface_filename
        
        # API 端点字段
        if model_create.endpoint_provider:
            config["endpoint_provider"] = model_create.endpoint_provider.value if hasattr(model_create.endpoint_provider, 'value') else model_create.endpoint_provider
        if model_create.api_base_url:
            config["api_base_url"] = model_create.api_base_url
        if model_create.api_key:
            config["api_key"] = model_create.api_key
        if model_create.model_id:
            config["model_id"] = model_create.model_id
        
        self._save_yaml(model_path, config)
        
        return self._load_model(catalog_id, schema_name, model_path)
    
    def update_model(self, catalog_id: str, schema_name: str, model_name: str, update: ModelUpdate) -> Optional[Model]:
        """更新 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return None
        
        model_path = schema_path / MODELS_DIR / f"{model_name}.yaml"
        if not model_path.exists():
            return None
        
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path)
        
        if update.display_name is not None:
            baseinfo["display_name"] = update.display_name
        if update.description is not None:
            baseinfo["description"] = update.description
        if update.tags is not None:
            baseinfo["tags"] = update.tags
        baseinfo["updated_at"] = self._now_iso()
        config["baseinfo"] = baseinfo
        
        if update.api_key is not None:
            config["api_key"] = update.api_key
        if update.api_base_url is not None:
            config["api_base_url"] = update.api_base_url
        if update.model_id is not None:
            config["model_id"] = update.model_id
        
        self._save_yaml(model_path, config)
        
        return self._load_model(catalog_id, schema_name, model_path)
    
    def delete_model(self, catalog_id: str, schema_name: str, model_name: str) -> bool:
        """删除 Model"""
        schema_path = self._get_schema_path(catalog_id, schema_name)
        if not schema_path:
            return False
        
        model_path = schema_path / MODELS_DIR / f"{model_name}.yaml"
        if not model_path.exists():
            return False
        
        model_path.unlink()
        return True
    
    # ==================== 导航树 ====================
    
    def get_catalog_tree(self) -> List[CatalogTreeNode]:
        """获取 Catalog 导航树"""
        catalogs = self.discover_catalogs()
        tree = []
        
        for catalog in catalogs:
            catalog_node = CatalogTreeNode(
                id=catalog.id,
                name=catalog.name,
                display_name=catalog.display_name or catalog.name,
                node_type="catalog",
                children=[],
                metadata={"description": catalog.description},
            )
            
            # 添加 Agents
            for agent in catalog.agents:
                agent_children = []
                
                if agent.skills:
                    skills_folder = CatalogTreeNode(
                        id=f"{agent.id}_skills",
                        name="skills",
                        display_name="Skills",
                        node_type="folder",
                        children=[
                            CatalogTreeNode(
                                id=f"{agent.id}_skill_{s}",
                                name=s,
                                display_name=s,
                                node_type="skill",
                                metadata={"catalog_id": catalog.id, "agent_name": agent.name},
                            )
                            for s in agent.skills
                        ],
                        metadata={"catalog_id": catalog.id, "agent_name": agent.name},
                    )
                    agent_children.append(skills_folder)
                
                if agent.prompts:
                    prompts_folder = CatalogTreeNode(
                        id=f"{agent.id}_prompts",
                        name="prompts",
                        display_name="Prompts",
                        node_type="folder",
                        children=[
                            CatalogTreeNode(
                                id=f"{agent.id}_prompt_{p}",
                                name=p,
                                display_name=p,
                                node_type="prompt",
                                metadata={"catalog_id": catalog.id, "agent_name": agent.name},
                            )
                            for p in agent.prompts
                        ],
                        metadata={"catalog_id": catalog.id, "agent_name": agent.name},
                    )
                    agent_children.append(prompts_folder)
                
                agent_node = CatalogTreeNode(
                    id=agent.id,
                    name=agent.name,
                    display_name=agent.display_name or agent.name,
                    node_type="agent",
                    children=agent_children,
                    metadata={"description": agent.description, "catalog_id": catalog.id},
                )
                catalog_node.children.append(agent_node)
            
            # 添加 Schemas
            for schema in catalog.schemas:
                assets = self.scan_assets(catalog.id, schema.name)
                models = self.list_models(catalog.id, schema.name)
                
                asset_children = [
                    CatalogTreeNode(
                        id=a.id,
                        name=a.name,
                        display_name=a.display_name or a.name,
                        node_type=a.asset_type.value if hasattr(a.asset_type, 'value') else str(a.asset_type),
                        schema_type=schema.schema_type,
                        metadata={"catalog_id": catalog.id, "schema_name": schema.name, "description": a.description},
                    )
                    for a in assets
                ]
                
                asset_children.extend([
                    CatalogTreeNode(
                        id=m.id,
                        name=m.name,
                        display_name=m.display_name or m.name,
                        node_type="model",
                        metadata={"catalog_id": catalog.id, "schema_name": schema.name, "description": m.description},
                    )
                    for m in models
                ])
                
                schema_node = CatalogTreeNode(
                    id=schema.id,
                    name=schema.name,
                    display_name=schema.display_name or schema.name,
                    node_type="schema",
                    schema_type=schema.schema_type,
                    children=asset_children,
                    metadata={
                        "description": schema.description,
                        "has_connection": schema.connection is not None,
                        "catalog_id": catalog.id,
                    },
                )
                catalog_node.children.append(schema_node)
            
            tree.append(catalog_node)
        
        return tree


# 全局服务实例
catalog_service = CatalogService()
