"""Build OpenAI Agents SDK handoffs from the existing built-in subagent registry."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..tools.openai_tool_adapter import OpenAIToolAdapter
from .subagents.registry import build_builtin_subagents

logger = logging.getLogger(__name__)

Agent = None
_OPENAI_HANDOFFS_AVAILABLE = False
_OPENAI_HANDOFFS_IMPORT_ERROR: Optional[str] = None


def _refresh_openai_handoff_dependencies() -> bool:
    """Try importing OpenAI handoff primitives and refresh cached availability state."""
    global Agent, _OPENAI_HANDOFFS_AVAILABLE, _OPENAI_HANDOFFS_IMPORT_ERROR

    try:
        agents_module = importlib.import_module("agents")
        Agent = getattr(agents_module, "Agent")
        _OPENAI_HANDOFFS_AVAILABLE = True
        _OPENAI_HANDOFFS_IMPORT_ERROR = None
        return True
    except Exception as exc:  # pragma: no cover - depends on local environment
        Agent = None
        _OPENAI_HANDOFFS_AVAILABLE = False
        _OPENAI_HANDOFFS_IMPORT_ERROR = str(exc)
        return False


_refresh_openai_handoff_dependencies()


@dataclass
class OpenAIHandoffCollection:
    """Built handoff agents plus any resource handles they own."""

    handoffs: List[Any] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)


def check_openai_handoff_dependencies(raise_error: bool = True) -> bool:
    """Check whether OpenAI handoff dependencies are available."""
    if _OPENAI_HANDOFFS_AVAILABLE:
        return True
    if _refresh_openai_handoff_dependencies():
        logger.info("Recovered OpenAI handoff imports after runtime recheck")
        return True
    if raise_error:
        raise ImportError(
            "openai-agents is required for handoff construction. "
            f"Original import error: {_OPENAI_HANDOFFS_IMPORT_ERROR}"
        )
    return False


def build_openai_handoffs(
    *,
    parent_model: Any,
    parent_model_settings: Any = None,
    parent_tools: List[Any],
    parent_backend: Any,
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
    registry: Any = None,
) -> OpenAIHandoffCollection:
    """Build OpenAI SDK handoffs from the legacy built-in subagent registry."""
    check_openai_handoff_dependencies(raise_error=True)

    collection = build_builtin_subagents(
        parent_model=parent_model,
        parent_tools=parent_tools,
        parent_backend=parent_backend,
        business_unit_path=business_unit_path,
        asset_bundles=asset_bundles,
        registry=registry,
    )

    handoffs: List[Any] = []
    for definition in collection.subagents:
        name = str(definition.get("name") or "").strip()
        if not name:
            continue

        description = str(definition.get("description") or "").strip() or None
        system_prompt = str(definition.get("system_prompt") or definition.get("description") or "").strip()
        raw_tools = definition.get("tools") or []
        sdk_tools = _ensure_sdk_tools(raw_tools)
        model = definition.get("model") or parent_model
        model_settings = definition.get("model_settings") or parent_model_settings

        agent_kwargs: Dict[str, Any] = {
            "name": name,
            "instructions": system_prompt,
            "model": model,
        }
        if description:
            agent_kwargs["handoff_description"] = description
        if sdk_tools:
            agent_kwargs["tools"] = sdk_tools
        if model_settings is not None:
            agent_kwargs["model_settings"] = model_settings

        handoffs.append(Agent(**agent_kwargs))

    logger.info("Built %d OpenAI handoff agent(s)", len(handoffs))
    return OpenAIHandoffCollection(handoffs=handoffs, resources=dict(collection.resources))


def _ensure_sdk_tools(tools: List[Any]) -> List[Any]:
    """Adapt LangChain-style tools into SDK tools when required."""
    if not tools:
        return []

    needs_adaptation = any(
        hasattr(tool, "_run") or hasattr(tool, "_arun") or getattr(tool, "args_schema", None) is not None
        for tool in tools
    )
    if needs_adaptation:
        return OpenAIToolAdapter.adapt_tools(tools)
    return tools


__all__ = [
    "OpenAIHandoffCollection",
    "build_openai_handoffs",
    "check_openai_handoff_dependencies",
]
