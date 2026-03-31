"""
BusinessUnit Service - core service managing BusinessUnit and sub-services
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.core.constants import (
    BUSINESS_UNIT_CONFIG_FILE, AGENT_CONFIG_FILE,
    ASSET_BUNDLE_CONFIG_FILE,
    ASSET_FILE_SUFFIX, AGENTS_DIR, ASSET_BUNDLES_DIR,
    TABLES_DIR, VOLUMES_DIR, FUNCTIONS_DIR, NOTES_DIR,
    BUNDLE_ASSET_TYPE_TO_DIR, AGENT_MODELS_DIR, AGENT_MCPS_DIR,
    AGENT_OUTPUT_DIR,
)
from app.models.business_unit import (
    BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate,
    BusinessUnitTreeNode, EntityType,
    AssetBundle, AssetBundleCreate, AssetBundleUpdate,
    ConnectionConfig,
    Asset, AssetCreate, AssetType,
    Agent, AgentCreate, AgentUpdate,
    Model, ModelCreate, ModelUpdate,
    MCP, MCPCreate, MCPUpdate,
    Memory, MemoryCreate, MemoryUpdate,
)
from app.models.metadata import SyncResult
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class BusinessUnitService(BaseService):
    """BusinessUnit service class"""
    
    def __init__(self):
        super().__init__(settings.CATALOGS_DIR)
        # Lazy import to avoid circular dependencies
        self._asset_bundle_service = None
        self._agent_service = None
        logger.debug(f"BusinessUnitService initialized, base_dir={settings.CATALOGS_DIR}")
    
    @property
    def asset_bundle_service(self):
        """AssetBundle service"""
        if self._asset_bundle_service is None:
            from app.services.asset_bundle_service import AssetBundleService
            self._asset_bundle_service = AssetBundleService(self)
        return self._asset_bundle_service
    
    @property
    def agent_service(self):
        if self._agent_service is None:
            from app.services.agent_service import AgentService
            self._agent_service = AgentService(self)
        return self._agent_service
    
    # ==================== Path Methods ====================
    
    def get_business_unit_path(self, business_unit_id: str) -> Path:
        """Get BusinessUnit path"""
        return self.base_dir / business_unit_id
    
    def get_config_path(self, bu_path: Path) -> Path:
        """Get BusinessUnit config file path"""
        return bu_path / BUSINESS_UNIT_CONFIG_FILE
    
    def get_agents_dir(self, bu_path: Path) -> Path:
        """Get Agents directory path"""
        return bu_path / AGENTS_DIR
    
    def get_asset_bundles_dir(self, bu_path: Path) -> Path:
        """Get AssetBundles directory path"""
        return bu_path / ASSET_BUNDLES_DIR
    
    def get_asset_bundle_path(self, business_unit_id: str, bundle_name: str) -> Optional[Path]:
        """Get AssetBundle path"""
        bu_path = self.get_business_unit_path(business_unit_id)
        bundle_path = self.get_asset_bundles_dir(bu_path) / bundle_name
        return bundle_path if bundle_path.exists() else None
    
    # ==================== BusinessUnit CRUD ====================
    
    def discover_business_units(self) -> List[BusinessUnit]:
        """Discover all BusinessUnits"""
        logger.debug(f"Scanning BusinessUnit directory: {self.base_dir}")
        bus = self._scan_subdirs(self.base_dir, self._load_business_unit)
        logger.info(f"Discover {len(bus)}  BusinessUnit(s)")
        return bus
    
    def _load_business_unit(self, bu_path: Path) -> Optional[BusinessUnit]:
        """Load BusinessUnit"""
        logger.debug(f"Loading BusinessUnit: {bu_path.name}")
        config_path = self.get_config_path(bu_path)
        config = self._load_yaml(config_path)
        
        if config is None:
            logger.debug(f"BusinessUnit config not found, creating default config: {bu_path.name}")
            baseinfo = self._create_baseinfo(bu_path.name)
            config = {"baseinfo": baseinfo}
            self._save_yaml(config_path, config)
        
        baseinfo = self._extract_baseinfo(config, bu_path.name)
        
        return BusinessUnit(
            id=bu_path.name,
            name=bu_path.name,
            display_name=baseinfo.get("display_name") or bu_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            entity_type=EntityType.BUSINESS_UNIT,
            path=str(bu_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            asset_bundles=self.asset_bundle_service.scan_asset_bundles(bu_path, bu_path.name),
            agents=self.agent_service.scan_agents(bu_path, bu_path.name),
        )
    
    def get_business_unit(self, business_unit_id: str) -> Optional[BusinessUnit]:
        """Get BusinessUnit"""
        logger.debug(f"Fetching BusinessUnit: {business_unit_id}")
        bu_path = self.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            logger.debug(f"BusinessUnit  does not exist: {business_unit_id}")
            return None
        return self._load_business_unit(bu_path)
    
    def get_business_unit_config_content(self, business_unit_id: str) -> Optional[str]:
        """Get BusinessUnit config raw content"""
        bu_path = self.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            return None
        return self._read_file(self.get_config_path(bu_path))
    
    def create_business_unit(self, data: BusinessUnitCreate) -> BusinessUnit:
        """Create BusinessUnit"""
        logger.info(f"Creating BusinessUnit: {data.name}")
        bu_path = self.get_business_unit_path(data.name)
        if bu_path.exists():
            logger.warning(f"BusinessUnit  already exists: {data.name}")
            raise ValueError(f"BusinessUnit '{data.name}' already exists")
        
        # Create directory structure
        bu_path.mkdir(parents=True, exist_ok=True)
        self.get_agents_dir(bu_path).mkdir(exist_ok=True)
        (bu_path / ASSET_BUNDLES_DIR).mkdir(exist_ok=True)  # Use new directory name
        
        # Create config
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        self._save_yaml(bu_path / BUSINESS_UNIT_CONFIG_FILE, {"baseinfo": baseinfo})
        logger.info(f"BusinessUnit created successfully: {data.name}")
        return self._load_business_unit(bu_path)
    
    def update_business_unit(self, business_unit_id: str, update: BusinessUnitUpdate) -> Optional[BusinessUnit]:
        """Update BusinessUnit"""
        logger.info(f"Updating BusinessUnit: {business_unit_id}")
        bu_path = self.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            logger.warning(f"BusinessUnit  does not exist: {business_unit_id}")
            return None
        
        config_path = self.get_config_path(bu_path)
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, bu_path.name)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        self._save_yaml(config_path, config)
        
        logger.info(f"BusinessUnit updated successfully: {business_unit_id}")
        return self._load_business_unit(bu_path)
    
    def delete_business_unit(self, business_unit_id: str) -> bool:
        """Delete BusinessUnit"""
        logger.info(f"Deleting BusinessUnit: {business_unit_id}")
        result = self._remove_dir(self.get_business_unit_path(business_unit_id))
        if result:
            logger.info(f"BusinessUnit deleted successfully: {business_unit_id}")
        else:
            logger.warning(f"BusinessUnit  does not exist: {business_unit_id}")
        return result
    
    # ==================== AssetBundle Proxy Methods ====================
    
    def get_asset_bundles(self, business_unit_id: str) -> List[AssetBundle]:
        return self.asset_bundle_service.get_asset_bundles(business_unit_id)
    
    def get_asset_bundle_config_content(self, business_unit_id: str, bundle_name: str) -> Optional[str]:
        return self.asset_bundle_service.get_asset_bundle_config_content(business_unit_id, bundle_name)
    
    def create_asset_bundle(self, business_unit_id: str, data: AssetBundleCreate) -> AssetBundle:
        return self.asset_bundle_service.create_asset_bundle(business_unit_id, data)
    
    def update_asset_bundle(self, business_unit_id: str, bundle_name: str, update: AssetBundleUpdate) -> Optional[AssetBundle]:
        return self.asset_bundle_service.update_asset_bundle(business_unit_id, bundle_name, update)
    
    def delete_asset_bundle(self, business_unit_id: str, bundle_name: str) -> bool:
        return self.asset_bundle_service.delete_asset_bundle(business_unit_id, bundle_name)
    
    def sync_asset_bundle_metadata(self, business_unit_id: str, bundle_name: str) -> SyncResult:
        return self.asset_bundle_service.sync_asset_bundle_metadata(business_unit_id, bundle_name)
    
    # ==================== Asset Proxy Methods ====================
    
    def scan_assets(self, business_unit_id: str, bundle_name: str) -> List[Asset]:
        return self.asset_bundle_service.scan_assets(business_unit_id, bundle_name)
    
    def get_asset_config_content(self, business_unit_id: str, bundle_name: str, asset_name: str) -> Optional[str]:
        return self.asset_bundle_service.get_asset_config_content(business_unit_id, bundle_name, asset_name)
    
    def create_asset(self, business_unit_id: str, bundle_name: str, data: AssetCreate) -> Asset:
        return self.asset_bundle_service.create_asset(business_unit_id, bundle_name, data)
    
    def delete_asset(self, business_unit_id: str, bundle_name: str, asset_name: str) -> bool:
        return self.asset_bundle_service.delete_asset(business_unit_id, bundle_name, asset_name)
    
    def preview_table_data(self, business_unit_id: str, bundle_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        return self.asset_bundle_service.preview_table_data(business_unit_id, bundle_name, table_name, limit, offset)
    
    # ==================== Agent Proxy Methods ====================
    
    def list_agents(self, business_unit_id: str) -> List[Agent]:
        return self.agent_service.list_agents(business_unit_id)
    
    def get_agent(self, business_unit_id: str, agent_name: str) -> Optional[Agent]:
        return self.agent_service.get_agent(business_unit_id, agent_name)
    
    def get_agent_config_content(self, business_unit_id: str, agent_name: str) -> Optional[str]:
        return self.agent_service.get_agent_config_content(business_unit_id, agent_name)
    
    def create_agent(self, business_unit_id: str, data: AgentCreate) -> Agent:
        return self.agent_service.create_agent(business_unit_id, data)
    
    def update_agent(self, business_unit_id: str, agent_name: str, update: AgentUpdate) -> Optional[Agent]:
        return self.agent_service.update_agent(business_unit_id, agent_name, update)
    
    def delete_agent(self, business_unit_id: str, agent_name: str) -> bool:
        return self.agent_service.delete_agent(business_unit_id, agent_name)
    
    # ==================== Model Proxy Methods ====================
    
    def list_models(self, business_unit_id: str, agent_name: str) -> List[Model]:
        return self.agent_service.list_models(business_unit_id, agent_name)
    
    def get_model(self, business_unit_id: str, agent_name: str, model_name: str) -> Optional[Model]:
        return self.agent_service.get_model(business_unit_id, agent_name, model_name)
    
    def get_model_config_content(self, business_unit_id: str, agent_name: str, model_name: str) -> Optional[str]:
        return self.agent_service.get_model_config_content(business_unit_id, agent_name, model_name)
    
    def create_model(self, business_unit_id: str, agent_name: str, data: ModelCreate) -> Model:
        return self.agent_service.create_model(business_unit_id, agent_name, data)
    
    def update_model(self, business_unit_id: str, agent_name: str, model_name: str, update: ModelUpdate) -> Optional[Model]:
        return self.agent_service.update_model(business_unit_id, agent_name, model_name, update)
    
    def delete_model(self, business_unit_id: str, agent_name: str, model_name: str) -> bool:
        return self.agent_service.delete_model(business_unit_id, agent_name, model_name)
    
    def enable_model(self, business_unit_id: str, agent_name: str, model_name: str) -> bool:
        """Enable specified Model"""
        return self.agent_service.enable_model(business_unit_id, agent_name, model_name)
    
    # ==================== MCP Proxy Methods ====================
    
    def list_mcps(self, business_unit_id: str, agent_name: str) -> List[MCP]:
        return self.agent_service.list_mcps(business_unit_id, agent_name)
    
    def get_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str) -> Optional[MCP]:
        return self.agent_service.get_mcp(business_unit_id, agent_name, mcp_name)
    
    def create_mcp(self, business_unit_id: str, agent_name: str, data: MCPCreate) -> MCP:
        return self.agent_service.create_mcp(business_unit_id, agent_name, data)
    
    def update_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str, update: MCPUpdate) -> Optional[MCP]:
        return self.agent_service.update_mcp(business_unit_id, agent_name, mcp_name, update)
    
    def delete_mcp(self, business_unit_id: str, agent_name: str, mcp_name: str) -> bool:
        return self.agent_service.delete_mcp(business_unit_id, agent_name, mcp_name)
    
    # ==================== Memory Proxy Methods ====================
    
    def list_agent_memories(self, business_unit_id: str, agent_name: str) -> Optional[List[Memory]]:
        return self.agent_service.list_memories(business_unit_id, agent_name)
    
    def get_agent_memory_detail(self, business_unit_id: str, agent_name: str, memory_name: str) -> Optional[Memory]:
        return self.agent_service.get_memory(business_unit_id, agent_name, memory_name)
    
    def create_agent_memory(self, business_unit_id: str, agent_name: str, data: MemoryCreate) -> bool:
        return self.agent_service.create_memory(business_unit_id, agent_name, data)
    
    def update_agent_memory(self, business_unit_id: str, agent_name: str, memory_name: str, update: MemoryUpdate) -> bool:
        return self.agent_service.update_memory(business_unit_id, agent_name, memory_name, update)
    
    def delete_agent_memory(self, business_unit_id: str, agent_name: str, memory_name: str) -> bool:
        return self.agent_service.delete_memory(business_unit_id, agent_name, memory_name)
    
    def toggle_memory_enabled(self, business_unit_id: str, agent_name: str, memory_name: str, enabled: bool) -> bool:
        return self.agent_service.toggle_memory_enabled(business_unit_id, agent_name, memory_name, enabled)
    
    # ==================== Skill Proxy Methods ====================
    
    def get_agent_skill(self, business_unit_id: str, agent_name: str, skill_name: str) -> Optional[Dict[str, Any]]:
        return self.agent_service.get_skill(business_unit_id, agent_name, skill_name)
    
    def delete_agent_skill(self, business_unit_id: str, agent_name: str, skill_name: str) -> bool:
        return self.agent_service.delete_skill(business_unit_id, agent_name, skill_name)
    
    def toggle_skill_enabled(self, business_unit_id: str, agent_name: str, skill_name: str, enabled: bool) -> bool:
        return self.agent_service.toggle_skill_enabled(business_unit_id, agent_name, skill_name, enabled)
    
    def import_skill_from_zip(self, business_unit_id: str, agent_name: str, zip_file_path: Path, original_filename: str = None) -> Dict[str, Any]:
        return self.agent_service.import_skill_from_zip(business_unit_id, agent_name, zip_file_path, original_filename)
    
    # ==================== Navigation Tree ====================
    
    def get_business_unit_tree(self) -> List[BusinessUnitTreeNode]:
        """Get navigation tree"""
        return [self._build_bu_node(bu) for bu in self.discover_business_units()]
    
    def _build_bu_node(self, bu: BusinessUnit) -> BusinessUnitTreeNode:
        """Build BusinessUnit tree node"""
        children = []
        
        # Agent nodes
        for agent in bu.agents:
            agent_children = []
            
            # Skills folder
            if agent.skills:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_skills", "skills", "Skills", "skill",
                    agent.skills, {"business_unit_id": bu.id, "agent_name": agent.name}
                ))
            
            # Memories folder
            if agent.memories:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_memories", "memories", "Memories", "prompt",
                    agent.memories, {"business_unit_id": bu.id, "agent_name": agent.name}
                ))
            
            # Models folder
            if agent.models:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_models", "models", "Models", "model",
                    agent.models, {"business_unit_id": bu.id, "agent_name": agent.name, "active_model": agent.active_model}
                ))
            
            # MCPs folder
            if agent.mcps:
                agent_children.append(self._build_folder_node(
                    f"{agent.id}_mcps", "mcps", "MCPs", "mcp",
                    agent.mcps, {"business_unit_id": bu.id, "agent_name": agent.name}
                ))

            # Output folder
            output_node = self._build_output_node(bu.id, agent.name, agent.id)
            if output_node:
                agent_children.append(output_node)
            
            children.append(BusinessUnitTreeNode(
                id=agent.id, name=agent.name, display_name=agent.display_name or agent.name,
                node_type="agent", children=agent_children,
                metadata={"description": agent.description, "business_unit_id": bu.id, "active_model": agent.active_model}
            ))
        
        # AssetBundle 节点
        for bundle in bu.asset_bundles:
            assets = self.scan_assets(bu.id, bundle.name)
            
            asset_children = [
                BusinessUnitTreeNode(
                    id=a.id, name=a.name, display_name=a.display_name or a.name,
                    node_type=a.asset_type.value if hasattr(a.asset_type, 'value') else str(a.asset_type),
                    bundle_type=bundle.bundle_type,
                    metadata={"business_unit_id": bu.id, "bundle_name": bundle.name, "description": a.description}
                ) for a in assets
            ]
            
            children.append(BusinessUnitTreeNode(
                id=bundle.id, name=bundle.name, display_name=bundle.display_name or bundle.name,
                node_type="asset_bundle", bundle_type=bundle.bundle_type, children=asset_children,
                metadata={"description": bundle.description, "has_connection": bundle.connection is not None, "business_unit_id": bu.id}
            ))
        
        return BusinessUnitTreeNode(
            id=bu.id, name=bu.name, display_name=bu.display_name or bu.name,
            node_type="business_unit", children=children, metadata={"description": bu.description}
        )
    
    def _build_folder_node(self, id: str, name: str, display_name: str, child_type: str, items: List[str], metadata: Dict) -> BusinessUnitTreeNode:
        """Build folder node"""
        return BusinessUnitTreeNode(
            id=id, name=name, display_name=display_name, node_type="folder",
            children=[
                BusinessUnitTreeNode(id=f"{id}_{item}", name=item, display_name=item, node_type=child_type, metadata=metadata)
                for item in items
            ],
            metadata=metadata
        )

    def _build_output_node(self, business_unit_id: str, agent_name: str, agent_id: str) -> Optional[BusinessUnitTreeNode]:
        """Build Agent output tree node"""
        agent_path = self.agent_service._get_agent_path(business_unit_id, agent_name)
        output_path = agent_path / AGENT_OUTPUT_DIR
        if not output_path.exists() or not output_path.is_dir():
            return None

        metadata = {
            "business_unit_id": business_unit_id,
            "agent_name": agent_name,
            "relative_path": "",
            "is_dir": True,
            "absolute_path": str(output_path),
        }
        return BusinessUnitTreeNode(
            id=f"{agent_id}_output",
            name="output",
            display_name="output",
            node_type="output",
            children=self._build_output_tree(output_path, business_unit_id, agent_name, f"{agent_id}_output", ""),
            metadata=metadata,
        )

    def _build_output_tree(
        self,
        root_path: Path,
        business_unit_id: str,
        agent_name: str,
        parent_id: str,
        relative_path: str,
    ) -> List[BusinessUnitTreeNode]:
        """Recursively build directory tree under output"""
        current_path = root_path / relative_path if relative_path else root_path
        if not current_path.exists() or not current_path.is_dir():
            return []

        nodes: List[BusinessUnitTreeNode] = []
        for item in sorted(current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.name.startswith('.'):
                continue

            item_relative = f"{relative_path}/{item.name}" if relative_path else item.name
            node_id = f"{parent_id}/{item.name}"
            if item.is_dir():
                nodes.append(BusinessUnitTreeNode(
                    id=node_id,
                    name=item.name,
                    display_name=item.name,
                    node_type="folder",
                    children=self._build_output_tree(root_path, business_unit_id, agent_name, node_id, item_relative),
                    metadata={
                        "business_unit_id": business_unit_id,
                        "agent_name": agent_name,
                        "relative_path": item_relative,
                        "is_dir": True,
                    },
                ))
            else:
                nodes.append(BusinessUnitTreeNode(
                    id=node_id,
                    name=item.name,
                    display_name=item.name,
                    node_type="output_file",
                    metadata={
                        "business_unit_id": business_unit_id,
                        "agent_name": agent_name,
                        "relative_path": item_relative,
                        "is_dir": False,
                        "size": item.stat().st_size,
                    },
                ))
        return nodes

    def _resolve_output_path(self, business_unit_id: str, agent_name: str, relative_path: str) -> Path:
        """Parse and validate output relative path to prevent directory traversal"""
        agent_path = self.agent_service._get_agent_path(business_unit_id, agent_name)
        output_path = (agent_path / AGENT_OUTPUT_DIR).resolve()
        if not output_path.exists() or not output_path.is_dir():
            raise FileNotFoundError("output not found")

        if relative_path is None:
            raise ValueError("relative path is required")

        normalized = relative_path.strip().replace('\\', '/')
        if normalized.startswith('/'):
            raise ValueError("absolute path is not allowed")

        target_path = (output_path / normalized).resolve()
        try:
            target_path.relative_to(output_path)
        except ValueError as exc:
            raise ValueError("invalid relative path") from exc

        return target_path

    def get_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str) -> Dict[str, Any]:
        """Read file content under output"""
        target_path = self._resolve_output_path(business_unit_id, agent_name, relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("output file not found")

        content = self._read_file(target_path)
        if content is None:
            raise ValueError("file content is not readable as utf-8 text")

        return {
            "path": str(target_path),
            "relative_path": relative_path.replace('\\', '/'),
            "content": content,
        }

    def save_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str, content: str) -> Dict[str, Any]:
        """Save edited content to an output file"""
        target_path = self._resolve_output_path(business_unit_id, agent_name, relative_path)

        # Allow saving to existing files only (prevent creating arbitrary files)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("output file not found")

        self._write_file(target_path, content)

        return {
            "path": str(target_path),
            "relative_path": relative_path.replace('\\', '/'),
            "content": content,
        }


# Global service instance
business_unit_service = BusinessUnitService()
