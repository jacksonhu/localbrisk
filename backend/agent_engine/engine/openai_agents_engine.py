"""OpenAI Agents SDK runtime engine and session-aware runtime wrapper."""

from __future__ import annotations

import importlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.exceptions import AgentConfigError
from ..llm.provider_adapter import build_openai_model_bundle
from ..tools.openai_tool_adapter import OpenAIToolAdapter
from ..tools.registry import build_builtin_tools
from .agent_context_loader import AgentBuildContext, AssetBundleBackendConfig, SkillConfig, load_agent_context
from .handoff_registry import build_openai_handoffs
from .native_skill_registry import build_openai_skills

logger = logging.getLogger(__name__)

Agent = None
Runner = None
SQLiteSession = None
_OPENAI_AGENTS_AVAILABLE = False
_OPENAI_AGENTS_IMPORT_ERROR: Optional[str] = None
def _refresh_openai_agents_dependencies() -> bool:
    """Try importing OpenAI Agents SDK symbols and refresh cached availability state."""
    global Agent, Runner, SQLiteSession, _OPENAI_AGENTS_AVAILABLE, _OPENAI_AGENTS_IMPORT_ERROR

    try:
        agents_module = importlib.import_module("agents")
        Agent = getattr(agents_module, "Agent")
        Runner = getattr(agents_module, "Runner")
        SQLiteSession = getattr(agents_module, "SQLiteSession")
        _OPENAI_AGENTS_AVAILABLE = True
        _OPENAI_AGENTS_IMPORT_ERROR = None
        return True
    except Exception as exc:  # pragma: no cover - depends on local environment
        Agent = None
        Runner = None
        SQLiteSession = None
        _OPENAI_AGENTS_AVAILABLE = False
        _OPENAI_AGENTS_IMPORT_ERROR = str(exc)
        return False


_refresh_openai_agents_dependencies()


class OpenAIAgentRuntime:
    """Runtime wrapper that binds one SDK agent with persisted sessions."""

    def __init__(
        self,
        *,
        agent: Any,
        context: AgentBuildContext,
        session_db_path: str,
        model: Any,
        tools: List[Any],
        sdk_tools: List[Any],
        handoffs: Optional[List[Any]] = None,
        resources: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.agent = agent
        self.context = context
        self.session_db_path = session_db_path
        self.model = model
        self.tools = tools
        self.sdk_tools = sdk_tools
        self.handoffs = handoffs or []
        self.resources = resources or {}
        self.is_openai_runtime = True
        self._sessions: Dict[str, Any] = {}

        Path(self.session_db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_session(self, session_id: Optional[str]) -> Any:
        """Return a cached SQLite-backed session when a session id is provided."""
        if not session_id:
            return None
        if not _OPENAI_AGENTS_AVAILABLE or SQLiteSession is None:
            return None

        cached = self._sessions.get(session_id)
        if cached is not None:
            return cached

        try:
            session = SQLiteSession(session_id=session_id, db_path=self.session_db_path)
        except TypeError:
            session = SQLiteSession(session_id, self.session_db_path)
        self._sessions[session_id] = session
        return session

    async def run(self, input_data: Any, *, session_id: Optional[str] = None, run_config: Any = None) -> Any:
        """Run the wrapped SDK agent without streaming."""
        check_openai_agents_dependencies(raise_error=True)
        normalized_input = self._normalize_input(input_data)
        return await Runner.run(
            self.agent,
            normalized_input,
            session=self.get_session(session_id),
            run_config=run_config,
        )

    async def run_streamed(
        self,
        input_data: Any,
        *,
        session_id: Optional[str] = None,
        run_config: Any = None,
    ) -> Any:
        """Run the wrapped SDK agent with streaming events enabled."""
        check_openai_agents_dependencies(raise_error=True)
        normalized_input = self._normalize_input(input_data)
        return Runner.run_streamed(
            self.agent,
            normalized_input,
            session=self.get_session(session_id),
            run_config=run_config,
        )

    async def clear_session(self, session_id: Optional[str]) -> bool:
        """Clear one persisted SDK session when the session backend supports it."""
        if not session_id:
            return False

        session = self.get_session(session_id)
        if session is None:
            return False

        for method_name in ("clear_session", "delete_session", "delete_thread", "adelete_thread"):
            clear_method = getattr(session, method_name, None)
            if not callable(clear_method):
                continue
            result = clear_method() if method_name in {"clear_session", "delete_session"} else clear_method(session_id)
            if hasattr(result, "__await__"):
                await result
            self._sessions.pop(session_id, None)
            logger.info("Cleared OpenAI runtime session: agent=%s session_id=%s", self.context.agent_name, session_id)
            return True

        logger.warning("Session backend does not support clearing session '%s' for agent %s", session_id, self.context.agent_name)
        return False

    def close(self) -> None:
        """Release cached local session handles."""
        for session_id, session in list(self._sessions.items()):
            close_method = getattr(session, "close", None)
            if not callable(close_method):
                continue
            try:
                close_method()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to close cached OpenAI runtime session %s: %s", session_id, exc)
        self._sessions.clear()

    @staticmethod
    def _normalize_input(input_data: Any) -> Any:
        """Normalize legacy message payloads into SDK-compatible input text."""
        if not isinstance(input_data, dict):
            return input_data

        messages = input_data.get("messages")
        if not isinstance(messages, list):
            return input_data

        text_parts: List[str] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "").strip().lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                text_parts.append(content.strip())
        return "\n\n".join(text_parts) if text_parts else input_data


class OpenAIAgentsEngine:
    """Build OpenAI Agents SDK runtime instances from agent directories."""

    def __init__(self) -> None:
        logger.info("Initializing OpenAIAgentsEngine")
        self._model_resolver: Optional[callable] = None
        self._session_db_paths: Dict[int, str] = {}
        self._text2sql_services: Dict[int, Any] = {}

    def set_model_resolver(self, resolver: callable) -> None:
        """Configure an async model resolver used during runtime build."""
        self._model_resolver = resolver
        logger.debug("Model resolver configured for OpenAI runtime")

    async def build_agent(
        self,
        agent_path: str,
        business_unit_id: str,
        tools: Optional[List[Any]] = None,
    ) -> OpenAIAgentRuntime:
        """Build and return one session-aware OpenAI Agents runtime."""
        check_openai_agents_dependencies(raise_error=True)
        logger.info("Building OpenAI agent runtime from %s for business unit %s", agent_path, business_unit_id)

        context = await self._load_agent_context(agent_path, business_unit_id)
        if not context.model_config:
            raise AgentConfigError(
                message=(
                    f"Agent '{context.agent_name}' has no OpenAI-compatible model configured. "
                    "Please set 'llm_config.llm_model' in agent_spec.yaml and provide a matching "
                    "model definition file under the models/ directory."
                ),
                config_path=str(Path(agent_path) / "agent_spec.yaml"),
                field="llm_config.llm_model",
            )

        model_bundle = build_openai_model_bundle(
            agent_name=context.agent_name,
            agent_spec=context.agent_spec,
            model_config=context.model_config,
        )
        instructions = self._build_instructions(context)

        task_root = Path(context.output_path) / ".task"
        task_root.mkdir(parents=True, exist_ok=True)
        runtime_tools = build_builtin_tools(
            agent_path=context.agent_path,
            task_root=str(task_root),
            business_unit_path=context.business_unit_path,
            asset_bundles=context.asset_bundles or [],
        ) + (tools or [])
        sdk_runtime_tools = OpenAIToolAdapter.adapt_tools(runtime_tools)
        skill_collection = build_openai_skills(
            agent_cls=Agent,
            parent_model=model_bundle.model,
            parent_model_settings=model_bundle.model_settings,
            parent_tools=sdk_runtime_tools,
            skills=context.skills,
        )
        sdk_tools = sdk_runtime_tools + skill_collection.tools
        handoff_collection = build_openai_handoffs(
            parent_model=model_bundle.model,
            parent_model_settings=model_bundle.model_settings,
            parent_tools=runtime_tools,
            business_unit_path=context.business_unit_path,
            asset_bundles=context.asset_bundles or [],
        )

        agent_kwargs: Dict[str, Any] = {
            "name": context.agent_name,
            "instructions": instructions,
            "model": model_bundle.model,
        }
        if sdk_tools:
            agent_kwargs["tools"] = sdk_tools
        if model_bundle.model_settings is not None:
            agent_kwargs["model_settings"] = model_bundle.model_settings
        if handoff_collection.handoffs:
            agent_kwargs["handoffs"] = handoff_collection.handoffs

        sdk_agent = Agent(**agent_kwargs)
        session_db_path = str(Path(context.output_path) / ".openai_sessions.sqlite")
        runtime = OpenAIAgentRuntime(
            agent=sdk_agent,
            context=context,
            session_db_path=session_db_path,
            model=model_bundle.model,
            tools=runtime_tools,
            sdk_tools=sdk_tools,
            handoffs=handoff_collection.handoffs,
            resources=handoff_collection.resources,
        )
        runtime.model_settings = model_bundle.model_settings
        runtime.provider = model_bundle.provider
        runtime.model_id = model_bundle.model_id
        runtime.api_base_url = model_bundle.api_base_url
        self._session_db_paths[id(runtime)] = session_db_path

        text2sql_service = handoff_collection.resources.get("text2sql_service")
        if text2sql_service is not None:
            self._text2sql_services[id(runtime)] = text2sql_service

        logger.info(
            "OpenAI agent runtime built successfully: agent=%s provider=%s model=%s tools=%s skill_tools=%s handoffs=%s session_db=%s",
            context.agent_name,
            model_bundle.provider,
            model_bundle.model_id,
            len(sdk_runtime_tools),
            len(skill_collection.tools),
            len(handoff_collection.handoffs),
            session_db_path,
        )
        return runtime

    async def close_agent_resources(self, agent: Any) -> None:
        """Release cached runtime resources owned by a built agent wrapper."""
        runtime_id = id(agent)
        self._session_db_paths.pop(runtime_id, None)

        text2sql_service = self._text2sql_services.pop(runtime_id, None)
        if text2sql_service is not None:
            try:
                text2sql_service.close()
                logger.info("Closed Text2SQL service for OpenAI runtime %s", runtime_id)
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to close Text2SQL service for OpenAI runtime %s: %s", runtime_id, exc)

        close = getattr(agent, "close", None)
        if callable(close):
            close()

    async def _load_agent_context(self, agent_path: str, business_unit_id: str) -> AgentBuildContext:
        """Load the framework-neutral build context for one agent."""
        return await load_agent_context(agent_path, business_unit_id, self._model_resolver)

    def _build_instructions(self, context: AgentBuildContext) -> str:
        """Assemble the SDK instructions string from the current agent context.

        Composition order:
          1. Rendered ``instruction`` template from agent_spec.yaml (the user
             authors this freely; placeholders are substituted at runtime).
          2. Optional asset-bundle hint so the agent knows which data bundles
             are mounted under the business unit.
          3. Memory block built from every markdown file under ``memories/``.
          4. A trailing guard rail reminding the agent to stay grounded.
        """
        parts: List[str] = []

        rendered_instruction = self._render_instruction(context)
        if rendered_instruction:
            parts.append(rendered_instruction)

        asset_bundle_prompt = self._build_asset_bundle_prompt(context.asset_bundles or [])
        if asset_bundle_prompt:
            parts.append(asset_bundle_prompt)

        memory_block = self._build_memory_block(context)
        if memory_block:
            parts.append(memory_block)

        parts.append(
            "When you use tools, keep outputs grounded in tool results and do not invent "
            "file contents, SQL results, or command outcomes."
        )
        return "\n\n".join(part for part in parts if isinstance(part, str) and part.strip())

    def _render_instruction(self, context: AgentBuildContext) -> str:
        """Render the instruction template, substituting runtime placeholders.

        Supported placeholders:
        - ``{{agent_name}}`` -> the agent's logical name.
        - ``{{agent_path}}`` -> the agent's on-disk directory.
        - ``{{now}}``        -> the current local timestamp.

        Falls back to a minimal default when the spec has no instruction set.
        """
        agent_spec = context.agent_spec if isinstance(context.agent_spec, dict) else {}
        template = agent_spec.get("instruction")
        if not isinstance(template, str) or not template.strip():
            template = (
                "You are agent {{agent_name}}\n"
                "Working directory: {{agent_path}}\n"
                "Current date: {{now}}"
            )

        replacements = {
            "{{agent_name}}": context.agent_name,
            "{{agent_path}}": f"{context.agent_path}/",
            "{{now}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        rendered = template
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)
        return rendered.strip()

    def _build_memory_block(self, context: AgentBuildContext) -> str:
        """Render loaded memory markdown files into one instructions block."""
        sections: List[str] = []
        for mount_path in context.memories:
            file_path = Path(context.agent_path) / mount_path.lstrip("/")
            content = self._read_text_file(file_path)
            if not content:
                continue
            sections.append(f"### Memory: {file_path.name}\n{content}")
        if not sections:
            return ""
        return "## Memory\n\n" + "\n\n".join(sections)

    @staticmethod
    def _read_text_file(path: Path) -> str:
        """Read one UTF-8 text file and return stripped content."""
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning("Instruction file not found while building OpenAI runtime: %s", path)
            return ""
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to read instruction file %s: %s", path, exc)
            return ""

    @staticmethod
    def _build_asset_bundle_prompt(asset_bundles: List[AssetBundleBackendConfig]) -> str:
        """Build a lightweight asset bundle hint for the runtime system prompt."""
        if not asset_bundles:
            return ""

        lines = [
            "## Asset Bundles",
            "The current business unit has data bundles available for analysis.",
            "Prefer bundle-aware analysis tools or handoffs when the user asks about business data.",
        ]
        for bundle in asset_bundles:
            lines.append(f"- `{bundle.bundle_name}` ({bundle.bundle_type})")
        return "\n".join(lines)


def check_openai_agents_dependencies(raise_error: bool = True) -> bool:
    """Check whether OpenAI Agents SDK runtime dependencies are available."""
    if _OPENAI_AGENTS_AVAILABLE:
        return True

    if _refresh_openai_agents_dependencies():
        logger.info("Recovered OpenAI Agents SDK import after runtime recheck")
        return True

    if raise_error:
        raise ImportError(
            "openai-agents is required for the OpenAI runtime engine. "
            f"Original import error: {_OPENAI_AGENTS_IMPORT_ERROR}"
        )
    return False


_engine_instance: Optional[OpenAIAgentsEngine] = None


def get_openai_agents_engine() -> OpenAIAgentsEngine:
    """Return the shared OpenAI Agents engine instance."""
    global _engine_instance
    if _engine_instance is None:
        logger.debug("Creating global OpenAIAgentsEngine instance")
        _engine_instance = OpenAIAgentsEngine()
    return _engine_instance


__all__ = [
    "OpenAIAgentRuntime",
    "OpenAIAgentsEngine",
    "AgentBuildContext",
    "AssetBundleBackendConfig",
    "SkillConfig",
    "check_openai_agents_dependencies",
    "get_openai_agents_engine",
]
