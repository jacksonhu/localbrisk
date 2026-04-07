"""BusinessUnit aggregate service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.constants import AGENTS_DIR, ASSET_BUNDLES_DIR, BUSINESS_UNIT_CONFIG_FILE
from app.models.business_unit import (
    Agent,
    AgentCreate,
    AssetBundleCreate,
    AssetCreate,
    AssetType,
    BusinessUnit,
    BusinessUnitCreate,
    BusinessUnitTreeNode,
    BusinessUnitUpdate,
    EntityType,
)
from app.services.base_service import BaseService
from app.services.business_unit_navigation import BusinessUnitTreeBuilder
from app.services.business_unit_output import BusinessUnitOutputService

logger = logging.getLogger(__name__)
DEFAULT_OUTPUT_BUNDLE_NAME = "output"


class BusinessUnitService(BaseService):
    """Manage business units and coordinate nested resource services."""

    def __init__(self):
        super().__init__(settings.CATALOGS_DIR)
        self._asset_bundle_service = None
        self._agent_service = None
        self._tree_builder = BusinessUnitTreeBuilder(self)
        self._output_service = BusinessUnitOutputService(self)
        logger.debug("BusinessUnitService initialized with base_dir=%s", settings.CATALOGS_DIR)

    @property
    def asset_bundle_service(self):
        """Return the lazily created asset bundle service."""
        if self._asset_bundle_service is None:
            from app.services.asset_bundle_service import AssetBundleService

            self._asset_bundle_service = AssetBundleService(self)
        return self._asset_bundle_service

    @property
    def agent_service(self):
        """Return the lazily created agent service."""
        if self._agent_service is None:
            from app.services.agent_service import AgentService

            self._agent_service = AgentService(self)
        return self._agent_service

    def get_business_unit_path(self, business_unit_id: str) -> Path:
        """Return the root path of a business unit."""
        return self.base_dir / business_unit_id

    def get_config_path(self, business_unit_path: Path) -> Path:
        """Return the business unit config file path."""
        return business_unit_path / BUSINESS_UNIT_CONFIG_FILE

    def get_agents_dir(self, business_unit_path: Path) -> Path:
        """Return the agents directory under a business unit."""
        return business_unit_path / AGENTS_DIR

    def get_asset_bundles_dir(self, business_unit_path: Path) -> Path:
        """Return the asset bundles directory under a business unit."""
        return business_unit_path / ASSET_BUNDLES_DIR

    def get_asset_bundle_path(self, business_unit_id: str, bundle_name: str) -> Optional[Path]:
        """Return the asset bundle path if it exists."""
        business_unit_path = self.get_business_unit_path(business_unit_id)
        bundle_path = self.get_asset_bundles_dir(business_unit_path) / bundle_name
        return bundle_path if bundle_path.exists() else None

    def discover_business_units(self) -> list[BusinessUnit]:
        """Scan and return all business units."""
        business_units = self._scan_subdirs(self.base_dir, self._load_business_unit)
        logger.info("Discovered %s business unit(s)", len(business_units))
        return business_units

    def _load_business_unit(self, business_unit_path: Path) -> Optional[BusinessUnit]:
        """Load a business unit from disk."""
        config_path = self.get_config_path(business_unit_path)
        config = self._load_yaml(config_path)
        if config is None:
            baseinfo = self._create_baseinfo(business_unit_path.name)
            config = {"baseinfo": baseinfo}
            self._save_yaml(config_path, config)

        baseinfo = self._extract_baseinfo(config, business_unit_path.name)
        return BusinessUnit(
            id=business_unit_path.name,
            name=business_unit_path.name,
            display_name=baseinfo.get("display_name") or business_unit_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            entity_type=EntityType.BUSINESS_UNIT,
            path=str(business_unit_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            asset_bundles=self.asset_bundle_service.scan_asset_bundles(business_unit_path, business_unit_path.name),
            agents=self.agent_service.scan_agents(business_unit_path, business_unit_path.name),
        )

    def get_business_unit(self, business_unit_id: str) -> Optional[BusinessUnit]:
        """Return a business unit by id."""
        business_unit_path = self.get_business_unit_path(business_unit_id)
        if not business_unit_path.exists():
            return None
        return self._load_business_unit(business_unit_path)

    def get_business_unit_config_content(self, business_unit_id: str) -> Optional[str]:
        """Return raw business unit config content."""
        business_unit_path = self.get_business_unit_path(business_unit_id)
        if not business_unit_path.exists():
            return None
        return self._read_file(self.get_config_path(business_unit_path))

    def create_business_unit(self, data: BusinessUnitCreate) -> BusinessUnit:
        """Create a business unit and initialize default folders."""
        business_unit_path = self.get_business_unit_path(data.name)
        if business_unit_path.exists():
            raise ValueError(f"BusinessUnit '{data.name}' already exists")

        business_unit_path.mkdir(parents=True, exist_ok=True)
        self.get_agents_dir(business_unit_path).mkdir(exist_ok=True)
        self.get_asset_bundles_dir(business_unit_path).mkdir(exist_ok=True)

        baseinfo = self._create_baseinfo(
            data.name,
            data.display_name,
            data.description,
            data.tags,
            data.owner or "admin",
        )
        self._save_yaml(self.get_config_path(business_unit_path), {"baseinfo": baseinfo})
        self._ensure_default_output_bundle(data.name)
        logger.info("Created business unit: %s", data.name)
        return self._load_business_unit(business_unit_path)

    def update_business_unit(self, business_unit_id: str, update: BusinessUnitUpdate) -> Optional[BusinessUnit]:
        """Update a business unit."""
        business_unit_path = self.get_business_unit_path(business_unit_id)
        if not business_unit_path.exists():
            return None

        config_path = self.get_config_path(business_unit_path)
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, business_unit_path.name)
        config["baseinfo"] = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        self._save_yaml(config_path, config)
        logger.info("Updated business unit: %s", business_unit_id)
        return self._load_business_unit(business_unit_path)

    def delete_business_unit(self, business_unit_id: str) -> bool:
        """Delete a business unit."""
        deleted = self._remove_dir(self.get_business_unit_path(business_unit_id))
        if deleted:
            logger.info("Deleted business unit: %s", business_unit_id)
        else:
            logger.warning("Business unit not found for delete: %s", business_unit_id)
        return deleted

    def create_agent(self, business_unit_id: str, data: AgentCreate) -> Agent:
        """Create an agent and register its output directory as a local volume."""
        agent = self.agent_service.create_agent(business_unit_id, data)
        self._ensure_agent_output_volume(business_unit_id, agent)
        logger.info("Created agent under business unit %s: %s", business_unit_id, agent.name)
        return agent

    def get_business_unit_tree(self) -> list[BusinessUnitTreeNode]:
        """Return the business unit navigation tree."""
        return self._tree_builder.build_tree()

    def get_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str):
        """Return agent output file content."""
        return self._output_service.get_output_file_content(business_unit_id, agent_name, relative_path)

    def save_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str, content: str):
        """Persist updated content to an existing agent output file."""
        return self._output_service.save_output_file_content(business_unit_id, agent_name, relative_path, content)

    def _ensure_default_output_bundle(self, business_unit_id: str) -> None:
        """Create the default local output bundle if it is missing."""
        if self.get_asset_bundle_path(business_unit_id, DEFAULT_OUTPUT_BUNDLE_NAME):
            return

        self.asset_bundle_service.create_asset_bundle(
            business_unit_id,
            AssetBundleCreate(
                name=DEFAULT_OUTPUT_BUNDLE_NAME,
                display_name="output",
                description="Default output bundle for agent generated files",
                bundle_type="local",
            ),
        )

    def _ensure_agent_output_volume(self, business_unit_id: str, agent: Agent) -> None:
        """Register the agent output directory in the default output bundle."""
        self._ensure_default_output_bundle(business_unit_id)
        output_bundle_path = self.get_asset_bundle_path(business_unit_id, DEFAULT_OUTPUT_BUNDLE_NAME)
        if output_bundle_path is None:
            return

        volume_file = output_bundle_path / "volumes" / f"{agent.name}.yaml"
        if volume_file.exists():
            return

        agent_output_path = Path(agent.path or self.agent_service._get_agent_path(business_unit_id, agent.name)) / "output"
        self.asset_bundle_service.create_asset(
            business_unit_id,
            DEFAULT_OUTPUT_BUNDLE_NAME,
            AssetCreate(
                name=agent.name,
                display_name=agent.display_name or agent.name,
                description=f"Output volume for agent {agent.name}",
                asset_type=AssetType.VOLUME,
                volume_type="local",
                storage_location=str(agent_output_path),
            ),
        )


business_unit_service = BusinessUnitService()
