"""Adapters that expose existing runtime tools to the OpenAI Agents SDK."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)

FunctionTool = None
_OPENAI_AGENTS_AVAILABLE = False
_OPENAI_AGENTS_IMPORT_ERROR: Optional[str] = None


def _refresh_openai_tool_dependencies() -> bool:
    """Try importing OpenAI tool primitives and refresh cached availability state."""
    global FunctionTool, _OPENAI_AGENTS_AVAILABLE, _OPENAI_AGENTS_IMPORT_ERROR

    try:
        agents_module = importlib.import_module("agents")
        FunctionTool = getattr(agents_module, "FunctionTool")
        _OPENAI_AGENTS_AVAILABLE = True
        _OPENAI_AGENTS_IMPORT_ERROR = None
        return True
    except Exception as exc:  # pragma: no cover - depends on local environment
        FunctionTool = None
        _OPENAI_AGENTS_AVAILABLE = False
        _OPENAI_AGENTS_IMPORT_ERROR = str(exc)
        return False


_refresh_openai_tool_dependencies()


def check_openai_agents_tools_available(raise_error: bool = True) -> bool:
    """Check whether OpenAI Agents SDK tool primitives are available."""
    if _OPENAI_AGENTS_AVAILABLE:
        return True
    if _refresh_openai_tool_dependencies():
        logger.info("Recovered OpenAI tool adapter imports after runtime recheck")
        return True
    if raise_error:
        raise ImportError(
            "openai-agents is required for OpenAI tool adaptation. "
            f"Original import error: {_OPENAI_AGENTS_IMPORT_ERROR}"
        )
    return False


class OpenAIToolAdapter:
    """Convert existing runtime tools into OpenAI Agents SDK tools."""

    @classmethod
    def adapt_tools(cls, tools: Optional[List[Any]]) -> List[Any]:
        """Adapt a list of runtime tools into SDK FunctionTools."""
        if not tools:
            return []
        return [cls.adapt_tool(tool) for tool in tools]

    @classmethod
    def adapt_tool(cls, tool: Any) -> Any:
        """Adapt a single runtime tool into one SDK FunctionTool."""
        check_openai_agents_tools_available(raise_error=True)

        tool_name = str(getattr(tool, "name", "") or "").strip()
        if not tool_name:
            raise ValueError("Tool name must not be empty")

        description = str(getattr(tool, "description", "") or f"Execute tool '{tool_name}'.")
        args_model = cls._get_args_model(tool)
        params_json_schema = args_model.model_json_schema() if args_model else cls._build_default_schema()

        async def on_invoke_tool(_context: Any, raw_args: str) -> str:
            parsed_kwargs = cls._parse_arguments(args_model, raw_args)
            result = await cls._invoke_tool(tool, parsed_kwargs)
            return cls._normalize_result(result)

        return FunctionTool(
            name=tool_name,
            description=description,
            params_json_schema=params_json_schema,
            on_invoke_tool=on_invoke_tool,
        )

    @staticmethod
    def _get_args_model(tool: Any) -> Optional[Type[BaseModel]]:
        """Return the Pydantic args schema when the tool exposes one."""
        schema = getattr(tool, "args_schema", None)
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema
        return None

    @staticmethod
    def _build_default_schema() -> Dict[str, Any]:
        """Return an empty JSON schema for parameterless tools."""
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    @staticmethod
    def _parse_arguments(args_model: Optional[Type[BaseModel]], raw_args: str) -> Dict[str, Any]:
        """Parse the raw JSON tool arguments into keyword arguments."""
        payload = (raw_args or "{}").strip() or "{}"
        if args_model is not None:
            parsed = args_model.model_validate_json(payload)
            return parsed.model_dump(exclude_none=True)

        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Tool arguments must decode into a JSON object")
        return data

    @classmethod
    async def _invoke_tool(cls, tool: Any, kwargs: Dict[str, Any]) -> Any:
        """Invoke a tool using its async or sync runtime hooks."""
        arun = getattr(tool, "_arun", None)
        if callable(arun):
            result = arun(**kwargs) if kwargs else arun()
            if asyncio.iscoroutine(result):
                return await result
            return result

        run = getattr(tool, "_run", None)
        if callable(run):
            return await asyncio.to_thread(run, **kwargs)

        invoke = getattr(tool, "invoke", None)
        if callable(invoke):
            return await asyncio.to_thread(invoke, kwargs)

        raise TypeError(f"Tool '{getattr(tool, 'name', type(tool).__name__)}' is not invokable")

    @staticmethod
    def _normalize_result(result: Any) -> str:
        """Normalize tool output into a string result for the SDK."""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False)
        return str(result)


__all__ = [
    "OpenAIToolAdapter",
    "check_openai_agents_tools_available",
]
