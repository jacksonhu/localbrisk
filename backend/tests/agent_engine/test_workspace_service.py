"""Unit tests for workspace service and workspace factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_engine.engine.workspace_factory import create_workspace_backend
from agent_engine.engine.agent_context_loader import AgentBuildContext, AssetBundleBackendConfig
from agent_engine.services.workspace_service import WorkspaceMount, WorkspaceService
from agent_engine.utils.path_resolver import list_backend_routes, resolve_virtual_path


@pytest.fixture
def workspace_layout(tmp_path: Path):
    """Create one agent workspace plus one external asset bundle mount."""
    business_unit_dir = tmp_path / "test_unit"
    agent_dir = business_unit_dir / "agents" / "test_agent"
    output_dir = agent_dir / "output"
    hidden_tool_dir = agent_dir / ".large_tool_results"
    bundle_tables_dir = business_unit_dir / "asset_bundles" / "sales_bundle" / "tables"

    output_dir.mkdir(parents=True, exist_ok=True)
    hidden_tool_dir.mkdir(parents=True, exist_ok=True)
    bundle_tables_dir.mkdir(parents=True, exist_ok=True)

    (agent_dir / "report.txt").write_text("local report", encoding="utf-8")
    (output_dir / "result.md").write_text("generated result", encoding="utf-8")
    (hidden_tool_dir / "trace.json").write_text("{}", encoding="utf-8")
    (bundle_tables_dir / "orders.csv").write_text("id,amount\n1,99", encoding="utf-8")

    context = AgentBuildContext(
        business_unit_path=str(business_unit_dir),
        agent_path=str(agent_dir),
        agent_name="test_agent",
        business_unit_id="test_unit",
        agent_spec={"baseinfo": {"name": "test_agent"}},
        model_config={"model_id": "gpt-4o-mini"},
        memories=[],
        skills=[],
        output_path=str(output_dir),
        asset_bundles=[
            AssetBundleBackendConfig(
                bundle_name="sales_bundle",
                bundle_type="external",
                bundle_path=str(bundle_tables_dir.parent),
                mount_path="/sales_bundle",
                volumes=[],
            )
        ],
    )
    return {"context": context, "bundle_tables_dir": bundle_tables_dir}


class TestWorkspaceService:
    """Workspace path and listing tests."""

    def test_resolve_virtual_path_blocks_path_traversal(self, tmp_path: Path):
        workspace = WorkspaceService(root_dir=tmp_path)

        with pytest.raises(ValueError, match="Path traversal"):
            workspace.resolve_virtual_path("../secret.txt")

    def test_root_listing_includes_mount_placeholders(self, workspace_layout):
        workspace = create_workspace_backend(workspace_layout["context"])

        entries = workspace.ls_info("/")
        paths = {entry["path"] for entry in entries}

        assert "/report.txt" in paths
        assert "/output" in paths
        assert "/sales_bundle" in paths

    def test_resolve_virtual_path_uses_mounts_and_system_routes(self, workspace_layout):
        workspace = create_workspace_backend(workspace_layout["context"])

        resolved_bundle = resolve_virtual_path(workspace, "/sales_bundle/orders.csv")
        resolved_tool_result = resolve_virtual_path(workspace, "/large_tool_results/trace.json")

        assert resolved_bundle == str(workspace_layout["bundle_tables_dir"] / "orders.csv")
        assert resolved_tool_result.endswith("/.large_tool_results/trace.json")

    def test_list_backend_routes_supports_workspace_service(self, workspace_layout):
        workspace = create_workspace_backend(workspace_layout["context"])

        routes = list_backend_routes(workspace)

        assert routes["/"] == str(Path(workspace_layout["context"].agent_path).resolve())
        assert routes["/sales_bundle"] == str(workspace_layout["bundle_tables_dir"].resolve())

    def test_mount_normalization_rejects_escaping_root(self, tmp_path: Path):
        safe_root = tmp_path / "safe"
        safe_root.mkdir(parents=True, exist_ok=True)
        workspace = WorkspaceService(
            root_dir=safe_root,
            mounts=[WorkspaceMount(virtual_prefix="/shared", real_path=str(tmp_path))],
        )

        with pytest.raises(ValueError, match="Path traversal"):
            workspace.resolve_virtual_path("/shared/../outside.txt")
