"""Unit tests for ``deepagents_engine.py``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


class TestDeepAgentsEngineImport:
    """Import smoke tests."""

    def test_import_deepagents_engine(self):
        from agent_engine.engine import deepagents_engine

        assert hasattr(deepagents_engine, "DeepAgentsEngine")
        assert hasattr(deepagents_engine, "AgentBuildContext")
        assert hasattr(deepagents_engine, "get_deepagents_engine")
        assert hasattr(deepagents_engine, "check_dependencies")

    def test_import_from_engine_init(self):
        from agent_engine.engine import (
            AgentBuildContext,
            DeepAgentsEngine,
            check_dependencies,
            get_deepagents_engine,
        )

        assert DeepAgentsEngine is not None
        assert AgentBuildContext is not None
        assert get_deepagents_engine is not None
        assert check_dependencies is not None


class TestCheckDependencies:
    """Dependency status tests."""

    def test_check_dependencies_no_raise(self):
        from agent_engine.engine.deepagents_engine import check_dependencies

        result = check_dependencies(raise_error=False)
        assert isinstance(result, bool)

    def test_check_dependencies_returns_status(self):
        from agent_engine.engine.deepagents_engine import (
            _DEEPAGENTS_AVAILABLE,
            _LANGCHAIN_AVAILABLE,
            _LANGGRAPH_AVAILABLE,
            check_dependencies,
        )

        result = check_dependencies(raise_error=False)
        assert result == (_LANGCHAIN_AVAILABLE and _LANGGRAPH_AVAILABLE and _DEEPAGENTS_AVAILABLE)


class TestDeepAgentsEngineSingleton:
    """Singleton tests."""

    def test_get_deepagents_engine_singleton(self):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        engine1 = get_deepagents_engine()
        engine2 = get_deepagents_engine()

        assert engine1 is engine2

    def test_engine_initialization(self):
        from agent_engine.engine.deepagents_engine import DeepAgentsEngine

        engine = DeepAgentsEngine()

        assert engine is not None
        assert engine._llm_factory is None
        assert engine._model_resolver is None
        assert engine._checkpointer_contexts == {}
        assert engine._text2sql_services == {}


class TestAgentBuildContext:
    """Dataclass tests."""

    def test_agent_build_context_creation(self):
        from agent_engine.engine.deepagents_engine import AgentBuildContext

        context = AgentBuildContext(
            business_unit_path="/path/to/business_unit",
            agent_name="test_agent",
            agent_path="/path/to/agent",
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test"}},
            model_config={"model_type": "endpoint"},
            memories=["/memories/default.md"],
            skills=[],
            output_path="/path/to/output",
        )

        assert context.agent_name == "test_agent"
        assert context.business_unit_id == "test_unit"
        assert context.memories == ["/memories/default.md"]
        assert context.asset_bundles == []


@pytest.fixture
def temp_business_unit_agent_dir(tmp_path: Path) -> dict:
    """Create a BusinessUnit-like structure with one external asset bundle."""
    business_unit_dir = tmp_path / "test_unit"
    agent_dir = business_unit_dir / "agents" / "test_data_analyst"
    asset_bundle_dir = business_unit_dir / "asset_bundles" / "sales_bundle"
    tables_dir = asset_bundle_dir / "tables"
    models_dir = agent_dir / "models"
    skills_dir = agent_dir / "skills" / "test_skill"
    output_dir = agent_dir / "output"

    tables_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    agent_spec = {
        "baseinfo": {"name": "test_data_analyst", "description": "Test agent"},
        "active_model": "test_model",
        "llm_config": {"temperature": 0.2, "max_tokens": 1024},
    }
    model_config = {
        "model_type": "endpoint",
        "endpoint_provider": "openai",
        "api_base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "model_id": "gpt-4o-mini",
        "temperature": 0.2,
    }
    bundle_yaml = {
        "bundle_type": "external",
        "connection": {
            "type": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "db_name": "sales_db",
            "username": "demo",
            "password": "secret",
        },
    }
    table_yaml = {
        "baseinfo": {"name": "orders", "description": "Order facts"},
        "schema_name": "sales_db",
        "primary_keys": ["id"],
        "columns": [
            {"name": "id", "data_type": "bigint", "nullable": False, "is_primary_key": True, "comment": "PK"},
            {"name": "amount", "data_type": "decimal(10,2)", "nullable": False, "is_primary_key": False, "comment": "Amount"},
        ],
    }

    with open(agent_dir / "agent_spec.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(agent_spec, file, allow_unicode=True, sort_keys=False)
    with open(models_dir / "test_model.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(model_config, file, allow_unicode=True, sort_keys=False)
    with open(skills_dir / "SKILL.md", "w", encoding="utf-8") as file:
        file.write("# Test Skill\n\nSkill content.")
    with open(asset_bundle_dir / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(bundle_yaml, file, allow_unicode=True, sort_keys=False)
    with open(tables_dir / "orders.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(table_yaml, file, allow_unicode=True, sort_keys=False)

    return {
        "business_unit_dir": business_unit_dir,
        "agent_path": str(agent_dir),
    }


class TestLoadAgentContext:
    """Context loading tests."""

    @pytest.mark.asyncio
    async def test_load_agent_context_success(self, temp_agent_dir):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        engine = get_deepagents_engine()
        context = await engine._load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert context is not None
        assert context.agent_name == "test_data_analyst"
        assert context.business_unit_id == "test_unit"
        assert Path(context.agent_path).exists()

    @pytest.mark.asyncio
    async def test_load_agent_context_with_model(self, temp_agent_dir):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        engine = get_deepagents_engine()
        context = await engine._load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert context.model_config is not None
        assert context.model_config.get("endpoint_provider") == "openai"
        assert context.model_config.get("model_id") == "gpt-4"

    @pytest.mark.asyncio
    async def test_load_agent_context_with_skills(self, temp_agent_dir):
        from agent_engine.engine.deepagents_engine import SkillConfig, get_deepagents_engine

        engine = get_deepagents_engine()
        context = await engine._load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert len(context.skills) >= 1
        skill_config = context.skills[0]
        assert isinstance(skill_config, SkillConfig)
        assert skill_config.name == "test_skill"
        assert "test_skill" in skill_config.absolute_path
        assert skill_config.mount_path == "/skills/test_skill/"

    @pytest.mark.asyncio
    async def test_load_agent_context_nonexistent_path(self):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        engine = get_deepagents_engine()

        with pytest.raises(ValueError, match="does not exist"):
            await engine._load_agent_context("/nonexistent/agent/path", "test_unit")

    @pytest.mark.asyncio
    async def test_load_agent_context_output_created(self, temp_agent_dir):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        output_dir = Path(temp_agent_dir["agent_path"]) / "output"
        if output_dir.exists():
            output_dir.rmdir()

        engine = get_deepagents_engine()
        context = await engine._load_agent_context(temp_agent_dir["agent_path"], "test_unit")

        assert Path(context.output_path).exists()

    @pytest.mark.asyncio
    async def test_load_agent_context_with_asset_bundles(self, temp_business_unit_agent_dir):
        from agent_engine.engine.deepagents_engine import get_deepagents_engine

        engine = get_deepagents_engine()
        context = await engine._load_agent_context(
            temp_business_unit_agent_dir["agent_path"],
            "test_unit",
        )

        assert len(context.asset_bundles) == 1
        bundle = context.asset_bundles[0]
        assert bundle.bundle_name == "sales_bundle"
        assert bundle.bundle_type == "external"
        assert bundle.bundle_path.endswith("sales_bundle")


class TestBuildAgent:
    """Build entry tests."""

    @pytest.mark.asyncio
    async def test_build_agent_requires_deepagents(self, temp_agent_dir):
        from agent_engine.engine.deepagents_engine import (
            _DEEPAGENTS_AVAILABLE,
            get_deepagents_engine,
        )

        if _DEEPAGENTS_AVAILABLE:
            pytest.skip("deepagents is installed in this environment")

        engine = get_deepagents_engine()

        with pytest.raises(ImportError, match="Missing required dependencies"):
            await engine.build_agent(temp_agent_dir["agent_path"], "test_unit")

    @pytest.mark.asyncio
    async def test_build_agent_passes_asset_bundles_to_builtin_subagents(self, tmp_path, monkeypatch):
        from agent_engine.engine import deepagents_engine as engine_module

        engine = engine_module.DeepAgentsEngine()
        agent_dir = tmp_path / "agent"
        output_dir = agent_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        context = engine_module.AgentBuildContext(
            business_unit_path=str(tmp_path / "test_unit"),
            agent_name="test_agent",
            agent_path=str(agent_dir),
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test_agent"}},
            model_config={"model_type": "endpoint"},
            memories=[],
            skills=[],
            output_path=str(output_dir),
            asset_bundles=[
                {
                    "bundle_name": "sales_bundle",
                    "bundle_type": "external",
                    "bundle_path": str(tmp_path / "test_unit" / "asset_bundles" / "sales_bundle"),
                    "mount_path": "/sales_bundle",
                    "volumes": [],
                }
            ],
        )

        engine._load_agent_context = AsyncMock(return_value=context)
        engine._create_llm_client = AsyncMock(return_value="mock-llm")
        engine._enter_checkpointer_context = AsyncMock(return_value="checkpointer")

        monkeypatch.setattr(engine_module, "check_dependencies", lambda raise_error=True: True)
        monkeypatch.setattr(engine, "_load_base_system_prompt", lambda: "cwd={{cwd}}")
        monkeypatch.setattr(engine, "_create_backend", lambda _: "mock-backend")
        monkeypatch.setattr("agent_engine.tools.get_builtin_tools", lambda backend, task_root: ["builtin-tool"])

        captured_subagent_args = {}

        def fake_create_builtin_subagents(**kwargs):
            captured_subagent_args.update(kwargs)
            return ([{"name": "data_analysis_agent", "tools": ["duckdb_query"]}], "mock-service")

        monkeypatch.setattr(engine_module, "create_builtin_subagents", fake_create_builtin_subagents)
        monkeypatch.setattr(
            engine_module,
            "AsyncSqliteSaver",
            type("FakeAsyncSqliteSaver", (), {"from_conn_string": staticmethod(lambda _: object())}),
        )
        monkeypatch.setattr(engine_module, "InMemorySaver", lambda: "memory-saver")
        monkeypatch.setattr(engine_module, "InMemoryCache", lambda: "memory-cache")
        monkeypatch.setattr(engine_module, "create_deep_agent", lambda **kwargs: {"agent": kwargs["subagents"]})

        agent = await engine.build_agent(str(agent_dir), "test_unit")

        assert captured_subagent_args["business_unit_path"] == context.business_unit_path
        assert captured_subagent_args["asset_bundles"] == context.asset_bundles
        assert captured_subagent_args["parent_tools"] == ["builtin-tool"]
        assert engine._text2sql_services[id(agent)] == "mock-service"
        assert id(agent) in engine._checkpointer_contexts


class TestSetModelResolver:
    """Resolver tests."""

    def test_set_model_resolver(self):
        from agent_engine.engine.deepagents_engine import DeepAgentsEngine

        engine = DeepAgentsEngine()

        async def mock_resolver(unit_id, agent_name, model_name):
            return {"model_id": "test"}

        engine.set_model_resolver(mock_resolver)

        assert engine._model_resolver is mock_resolver


class TestBuiltinSubagents:
    """Built-in sub-agent tests."""

    def test_create_builtin_subagents_returns_data_analysis_agent(self):
        from agent_engine.engine.subagents import create_builtin_subagents

        subagents, text2sql_service = create_builtin_subagents(
            parent_model="mock-model",
            parent_tools=["generic-tool"],
            parent_backend=None,
        )

        assert text2sql_service is None
        assert len(subagents) == 1
        agent = subagents[0]
        assert agent["name"] == "data_analysis_agent"
        assert agent["description"] == (
            "Tabular analysis across local CSV/Excel files and remote databases, "
            "including joint querying and result interpretation"
        )
        assert agent["tools"] == ["generic-tool"]

    def test_create_builtin_subagents_uses_dedicated_text2sql_tools(self, monkeypatch):
        from agent_engine.engine.subagents import create_builtin_subagents

        fake_service = MagicMock()
        fake_service.attached_sources = {"sales_bundle": "mysql"}
        fake_tools = ["duckdb_query", "list_table_metadata"]

        def fake_create_text2sql_tools(*, business_unit_path, asset_bundles):
            assert business_unit_path == "/tmp/test_unit"
            assert asset_bundles == [{"bundle_name": "sales_bundle", "bundle_type": "external", "bundle_path": "/tmp/test_unit/asset_bundles/sales_bundle", "mount_path": "/sales_bundle", "volumes": []}]
            return fake_tools, fake_service

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
                {
                    "bundle_name": "sales_bundle",
                    "bundle_type": "external",
                    "bundle_path": "/tmp/test_unit/asset_bundles/sales_bundle",
                    "mount_path": "/sales_bundle",
                    "volumes": [],
                }
            ],
        )

        assert text2sql_service is fake_service
        assert len(subagents) == 1
        assert subagents[0]["tools"] == fake_tools


class TestCloseAgentResources:
    """Resource cleanup tests."""

    @pytest.mark.asyncio
    async def test_close_agent_resources_releases_checkpointer_and_text2sql(self):
        from agent_engine.engine.deepagents_engine import DeepAgentsEngine

        engine = DeepAgentsEngine()
        fake_agent = object()
        fake_cm = MagicMock()
        fake_service = MagicMock()
        fake_service.close = MagicMock()

        engine._checkpointer_contexts[id(fake_agent)] = fake_cm
        engine._text2sql_services[id(fake_agent)] = fake_service

        async def fake_exit(cm):
            assert cm is fake_cm

        engine._exit_checkpointer_context = AsyncMock(side_effect=fake_exit)

        await engine.close_agent_resources(fake_agent)

        fake_service.close.assert_called_once()
        engine._exit_checkpointer_context.assert_awaited_once_with(fake_cm)
        assert id(fake_agent) not in engine._checkpointer_contexts
        assert id(fake_agent) not in engine._text2sql_services
