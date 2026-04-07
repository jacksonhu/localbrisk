"""Unit tests for the built-in subagent registry."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest


class TestSubagentRegistry:
    """Registry behavior tests."""

    def test_create_default_subagent_registry_contains_data_analysis_agent(self):
        from agent_engine.engine.subagents import create_default_subagent_registry

        registry = create_default_subagent_registry()

        assert registry.list_names() == ["data_analysis_agent"]

    def test_register_rejects_duplicate_builder_names(self):
        from agent_engine.engine.subagents import SubagentBuildResult, SubagentRegistry

        registry = SubagentRegistry()

        def build_table_analysis(_context):
            return SubagentBuildResult(
                definition={
                    "name": "data_analysis_agent",
                    "description": "Table analysis",
                    "system_prompt": "Prompt",
                }
            )

        registry.register("data_analysis_agent", build_table_analysis)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("data_analysis_agent", build_table_analysis)

    def test_build_builtin_subagents_aggregates_custom_resources(self):
        from agent_engine.engine.subagents import (
            SubagentBuildResult,
            SubagentRegistry,
            build_builtin_subagents,
        )

        registry = SubagentRegistry()

        def build_custom_agent(context):
            return SubagentBuildResult(
                definition={
                    "name": "custom_agent",
                    "description": "Custom test agent",
                    "system_prompt": "Prompt",
                    "tools": context.parent_tools,
                    "model": context.parent_model,
                },
                resources={"custom_service": "mock-service"},
            )

        registry.register("custom_agent", build_custom_agent)

        collection = build_builtin_subagents(
            parent_model="mock-model",
            parent_tools=["generic-tool"],
            parent_backend=None,
            registry=registry,
        )

        assert collection.subagents == [
            {
                "name": "custom_agent",
                "description": "Custom test agent",
                "system_prompt": "Prompt",
                "tools": ["generic-tool"],
                "model": "mock-model",
            }
        ]
        assert collection.resources == {"custom_service": "mock-service"}


class TestBuiltinSubagentCompatibility:
    """Compatibility tests for the public create helper."""

    def test_create_builtin_subagents_falls_back_to_parent_tools_when_text2sql_build_fails(self, monkeypatch):
        from agent_engine.engine.subagents import create_builtin_subagents

        def broken_create_text2sql_tools(*, business_unit_path, asset_bundles):
            raise RuntimeError(
                f"unexpected build failure for {business_unit_path} with {len(asset_bundles)} bundles"
            )

        monkeypatch.setattr(
            "agent_engine.engine.subagents.text2sql.create_text2sql_tools",
            broken_create_text2sql_tools,
        )

        subagents, text2sql_service = create_builtin_subagents(
            parent_model="mock-model",
            parent_tools=["generic-tool"],
            parent_backend=None,
            business_unit_path="/tmp/test_unit",
            asset_bundles=[{"bundle_name": "sales_bundle"}],
        )

        assert text2sql_service is None
        assert len(subagents) == 1
        assert subagents[0]["name"] == "data_analysis_agent"
        assert subagents[0]["tools"] == ["generic-tool"]

    def test_create_builtin_subagents_normalizes_bundle_objects(self, monkeypatch):
        from agent_engine.engine.subagents import create_builtin_subagents

        captured_args = {}

        class FakeService:
            attached_sources = {"sales_bundle": "mysql"}

        def fake_create_text2sql_tools(*, business_unit_path, asset_bundles):
            captured_args["business_unit_path"] = business_unit_path
            captured_args["asset_bundles"] = asset_bundles
            return ["duckdb_query"], FakeService()

        @dataclass
        class BundleConfig:
            bundle_name: str
            bundle_type: str
            bundle_path: str
            mount_path: str
            volumes: list[str] = field(default_factory=list)

        monkeypatch.setattr(
            "agent_engine.engine.subagents.text2sql.create_text2sql_tools",
            fake_create_text2sql_tools,
        )

        subagents, text2sql_service = create_builtin_subagents(
            parent_model="mock-model",
            parent_tools=["generic-tool"],
            parent_backend=None,
            business_unit_path="/tmp/test_unit",
            asset_bundles=[
                BundleConfig(
                    bundle_name="sales_bundle",
                    bundle_type="external",
                    bundle_path="/tmp/test_unit/asset_bundles/sales_bundle",
                    mount_path="/sales_bundle",
                )
            ],
        )

        assert captured_args["business_unit_path"] == "/tmp/test_unit"
        assert captured_args["asset_bundles"] == [
            {
                "bundle_name": "sales_bundle",
                "bundle_type": "external",
                "bundle_path": "/tmp/test_unit/asset_bundles/sales_bundle",
                "mount_path": "/sales_bundle",
                "volumes": [],
            }
        ]
        assert text2sql_service is not None
        assert subagents[0]["tools"] == ["duckdb_query"]
