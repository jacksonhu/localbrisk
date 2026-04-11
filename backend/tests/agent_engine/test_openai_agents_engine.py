"""Unit tests for ``openai_agents_engine.py``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def openai_runtime_context(tmp_path: Path):
    """Create one minimal agent directory that can feed the OpenAI runtime builder."""
    business_unit_dir = tmp_path / "test_unit"
    agent_dir = business_unit_dir / "agents" / "test_agent"
    output_dir = agent_dir / "output"
    memories_dir = agent_dir / "memories"
    skill_dir = agent_dir / "skills" / "analysis_skill"

    output_dir.mkdir(parents=True, exist_ok=True)
    memories_dir.mkdir(parents=True, exist_ok=True)
    skill_dir.mkdir(parents=True, exist_ok=True)

    (memories_dir / "default.md").write_text("Remember to verify results before responding.", encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("Use tabular reasoning when data is present.", encoding="utf-8")

    return {
        "business_unit_dir": business_unit_dir,
        "agent_dir": agent_dir,
        "output_dir": output_dir,
    }


class TestOpenAIAgentsEngineImport:
    """Import smoke tests."""

    def test_import_openai_agents_engine(self):
        from agent_engine.engine import openai_agents_engine

        assert hasattr(openai_agents_engine, "OpenAIAgentsEngine")
        assert hasattr(openai_agents_engine, "OpenAIAgentRuntime")
        assert hasattr(openai_agents_engine, "get_openai_agents_engine")
        assert hasattr(openai_agents_engine, "check_openai_agents_dependencies")

    def test_import_from_engine_init(self):
        from agent_engine.engine import (
            OpenAIAgentRuntime,
            OpenAIAgentsEngine,
            check_openai_agents_dependencies,
            get_openai_agents_engine,
        )

        assert OpenAIAgentRuntime is not None
        assert OpenAIAgentsEngine is not None
        assert get_openai_agents_engine is not None
        assert check_openai_agents_dependencies is not None


class TestOpenAIAgentsEngineSingleton:
    """Singleton behavior tests."""

    def test_get_openai_agents_engine_singleton(self):
        from agent_engine.engine.openai_agents_engine import get_openai_agents_engine

        engine1 = get_openai_agents_engine()
        engine2 = get_openai_agents_engine()

        assert engine1 is engine2


class TestOpenAIAgentsDependencies:
    """Dependency checks."""

    def test_check_openai_agents_dependencies_no_raise(self):
        from agent_engine.engine.openai_agents_engine import check_openai_agents_dependencies

        result = check_openai_agents_dependencies(raise_error=False)
        assert isinstance(result, bool)


class TestOpenAIAgentRuntime:
    """Runtime wrapper tests."""

    def test_get_session_reuses_cached_sqlite_session(self, openai_runtime_context, monkeypatch):
        from agent_engine.engine import openai_agents_engine as engine_module

        context = engine_module.AgentBuildContext(
            business_unit_path=str(openai_runtime_context["business_unit_dir"]),
            agent_path=str(openai_runtime_context["agent_dir"]),
            agent_name="test_agent",
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test_agent"}},
            model_config={"model_id": "gpt-4o-mini"},
            memories=[],
            skills=[],
            output_path=str(openai_runtime_context["output_dir"]),
        )

        created_sessions = []

        class FakeSQLiteSession:
            def __init__(self, session_id=None, db_path=None):
                self.session_id = session_id
                self.db_path = db_path
                created_sessions.append(self)

        monkeypatch.setattr(engine_module, "_OPENAI_AGENTS_AVAILABLE", True)
        monkeypatch.setattr(engine_module, "SQLiteSession", FakeSQLiteSession)

        runtime = engine_module.OpenAIAgentRuntime(
            agent=object(),
            context=context,
            session_db_path=str(openai_runtime_context["output_dir"] / ".openai_sessions.sqlite"),
            model="mock-model",
            tools=[],
            sdk_tools=[],
        )

        first = runtime.get_session("session-1")
        second = runtime.get_session("session-1")

        assert first is second
        assert len(created_sessions) == 1
        assert created_sessions[0].db_path.endswith(".openai_sessions.sqlite")

    @pytest.mark.asyncio
    async def test_run_streamed_returns_stream_result_without_awaiting(self, openai_runtime_context, monkeypatch):
        from agent_engine.engine import openai_agents_engine as engine_module

        context = engine_module.AgentBuildContext(
            business_unit_path=str(openai_runtime_context["business_unit_dir"]),
            agent_path=str(openai_runtime_context["agent_dir"]),
            agent_name="test_agent",
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test_agent"}},
            model_config={"model_id": "gpt-4o-mini"},
            memories=[],
            skills=[],
            output_path=str(openai_runtime_context["output_dir"]),
        )

        stream_result = object()

        class FakeRunner:
            @staticmethod
            def run_streamed(*args, **kwargs):
                return stream_result

        monkeypatch.setattr(engine_module, "_OPENAI_AGENTS_AVAILABLE", True)
        monkeypatch.setattr(engine_module, "Runner", FakeRunner)

        runtime = engine_module.OpenAIAgentRuntime(
            agent=object(),
            context=context,
            session_db_path=str(openai_runtime_context["output_dir"] / ".openai_sessions.sqlite"),
            model="mock-model",
            tools=[],
            sdk_tools=[],
        )

        result = await runtime.run_streamed("hello", session_id="session-1")

        assert result is stream_result


class TestOpenAIAgentsEngineBuild:
    """Runtime build entry tests."""

    def test_build_instructions_embeds_memory_and_skill_content(self, openai_runtime_context):
        from agent_engine.engine import openai_agents_engine as engine_module

        memory_path = "/memories/default.md"
        skill_config = engine_module.SkillConfig(
            name="analysis_skill",
            absolute_path=str(openai_runtime_context["agent_dir"] / "skills" / "analysis_skill"),
            mount_path="/skills/analysis_skill/",
        )
        context = engine_module.AgentBuildContext(
            business_unit_path=str(openai_runtime_context["business_unit_dir"]),
            agent_path=str(openai_runtime_context["agent_dir"]),
            agent_name="test_agent",
            business_unit_id="test_unit",
            agent_spec={
                "baseinfo": {"name": "test_agent", "description": "Analyze business data."},
                "instruction": {"system_prompt": "Always explain your reasoning."},
            },
            model_config={"model_id": "gpt-4o-mini"},
            memories=[memory_path],
            skills=[skill_config],
            output_path=str(openai_runtime_context["output_dir"]),
        )

        engine = engine_module.OpenAIAgentsEngine()
        instructions = engine._build_instructions(context)

        assert "Analyze business data." in instructions
        assert "Always explain your reasoning." in instructions
        assert "Remember to verify results before responding." in instructions
        assert "Use tabular reasoning when data is present." in instructions

    @pytest.mark.asyncio
    async def test_build_agent_adapts_tools_and_returns_runtime(self, openai_runtime_context, monkeypatch):
        from agent_engine.engine import openai_agents_engine as engine_module

        captured: dict = {}
        context = engine_module.AgentBuildContext(
            business_unit_path=str(openai_runtime_context["business_unit_dir"]),
            agent_path=str(openai_runtime_context["agent_dir"]),
            agent_name="test_agent",
            business_unit_id="test_unit",
            agent_spec={
                "baseinfo": {"name": "test_agent", "description": "Analyze business data."},
                "llm_config": {"temperature": 0.4, "max_tokens": 2048},
            },
            model_config={
                "model_id": "gpt-4o-mini",
                "endpoint_provider": "openai",
                "api_base_url": "https://example.com/v1",
                "api_key": "sk-test-key",
            },
            memories=["/memories/default.md"],
            skills=[
                engine_module.SkillConfig(
                    name="analysis_skill",
                    absolute_path=str(openai_runtime_context["agent_dir"] / "skills" / "analysis_skill"),
                    mount_path="/skills/analysis_skill/",
                )
            ],
            output_path=str(openai_runtime_context["output_dir"]),
        )

        class FakeAgent:
            def __init__(self, **kwargs):
                captured["agent_kwargs"] = kwargs
                self.kwargs = kwargs
                self.name = kwargs["name"]

        class FakeModelBundle:
            model = "sdk-model"
            model_settings = {"temperature": 0.4, "max_tokens": 2048}
            provider = "openai"
            model_id = "gpt-4o-mini"
            api_base_url = "https://example.com/v1"

        class FakeHandoffCollection:
            handoffs = ["handoff-agent"]
            resources = {"text2sql_service": MagicMock()}

        def fake_build_openai_model_bundle(**kwargs):
            captured["model_bundle_kwargs"] = kwargs
            return FakeModelBundle()

        def fake_build_openai_handoffs(**kwargs):
            captured["handoff_kwargs"] = kwargs
            return FakeHandoffCollection()

        engine = engine_module.OpenAIAgentsEngine()
        engine._load_agent_context = AsyncMock(return_value=context)

        monkeypatch.setattr(engine_module, "_OPENAI_AGENTS_AVAILABLE", True)
        monkeypatch.setattr(engine_module, "Agent", FakeAgent)
        monkeypatch.setattr(engine_module, "create_workspace_backend", lambda _context: "workspace-backend")
        def fake_build_builtin_tools(workspace_backend, task_root):
            captured["task_root"] = task_root
            return ["builtin-tool", workspace_backend]

        monkeypatch.setattr(engine_module, "build_builtin_tools", fake_build_builtin_tools)
        monkeypatch.setattr(engine_module, "build_openai_model_bundle", fake_build_openai_model_bundle)
        monkeypatch.setattr(engine_module, "build_openai_handoffs", fake_build_openai_handoffs)
        monkeypatch.setattr(engine_module.OpenAIToolAdapter, "adapt_tools", staticmethod(lambda tools: ["sdk-tool", *tools]))

        runtime = await engine.build_agent(str(openai_runtime_context["agent_dir"]), "test_unit", tools=["extra-tool"])

        assert isinstance(runtime, engine_module.OpenAIAgentRuntime)
        assert runtime.tools == ["builtin-tool", "workspace-backend", "extra-tool"]
        assert runtime.sdk_tools == ["sdk-tool", "builtin-tool", "workspace-backend", "extra-tool"]
        assert runtime.workspace == "workspace-backend"
        assert runtime.model == "sdk-model"
        assert runtime.handoffs == ["handoff-agent"]
        assert runtime.provider == "openai"
        assert captured["model_bundle_kwargs"]["agent_name"] == "test_agent"
        assert captured["handoff_kwargs"]["parent_tools"] == ["builtin-tool", "workspace-backend", "extra-tool"]
        assert captured["handoff_kwargs"]["parent_model_settings"] == {"temperature": 0.4, "max_tokens": 2048}
        assert captured["task_root"].endswith("output/.task")
        assert captured["agent_kwargs"]["name"] == "test_agent"
        assert captured["agent_kwargs"]["model"] == "sdk-model"
        assert captured["agent_kwargs"]["model_settings"] == {"temperature": 0.4, "max_tokens": 2048}
        assert captured["agent_kwargs"]["handoffs"] == ["handoff-agent"]
        assert captured["agent_kwargs"]["tools"] == ["sdk-tool", "builtin-tool", "workspace-backend", "extra-tool"]
        assert "Remember to verify results before responding." in captured["agent_kwargs"]["instructions"]
        assert id(runtime) in engine._text2sql_services

    @pytest.mark.asyncio
    async def test_close_agent_resources_releases_cached_handles(self, openai_runtime_context):
        from agent_engine.engine import openai_agents_engine as engine_module

        context = engine_module.AgentBuildContext(
            business_unit_path=str(openai_runtime_context["business_unit_dir"]),
            agent_path=str(openai_runtime_context["agent_dir"]),
            agent_name="test_agent",
            business_unit_id="test_unit",
            agent_spec={"baseinfo": {"name": "test_agent"}},
            model_config={"model_id": "gpt-4o-mini"},
            memories=[],
            skills=[],
            output_path=str(openai_runtime_context["output_dir"]),
        )

        runtime = engine_module.OpenAIAgentRuntime(
            agent=object(),
            context=context,
            session_db_path=str(openai_runtime_context["output_dir"] / ".openai_sessions.sqlite"),
            model="mock-model",
            tools=[],
            sdk_tools=[],
        )
        runtime._sessions["session-1"] = MagicMock()

        engine = engine_module.OpenAIAgentsEngine()
        fake_service = MagicMock()
        engine._session_db_paths[id(runtime)] = runtime.session_db_path
        engine._text2sql_services[id(runtime)] = fake_service

        await engine.close_agent_resources(runtime)

        fake_service.close.assert_called_once()
        assert runtime._sessions == {}
        assert id(runtime) not in engine._session_db_paths
        assert id(runtime) not in engine._text2sql_services
