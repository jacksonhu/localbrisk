"""DeepAgents engine implementation and orchestration."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .deepagents_backend import create_backend as create_deepagents_backend
from .deepagents_context import (
    AgentBuildContext,
    AssetBundleBackendConfig,
    SkillConfig,
    load_active_model,
    load_agent_context,
    load_asset_bundles,
    load_memories,
    load_single_bundle_config,
    load_skills,
    load_volumes_config,
)
from .deepagents_resources import AgentResourceRegistry
from .subagents import create_builtin_subagents

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

_LANGCHAIN_AVAILABLE = False
_LANGGRAPH_AVAILABLE = False
_DEEPAGENTS_AVAILABLE = False
_LANGCHAIN_IMPORT_ERROR: Optional[str] = None
_LANGGRAPH_IMPORT_ERROR: Optional[str] = None
_DEEPAGENTS_IMPORT_ERROR: Optional[str] = None

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.tools import BaseTool

    _LANGCHAIN_AVAILABLE = True
except ImportError as exc:
    BaseChatModel = None
    BaseTool = None
    _LANGCHAIN_IMPORT_ERROR = str(exc)

try:
    from langgraph.cache.memory import InMemoryCache
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    _LANGGRAPH_AVAILABLE = True
except ImportError as exc:
    AsyncSqliteSaver = None
    InMemorySaver = None
    InMemoryCache = None
    _LANGGRAPH_IMPORT_ERROR = str(exc)

try:
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend, FilesystemBackend, LocalShellBackend
    from langgraph.graph.state import CompiledStateGraph

    _DEEPAGENTS_AVAILABLE = True
except ImportError as exc:
    create_deep_agent = None
    FilesystemBackend = None
    LocalShellBackend = None
    CompositeBackend = None
    CompiledStateGraph = None
    _DEEPAGENTS_IMPORT_ERROR = str(exc)


def get_python_info() -> Dict[str, Any]:
    """Return a compact description of the current Python environment."""
    return {
        "executable": sys.executable,
        "version": sys.version,
        "prefix": sys.prefix,
        "path": sys.path[:5],
    }


def check_dependencies(raise_error: bool = True) -> bool:
    """Check whether DeepAgents runtime dependencies are available."""
    missing: List[str] = []
    errors: List[str] = []

    if not _LANGCHAIN_AVAILABLE:
        missing.append("langchain-core")
        if _LANGCHAIN_IMPORT_ERROR:
            errors.append(f"langchain-core: {_LANGCHAIN_IMPORT_ERROR}")
    if not _LANGGRAPH_AVAILABLE:
        missing.append("langgraph")
        if _LANGGRAPH_IMPORT_ERROR:
            errors.append(f"langgraph: {_LANGGRAPH_IMPORT_ERROR}")
    if not _DEEPAGENTS_AVAILABLE:
        missing.append("deepagents")
        if _DEEPAGENTS_IMPORT_ERROR:
            errors.append(f"deepagents: {_DEEPAGENTS_IMPORT_ERROR}")

    if missing and raise_error:
        python_info = get_python_info()
        raise ImportError(
            "Missing required dependencies: "
            f"{', '.join(missing)}.\n"
            f"Import errors: {'; '.join(errors)}\n"
            f"Current Python: {python_info['executable']}\n"
            f"Please ensure you are using the correct virtual environment, or run: pip install {' '.join(missing)}"
        )
    return len(missing) == 0


def log_dependency_status() -> None:
    """Log runtime dependency status at module import time."""
    python_info = get_python_info()
    logger.info("Python environment: %s", python_info["executable"])
    logger.info("Python version: %s", python_info["version"].split()[0])
    logger.info("langchain-core available: %s", _LANGCHAIN_AVAILABLE)
    logger.info("langgraph available: %s", _LANGGRAPH_AVAILABLE)
    logger.info("deepagents available: %s", _DEEPAGENTS_AVAILABLE)
    if _LANGCHAIN_IMPORT_ERROR:
        logger.warning("langchain-core import error: %s", _LANGCHAIN_IMPORT_ERROR)
    if _LANGGRAPH_IMPORT_ERROR:
        logger.warning("langgraph import error: %s", _LANGGRAPH_IMPORT_ERROR)
    if _DEEPAGENTS_IMPORT_ERROR:
        logger.warning("deepagents import error: %s", _DEEPAGENTS_IMPORT_ERROR)


log_dependency_status()


class DeepAgentsEngine:
    """Build DeepAgents runtime instances from agent directories."""

    def __init__(self):
        logger.info("Initializing DeepAgentsEngine")
        self._llm_factory = None
        self._model_resolver: Optional[callable] = None
        self._resource_registry = AgentResourceRegistry()
        self._checkpointer_contexts = self._resource_registry.checkpointer_contexts
        self._text2sql_services = self._resource_registry.text2sql_services

    def _ensure_llm_factory(self):
        """Return the shared LLM client factory."""
        if self._llm_factory is None:
            if not _LANGCHAIN_AVAILABLE:
                raise ImportError("langchain-core required: pip install langchain-core")
            from ..llm.client_factory import get_llm_client_factory

            self._llm_factory = get_llm_client_factory()
        return self._llm_factory

    def set_model_resolver(self, resolver: callable):
        """Configure an async model resolver used during agent build."""
        self._model_resolver = resolver
        if self._llm_factory:
            self._llm_factory.set_model_resolver(resolver)
        logger.debug("Model resolver configured")

    async def build_agent(
        self,
        agent_path: str,
        business_unit_id: str,
        tools: Optional[List] = None,
        debug: bool = False,
    ):
        """Build and return a compiled deep agent."""
        check_dependencies(raise_error=True)
        logger.info("Building agent from %s for business unit %s", agent_path, business_unit_id)

        context = await self._load_agent_context(agent_path, business_unit_id)

        # Fail fast when no LLM model is configured
        if not context.model_config:
            from ..core.exceptions import AgentConfigError

            raise AgentConfigError(
                message=(
                    f"Agent '{context.agent_name}' has no LLM model configured. "
                    "Please set 'active_model' or 'llm_config.llm_model' in agent_spec.yaml "
                    "and provide the corresponding model definition file under the models/ directory."
                ),
                config_path=str(Path(agent_path) / "agent_spec.yaml"),
                field="active_model",
            )

        llm_client = await self._create_llm_client(context)

        backend = self._create_backend(context)

        from agent_engine.tools import get_builtin_tools

        task_root = str(Path(context.agent_path) / ".task")
        Path(task_root).mkdir(parents=True, exist_ok=True)
        builtin_tools = get_builtin_tools(backend=backend, task_root=task_root)
        all_tools = builtin_tools + (tools if tools else [])

        checkpoint_root = str(Path(context.agent_path) / ".checkpoints")
        Path(checkpoint_root).mkdir(parents=True, exist_ok=True)
        checkpoint_db = str(Path(checkpoint_root) / "checkpoints.sqlite")
        checkpointer_cm = AsyncSqliteSaver.from_conn_string(checkpoint_db)
        await self._enter_checkpointer_context(checkpointer_cm)
        checkpointer = InMemorySaver()

        try:
            subagents, text2sql_service = create_builtin_subagents(
                parent_model=llm_client,
                parent_tools=all_tools,
                parent_backend=backend,
                business_unit_path=context.business_unit_path,
                asset_bundles=context.asset_bundles,
            )
            logger.info(
                "Creating deep agent: model=%s, skills=%s, memories=%s, subagents=%s",
                type(llm_client).__name__,
                len(context.skills),
                len(context.memories),
                len(subagents),
            )
            system_prompt=f"""
            - Your Role:{context.agent_name}
            - Working Directory: {context.agent_path}/
            - Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            - Available asset bundles: `{context.agent_path}/../../asset_bundles/`. Each bundle is defined in `bundle.yaml` and may include `tables` and `volumes` (files). User queries and bundle names may be in Chinese, English, or mixed language. Automatically identify the relevant bundle(s) and choose the best match for the user's request.
            - You must think and act in the Thought, Action, Observation format.
            """
            create_kwargs = {
                "model": llm_client,
                "tools": all_tools if all_tools else None,
                "system_prompt": system_prompt,
                "skills": ["./skills/"],
                "backend": backend,
                "memory": context.memories,
                "debug": debug,
                "checkpointer": checkpointer,
                "name": context.agent_name,
                "cache": InMemoryCache(),
                "subagents": subagents,
            }
            try:
                agent = create_deep_agent(**create_kwargs)
            except TypeError as exc:
                if "subagents" not in str(exc):
                    raise
                logger.warning("Current deepagents version does not support subagents, retrying without subagents: %s", exc)
                create_kwargs.pop("subagents", None)
                agent = create_deep_agent(**create_kwargs)
        except Exception:
            await self._exit_checkpointer_context(checkpointer_cm)
            raise

        self._resource_registry.register(agent, checkpointer_cm, text2sql_service)
        logger.info("Agent built successfully: %s", context.agent_name)
        return agent

    async def _enter_checkpointer_context(self, context_manager: Any) -> Any:
        """Enter a sync or async checkpointer context manager."""
        aenter = getattr(context_manager, "__aenter__", None)
        if callable(aenter):
            return await aenter()
        enter = getattr(context_manager, "__enter__", None)
        if callable(enter):
            return enter()
        return context_manager

    async def _exit_checkpointer_context(self, context_manager: Any) -> None:
        """Exit a sync or async checkpointer context manager."""
        aexit = getattr(context_manager, "__aexit__", None)
        if callable(aexit):
            await aexit(None, None, None)
            return
        exit_ = getattr(context_manager, "__exit__", None)
        if callable(exit_):
            exit_(None, None, None)

    async def close_agent_resources(self, agent: Any) -> None:
        """Close build-time resources tracked for a compiled agent."""
        text2sql_service = self._text2sql_services.pop(id(agent), None)
        if text2sql_service is not None:
            try:
                text2sql_service.close()
                logger.info("Closed Text2SQL service for agent %s", id(agent))
            except Exception as exc:
                logger.warning("Failed to close text2sql service: %s", exc)

        checkpointer_context = self._checkpointer_contexts.pop(id(agent), None)
        if checkpointer_context is None:
            return
        try:
            await self._exit_checkpointer_context(checkpointer_context)
        except Exception as exc:
            logger.warning("Failed to close checkpointer: %s", exc)

    async def _load_agent_context(self, agent_path: str, business_unit_id: str) -> AgentBuildContext:
        """Load the full build context for an agent."""
        return await load_agent_context(agent_path, business_unit_id, self._model_resolver)

    async def _load_active_model(
        self,
        agent_path: Path,
        agent_spec: Dict[str, Any],
        business_unit_id: str,
        agent_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Load active model config for an agent."""
        return await load_active_model(agent_path, agent_spec, business_unit_id, agent_name, self._model_resolver)

    def _load_memories(self, agent_path: Path) -> List[str]:
        """Load enabled memories for an agent."""
        return load_memories(agent_path)

    def _load_skills(self, agent_path: Path) -> List[SkillConfig]:
        """Load skills for an agent."""
        return load_skills(agent_path)

    async def _create_llm_client(self, context: AgentBuildContext):
        """Create the LLM client used by the compiled agent."""
        if not context.model_config:
            logger.warning("Agent %s has no model configured", context.agent_name)
            return None

        from ..core.config import AgentRuntimeConfig, LLMRuntimeConfig

        llm_runtime_config = LLMRuntimeConfig.from_agent_llm_config(context.agent_spec.get("llm_config", {}))
        model_temperature = context.model_config.get("temperature") or context.model_config.get("tempreture")
        if model_temperature is not None:
            llm_runtime_config.temperature = float(model_temperature)

        runtime_config = AgentRuntimeConfig(
            agent_name=context.agent_name,
            business_unit_id=context.business_unit_id,
            agent_path=context.agent_path,
            llm_config=llm_runtime_config,
        )
        llm_factory = self._ensure_llm_factory()
        if self._model_resolver:
            llm_factory.set_model_resolver(self._model_resolver)
        return await llm_factory.create_client(runtime_config, context.model_config)

    def _create_backend(self, context: AgentBuildContext):
        """Create the runtime backend used by DeepAgents."""
        return create_deepagents_backend(context, FilesystemBackend, LocalShellBackend, CompositeBackend)

    def _load_asset_bundles(self, business_unit_path: Path, business_unit_id: str) -> List[AssetBundleBackendConfig]:
        """Load backend bundle config for all asset bundles."""
        return load_asset_bundles(business_unit_path, business_unit_id)

    def _load_single_bundle_config(self, bundle_path: Path, business_unit_id: str) -> Optional[AssetBundleBackendConfig]:
        """Load backend bundle config for a single asset bundle."""
        return load_single_bundle_config(bundle_path, business_unit_id)

    def _load_volumes_config(self, volumes_dir: Path) -> List[Dict[str, Any]]:
        """Load local volume configuration files."""
        return load_volumes_config(volumes_dir)


_engine_instance: Optional[DeepAgentsEngine] = None


def get_deepagents_engine() -> DeepAgentsEngine:
    """Return the shared DeepAgents engine instance."""
    global _engine_instance
    if _engine_instance is None:
        logger.debug("Creating global DeepAgentsEngine instance")
        _engine_instance = DeepAgentsEngine()
    return _engine_instance


__all__ = [
    "DeepAgentsEngine",
    "AgentBuildContext",
    "AssetBundleBackendConfig",
    "SkillConfig",
    "get_deepagents_engine",
    "check_dependencies",
    "get_python_info",
    "log_dependency_status",
]
