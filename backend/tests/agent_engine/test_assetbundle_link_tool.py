"""Tests for the runtime asset bundle discovery tool."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agent_engine.engine.agent_context_loader import load_asset_bundles
from agent_engine.tools import build_builtin_tools, create_assetbundle_link_tool
from agent_engine.tools.shell import ShellRuntimeBootstrap


@pytest.fixture
def assetbundle_business_unit(tmp_path: Path) -> dict:
    business_unit_dir = tmp_path / "myunit"
    asset_bundles_dir = business_unit_dir / "asset_bundles"
    local_bundle_dir = asset_bundles_dir / "myasset"
    external_bundle_dir = asset_bundles_dir / "externalmysql"
    local_storage_dir = tmp_path / "analysis"

    (local_bundle_dir / "volumes").mkdir(parents=True, exist_ok=True)
    (local_bundle_dir / "functions").mkdir(parents=True, exist_ok=True)
    (external_bundle_dir / "tables").mkdir(parents=True, exist_ok=True)
    (external_bundle_dir / "functions").mkdir(parents=True, exist_ok=True)
    local_storage_dir.mkdir(parents=True, exist_ok=True)
    (local_storage_dir / "monthly.csv").write_text("month,amount\n2026-01,10\n", encoding="utf-8")
    (local_storage_dir / "notes.txt").write_text("summary", encoding="utf-8")

    with open(local_bundle_dir / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "baseinfo": {
                    "name": "myasset",
                    "display_name": "My Asset",
                    "description": "Local business files",
                },
                "bundle_type": "local",
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    with open(local_bundle_dir / "volumes" / "my_files.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "baseinfo": {
                    "name": "my_files",
                    "display_name": "My Files",
                    "description": "Monthly reports",
                },
                "asset_type": "volume",
                "source": "local",
                "volume_type": "local",
                "storage_location": str(local_storage_dir),
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    with open(external_bundle_dir / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "baseinfo": {
                    "name": "externalmysql",
                    "display_name": "External MySQL",
                    "description": "Remote metadata",
                },
                "bundle_type": "external",
                "connection": {
                    "type": "mysql",
                    "host": "127.0.0.1",
                    "port": 3306,
                    "db_name": "onecatalog",
                    "username": "root",
                    "password": "root@123",
                },
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    with open(external_bundle_dir / "tables" / "catalogs.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "baseinfo": {
                    "name": "catalogs",
                    "display_name": "Catalogs",
                    "description": "Catalog metadata",
                },
                "schema_name": "externalmysql",
                "table_type": "BASE TABLE",
                "primary_keys": ["id"],
                "columns": [
                    {"name": "id", "data_type": "bigint", "nullable": False, "is_primary_key": True},
                    {"name": "name", "data_type": "varchar(255)", "nullable": False, "is_primary_key": False},
                ],
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    asset_bundles = load_asset_bundles(business_unit_dir, "myunit")
    return {
        "business_unit_dir": business_unit_dir,
        "local_storage_dir": local_storage_dir,
        "asset_bundles": asset_bundles,
    }


class TestAssetBundleLinkTool:
    def test_assetbundle_link_overview_lists_bundles_without_secrets(self, assetbundle_business_unit: dict):
        tool = create_assetbundle_link_tool(
            business_unit_path=str(assetbundle_business_unit["business_unit_dir"]),
            asset_bundles=assetbundle_business_unit["asset_bundles"],
        )

        result = tool._run()

        assert tool.name == "assetbundle_link"
        assert "Mode: `overview`" in result
        assert "## Bundle `externalmysql`" in result
        assert "## Bundle `myasset`" in result
        assert "Connection summary: mysql, host=127.0.0.1:3306, db=onecatalog" in result
        assert "root@123" not in result
        assert "password" not in result

    def test_assetbundle_link_returns_local_volume_paths_and_samples(self, assetbundle_business_unit: dict):
        tool = create_assetbundle_link_tool(
            business_unit_path=str(assetbundle_business_unit["business_unit_dir"]),
            asset_bundles=assetbundle_business_unit["asset_bundles"],
        )

        result = tool._run(
            bundle_name="myasset",
            asset_type="volume",
            include_path_samples=True,
            sample_limit=3,
        )

        assert "Mode: `resource`" in result
        assert "### Volume `my_files`" in result
        assert f"- Linked path: `{assetbundle_business_unit['local_storage_dir'].resolve()}`" in result
        assert "- Path status: exists (directory)" in result
        assert "`monthly.csv`" in result
        assert "`notes.txt`" in result
        assert "file_search" in result

    def test_assetbundle_link_filters_external_tables(self, assetbundle_business_unit: dict):
        tool = create_assetbundle_link_tool(
            business_unit_path=str(assetbundle_business_unit["business_unit_dir"]),
            asset_bundles=assetbundle_business_unit["asset_bundles"],
        )

        result = tool._run(bundle_name="externalmysql", asset_type="table", keyword="catalog")

        assert "### Table `catalogs`" in result
        assert "- Schema: `externalmysql`" in result
        assert "- Column count: 2" in result
        assert "- Primary keys: `id`" in result
        assert "root@123" not in result
        assert "password" not in result

    def test_build_builtin_tools_includes_assetbundle_link(self, assetbundle_business_unit: dict, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(ShellRuntimeBootstrap, "ensure_ready", lambda self: None)

        tools = build_builtin_tools(
            agent_path=str(tmp_path / "agent"),
            task_root=str(tmp_path / ".task"),
            business_unit_path=str(assetbundle_business_unit["business_unit_dir"]),
            asset_bundles=assetbundle_business_unit["asset_bundles"],
        )
        tool_names = [tool.name for tool in tools]

        assert "assetbundle_link" in tool_names
