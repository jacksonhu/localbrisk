"""
Catalog 服务 - 核心服务，管理 Catalog 及其子服务
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.core.constants import (
    CATALOG_CONFIG_FILE, AGENT_CONFIG_FILE, SCHEMA_CONFIG_FILE,
    ASSET_FILE_SUFFIX, AGENTS_DIR, SCHEMAS_DIR, TABLES_DIR,
    VOLUMES_DIR, FUNCTIONS_DIR, MODELS_DIR, NOTES_DIR, ASSET_TYPE_TO_DIR,
)
from app.models.catalog import (
    Catalog, CatalogCreate, CatalogUpdate, CatalogTreeNode, EntityType,
    Schema, SchemaCreate, SchemaUpdate, ConnectionConfig,
    Asset, AssetCreate, AssetType,
    Agent, AgentCreate, AgentUpdate,
    Model, ModelCreate, ModelUpdate,
    Prompt, PromptCreate, PromptUpdate,
)
from app.models.metadata import SyncResult
from app.services.base_service import BaseService


class CatalogService(BaseService):
    """Catalog 服务类"""
    
    def __init__(self):
        super().__init__(settings.CATALOGS_DIR)
        # 延迟导入子服务，避免循环依赖
        self._schema_service = None
        self._agent_service = None
        self._model_service = None
    
    @property
    def schema_service(self):
        if self._schema_service is None:
            from app.services.schema_service import SchemaService
            self._schema_service = SchemaService(self)
        return self._schema_service
    
    @property
    def agent_service(self):
        if self._agent_service is None:
            from app.services.agent_service import AgentService
            self._agent_service = AgentService(self)
        return self._agent_service
    
    @property
    def model_service(self):
        if self._model_service is None:
            from app.services.model_service import ModelService
            self._model_service = ModelService(self)
        return self._model_service
    
    # ==================== 路径方法 ====================
    
    def get_catalog_path(self, catalog_id: str) -> Path:
        """获取 Catalog 路径"""
        return self.base_dir / catalog_id
    
    def get_config_path(self, catalog_path: Path) -> Path:
        """获取 Catalog 配置文件路径"""
        return catalog_path / CATALOG_CONFIG_FILE
    
    def get_agents_dir(self, catalog_path: Path) -> Path:
        """获取 Agents 目录路径"""
        return catalog_path / AGENTS_DIR
    
    def get_schemas_dir(self, catalog_path: Path) -> Path:
        """获取 Schemas 目录路径"""
        return catalog_path / SCHEMAS_DIR
    
    def get_schema_path(self, catalog_id: str, schema_name: str) -> Optional[Path]:
        """获取 Schema 路径"""
        catalog_path = self.get_catalog_path(catalog_id)
        schema_path = self.get_schemas_dir(catalog_path) / schema_name
        return schema_path if schema_path.exists() else None
    
    # ==================== Catalog CRUD ====================
    
    def discover_catalogs(self) -> List[Catalog]:
        """发现所有 Catalog"""
        return self._scan_subdirs(self.base_dir, self._load_catalog)
    
    def _load_catalog(self, catalog_path: Path) -> Optional[Catalog]:
        """加载 Catalog"""
        config_path = self.get_config_path(catalog_path)
        config = self._load_yaml(config_path)
        
        if config is None:
            baseinfo = self._create_baseinfo(catalog_path.name)
            config = {"baseinfo": baseinfo}
            self._save_yaml(config_path, config)
        
        baseinfo = self._extract_baseinfo(config, catalog_path.name)
        
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
            schemas=self.schema_service.scan_schemas(catalog_path, catalog_path.name),
            agents=self.agent_service.scan_agents(catalog_path, catalog_path.name),
        )
    
    def get_catalog(self, catalog_id: str) -> Optional[Catalog]:
        """获取 Catalog"""
        catalog_path = self.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        return self._load_catalog(catalog_path)
    
    def get_catalog_config_content(self, catalog_id: str) -> Optional[str]:
        """获取 Catalog 配置文件原始内容"""
        catalog_path = self.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        return self._read_file(self.get_config_path(catalog_path))
    
    def create_catalog(self, data: CatalogCreate) -> Catalog:
        """创建 Catalog"""
        catalog_path = self.get_catalog_path(data.name)
        if catalog_path.exists():
            raise ValueError(f"Catalog '{data.name}' 已存在")
        
        # 创建目录结构
        catalog_path.mkdir(parents=True, exist_ok=True)
        self.get_agents_dir(catalog_path).mkdir(exist_ok=True)
        self.get_schemas_dir(catalog_path).mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        self._save_yaml(self.get_config_path(catalog_path), {"baseinfo": baseinfo})
        
        return self._load_catalog(catalog_path)
    
    def update_catalog(self, catalog_id: str, update: CatalogUpdate) -> Optional[Catalog]:
        """更新 Catalog"""
        catalog_path = self.get_catalog_path(catalog_id)
        if not catalog_path.exists():
            return None
        
        config_path = self.get_config_path(catalog_path)
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, catalog_path.name)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        self._save_yaml(config_path, config)
        
        return self._load_catalog(catalog_path)
    
    def delete_catalog(self, catalog_id: str) -> bool:
        """删除 Catalog"""
        return self._remove_dir(self.get_catalog_path(catalog_id))
    
    # ==================== Schema 代理方法 ====================
    
    def get_schemas(self, catalog_id: str) -> List[Schema]:
        return self.schema_service.get_schemas(catalog_id)
    
    def get_schema_config_content(self, catalog_id: str, schema_name: str) -> Optional[str]:
        return self.schema_service.get_schema_config_content(catalog_id, schema_name)
    
    def create_schema(self, catalog_id: str, data: SchemaCreate) -> Schema:
        return self.schema_service.create_schema(catalog_id, data)
    
    def update_schema(self, catalog_id: str, schema_name: str, update: SchemaUpdate) -> Optional[Schema]:
        return self.schema_service.update_schema(catalog_id, schema_name, update)
    
    def delete_schema(self, catalog_id: str, schema_name: str) -> bool:
        return self.schema_service.delete_schema(catalog_id, schema_name)
    
    def sync_schema_metadata(self, catalog_id: str, schema_name: str) -> SyncResult:
        return self.schema_service.sync_schema_metadata(catalog_id, schema_name)
    
    # ==================== Asset 代理方法 ====================
    
    def scan_assets(self, catalog_id: str, schema_name: str) -> List[Asset]:
        return self.schema_service.scan_assets(catalog_id, schema_name)
    
    def get_asset_config_content(self, catalog_id: str, schema_name: str, asset_name: str) -> Optional[str]:
        return self.schema_service.get_asset_config_content(catalog_id, schema_name, asset_name)
    
    def create_asset(self, catalog_id: str, schema_name: str, data: AssetCreate) -> Asset:
        return self.schema_service.create_asset(catalog_id, schema_name, data)
    
    def delete_asset(self, catalog_id: str, schema_name: str, asset_name: str) -> bool:
        return self.schema_service.delete_asset(catalog_id, schema_name, asset_name)
    
    def preview_table_data(self, catalog_id: str, schema_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        return self.schema_service.preview_table_data(catalog_id, schema_name, table_name, limit, offset)
    
    # ==================== Agent 代理方法 ====================
    
    def list_agents(self, catalog_id: str) -> List[Agent]:
        return self.agent_service.list_agents(catalog_id)
    
    def get_agent(self, catalog_id: str, agent_name: str) -> Optional[Agent]:
        return self.agent_service.get_agent(catalog_id, agent_name)
    
    def get_agent_config_content(self, catalog_id: str, agent_name: str) -> Optional[str]:
        return self.agent_service.get_agent_config_content(catalog_id, agent_name)
    
    def create_agent(self, catalog_id: str, data: AgentCreate) -> Agent:
        return self.agent_service.create_agent(catalog_id, data)
    
    def update_agent(self, catalog_id: str, agent_name: str, update: AgentUpdate) -> Optional[Agent]:
        return self.agent_service.update_agent(catalog_id, agent_name, update)
    
    def delete_agent(self, catalog_id: str, agent_name: str) -> bool:
        return self.agent_service.delete_agent(catalog_id, agent_name)
    
    # ==================== Prompt 代理方法 ====================
    
    def list_agent_prompts(self, catalog_id: str, agent_name: str) -> Optional[List[Prompt]]:
        return self.agent_service.list_prompts(catalog_id, agent_name)
    
    def get_agent_prompt_detail(self, catalog_id: str, agent_name: str, prompt_name: str) -> Optional[Prompt]:
        return self.agent_service.get_prompt(catalog_id, agent_name, prompt_name)
    
    def create_agent_prompt(self, catalog_id: str, agent_name: str, data: PromptCreate) -> bool:
        return self.agent_service.create_prompt(catalog_id, agent_name, data)
    
    def update_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str, update: PromptUpdate) -> bool:
        return self.agent_service.update_prompt(catalog_id, agent_name, prompt_name, update)
    
    def delete_agent_prompt(self, catalog_id: str, agent_name: str, prompt_name: str) -> bool:
        return self.agent_service.delete_prompt(catalog_id, agent_name, prompt_name)
    
    def toggle_prompt_enabled(self, catalog_id: str, agent_name: str, prompt_name: str, enabled: bool) -> bool:
        return self.agent_service.toggle_prompt_enabled(catalog_id, agent_name, prompt_name, enabled)
    
    # ==================== Skill 代理方法 ====================
    
    def get_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> Optional[Dict[str, Any]]:
        return self.agent_service.get_skill(catalog_id, agent_name, skill_name)
    
    def delete_agent_skill(self, catalog_id: str, agent_name: str, skill_name: str) -> bool:
        return self.agent_service.delete_skill(catalog_id, agent_name, skill_name)
    
    def toggle_skill_enabled(self, catalog_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        return self.agent_service.toggle_skill_enabled(catalog_id, agent_name, skill_name, enabled)
    
    def import_skill_from_zip(self, catalog_id: str, agent_name: str, zip_file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        return self.agent_service.import_skill_from_zip(catalog_id, agent_name, zip_file_path, original_filename)
    
    # ==================== Model 代理方法 ====================
    
    def list_models(self, catalog_id: str, schema_name: str) -> List[Model]:
        return self.model_service.list_models(catalog_id, schema_name)
    
    def get_model(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[Model]:
        return self.model_service.get_model(catalog_id, schema_name, model_name)
    
    def get_model_config_content(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[str]:
        return self.model_service.get_model_config_content(catalog_id, schema_name, model_name)
    
    def create_model(self, catalog_id: str, schema_name: str, data: ModelCreate) -> Model:
        return self.model_service.create_model(catalog_id, schema_name, data)
    
    def update_model(self, catalog_id: str, schema_name: str, model_name: str, update: ModelUpdate) -> Optional[Model]:
        return self.model_service.update_model(catalog_id, schema_name, model_name, update)
    
    def delete_model(self, catalog_id: str, schema_name: str, model_name: str) -> bool:
        return self.model_service.delete_model(catalog_id, schema_name, model_name)
    
    # ==================== 导航树 ====================
    
    def get_catalog_tree(self) -> List[CatalogTreeNode]:
        """获取 Catalog 导航树"""
        return [self._build_catalog_node(c) for c in self.discover_catalogs()]
    
    def _build_catalog_node(self, catalog: Catalog) -> CatalogTreeNode:
        """构建 Catalog 树节点"""
        children = []
        
        # Agent 节点
        for agent in catalog.agents:
            agent_children = []
            if agent.skills:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_skills", "skills", "Skills", "skill",
                    agent.skills, {"catalog_id": catalog.id, "agent_name": agent.name}
                ))
            if agent.prompts:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_prompts", "prompts", "Prompts", "prompt",
                    agent.prompts, {"catalog_id": catalog.id, "agent_name": agent.name}
                ))
            children.append(CatalogTreeNode(
                id=agent.id, name=agent.name, display_name=agent.display_name or agent.name,
                node_type="agent", children=agent_children,
                metadata={"description": agent.description, "catalog_id": catalog.id}
            ))
        
        # Schema 节点
        for schema in catalog.schemas:
            assets = self.scan_assets(catalog.id, schema.name)
            models = self.list_models(catalog.id, schema.name)
            
            asset_children = [
                CatalogTreeNode(
                    id=a.id, name=a.name, display_name=a.display_name or a.name,
                    node_type=a.asset_type.value if hasattr(a.asset_type, 'value') else str(a.asset_type),
                    schema_type=schema.schema_type,
                    metadata={"catalog_id": catalog.id, "schema_name": schema.name, "description": a.description}
                ) for a in assets
            ]
            asset_children.extend([
                CatalogTreeNode(
                    id=m.id, name=m.name, display_name=m.display_name or m.name,
                    node_type="model",
                    metadata={"catalog_id": catalog.id, "schema_name": schema.name, "description": m.description}
                ) for m in models
            ])
            
            children.append(CatalogTreeNode(
                id=schema.id, name=schema.name, display_name=schema.display_name or schema.name,
                node_type="schema", schema_type=schema.schema_type, children=asset_children,
                metadata={"description": schema.description, "has_connection": schema.connection is not None, "catalog_id": catalog.id}
            ))
        
        return CatalogTreeNode(
            id=catalog.id, name=catalog.name, display_name=catalog.display_name or catalog.name,
            node_type="catalog", children=children, metadata={"description": catalog.description}
        )
    
    def _build_folder_node(self, id: str, name: str, display_name: str, child_type: str, items: List[str], metadata: Dict) -> CatalogTreeNode:
        """构建文件夹节点"""
        return CatalogTreeNode(
            id=id, name=name, display_name=display_name, node_type="folder",
            children=[
                CatalogTreeNode(id=f"{id}_{item}", name=item, display_name=item, node_type=child_type, metadata=metadata)
                for item in items
            ],
            metadata=metadata
        )


# 全局服务实例
catalog_service = CatalogService()
