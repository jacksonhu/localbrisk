"""BusinessUnit navigation tree builder."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from app.core.constants import AGENT_OUTPUT_DIR
from app.models.business_unit import BusinessUnit, BusinessUnitTreeNode

if TYPE_CHECKING:
    from app.services.business_unit_service import BusinessUnitService


class BusinessUnitTreeBuilder:
    """Build navigation tree nodes for business units and nested resources."""

    def __init__(self, business_unit_service: "BusinessUnitService"):
        self._business_unit_service = business_unit_service

    def build_tree(self) -> List[BusinessUnitTreeNode]:
        """Build the full navigation tree for all business units."""
        return [self._build_business_unit_node(business_unit) for business_unit in self._business_unit_service.discover_business_units()]

    def _build_business_unit_node(self, business_unit: BusinessUnit) -> BusinessUnitTreeNode:
        children: List[BusinessUnitTreeNode] = []

        for agent in business_unit.agents:
            agent_children: List[BusinessUnitTreeNode] = []
            if agent.skills:
                agent_children.append(
                    self._build_folder_node(
                        f"{agent.id}_skills",
                        "skills",
                        "Skills",
                        "skill",
                        agent.skills,
                        {"business_unit_id": business_unit.id, "agent_name": agent.name},
                    )
                )
            if agent.memories:
                agent_children.append(
                    self._build_folder_node(
                        f"{agent.id}_memories",
                        "memories",
                        "Memories",
                        "prompt",
                        agent.memories,
                        {"business_unit_id": business_unit.id, "agent_name": agent.name},
                    )
                )
            if agent.models:
                agent_children.append(
                    self._build_folder_node(
                        f"{agent.id}_models",
                        "models",
                        "Models",
                        "model",
                        agent.models,
                        {
                            "business_unit_id": business_unit.id,
                            "agent_name": agent.name,
                            "active_model": agent.active_model,
                        },
                    )
                )
            if agent.mcps:
                agent_children.append(
                    self._build_folder_node(
                        f"{agent.id}_mcps",
                        "mcps",
                        "MCPs",
                        "mcp",
                        agent.mcps,
                        {"business_unit_id": business_unit.id, "agent_name": agent.name},
                    )
                )

            output_node = self._build_output_node(business_unit.id, agent.name, agent.id)
            if output_node is not None:
                agent_children.append(output_node)

            children.append(
                BusinessUnitTreeNode(
                    id=agent.id,
                    name=agent.name,
                    display_name=agent.display_name or agent.name,
                    node_type="agent",
                    children=agent_children,
                    metadata={
                        "description": agent.description,
                        "business_unit_id": business_unit.id,
                        "active_model": agent.active_model,
                    },
                )
            )

        for bundle in business_unit.asset_bundles:
            assets = self._business_unit_service.asset_bundle_service.scan_assets(business_unit.id, bundle.name)
            asset_children = [
                BusinessUnitTreeNode(
                    id=asset.id,
                    name=asset.name,
                    display_name=asset.display_name or asset.name,
                    node_type=asset.asset_type.value if hasattr(asset.asset_type, "value") else str(asset.asset_type),
                    bundle_type=bundle.bundle_type,
                    metadata={
                        "business_unit_id": business_unit.id,
                        "bundle_name": bundle.name,
                        "description": asset.description,
                    },
                )
                for asset in assets
            ]
            children.append(
                BusinessUnitTreeNode(
                    id=bundle.id,
                    name=bundle.name,
                    display_name=bundle.display_name or bundle.name,
                    node_type="asset_bundle",
                    bundle_type=bundle.bundle_type,
                    children=asset_children,
                    metadata={
                        "description": bundle.description,
                        "has_connection": bundle.connection is not None,
                        "business_unit_id": business_unit.id,
                    },
                )
            )

        return BusinessUnitTreeNode(
            id=business_unit.id,
            name=business_unit.name,
            display_name=business_unit.display_name or business_unit.name,
            node_type="business_unit",
            children=children,
            metadata={"description": business_unit.description},
        )

    @staticmethod
    def _build_folder_node(
        node_id: str,
        name: str,
        display_name: str,
        child_type: str,
        items: List[str],
        metadata: Dict,
    ) -> BusinessUnitTreeNode:
        return BusinessUnitTreeNode(
            id=node_id,
            name=name,
            display_name=display_name,
            node_type="folder",
            children=[
                BusinessUnitTreeNode(
                    id=f"{node_id}_{item}",
                    name=item,
                    display_name=item,
                    node_type=child_type,
                    metadata=metadata,
                )
                for item in items
            ],
            metadata=metadata,
        )

    def _build_output_node(self, business_unit_id: str, agent_name: str, agent_id: str) -> Optional[BusinessUnitTreeNode]:
        agent_path = self._business_unit_service.agent_service._get_agent_path(business_unit_id, agent_name)
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
        current_path = root_path / relative_path if relative_path else root_path
        if not current_path.exists() or not current_path.is_dir():
            return []

        nodes: List[BusinessUnitTreeNode] = []
        for item in sorted(current_path.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
            if item.name.startswith('.'):
                continue

            item_relative = f"{relative_path}/{item.name}" if relative_path else item.name
            node_id = f"{parent_id}/{item.name}"
            if item.is_dir():
                nodes.append(
                    BusinessUnitTreeNode(
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
                    )
                )
                continue

            nodes.append(
                BusinessUnitTreeNode(
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
                )
            )
        return nodes
