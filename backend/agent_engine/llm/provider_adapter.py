"""OpenAI-compatible provider adapter for the new runtime engine."""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..core.exceptions import AgentConfigError
from .config.providers import get_provider_default_url

logger = logging.getLogger(__name__)

AsyncOpenAI = None
ModelSettings = None
OpenAIChatCompletionsModel = None
_OPENAI_PROVIDER_AVAILABLE = False
_OPENAI_PROVIDER_IMPORT_ERROR: Optional[str] = None


def _refresh_openai_provider_dependencies() -> bool:
    """Try importing provider adapter dependencies and refresh cached availability state."""
    global AsyncOpenAI, ModelSettings, OpenAIChatCompletionsModel
    global _OPENAI_PROVIDER_AVAILABLE, _OPENAI_PROVIDER_IMPORT_ERROR

    try:
        agents_module = importlib.import_module("agents")
        AsyncOpenAI = getattr(agents_module, "AsyncOpenAI")
        ModelSettings = getattr(agents_module, "ModelSettings")
        OpenAIChatCompletionsModel = getattr(agents_module, "OpenAIChatCompletionsModel")
        _OPENAI_PROVIDER_AVAILABLE = True
        _OPENAI_PROVIDER_IMPORT_ERROR = None
        return True
    except Exception as exc:  # pragma: no cover - depends on local environment
        AsyncOpenAI = None
        ModelSettings = None
        OpenAIChatCompletionsModel = None
        _OPENAI_PROVIDER_AVAILABLE = False
        _OPENAI_PROVIDER_IMPORT_ERROR = str(exc)
        return False


_refresh_openai_provider_dependencies()


@dataclass
class OpenAIModelBundle:
    """Resolved provider payload consumed by the OpenAI runtime engine."""

    model: Any
    model_settings: Any
    provider: str
    model_id: str
    api_base_url: Optional[str]


def check_openai_provider_dependencies(raise_error: bool = True) -> bool:
    """Check whether provider adapter dependencies are available."""
    if _OPENAI_PROVIDER_AVAILABLE:
        return True
    if _refresh_openai_provider_dependencies():
        logger.info("Recovered OpenAI provider adapter imports after runtime recheck")
        return True
    if raise_error:
        raise ImportError(
            "openai-agents is required for the OpenAI provider adapter. "
            f"Original import error: {_OPENAI_PROVIDER_IMPORT_ERROR}"
        )
    return False


def build_openai_model_bundle(
    *,
    agent_name: str,
    agent_spec: Dict[str, Any],
    model_config: Dict[str, Any],
) -> OpenAIModelBundle:
    """Build one OpenAI-compatible model bundle from catalog config."""
    check_openai_provider_dependencies(raise_error=True)
    config = model_config or {}

    model_id = str(config.get("model_id") or config.get("model_name") or "").strip()
    if not model_id:
        raise AgentConfigError(
            message=f"Agent '{agent_name}' is missing model_id in its model config",
            field="model_id",
        )

    provider = str(config.get("endpoint_provider") or config.get("local_provider") or "openai").strip() or "openai"
    model_type = str(config.get("model_type") or "endpoint").strip() or "endpoint"
    api_base_url = str(config.get("api_base_url") or config.get("base_url") or "").strip() or None
    if api_base_url is None:
        default_base_url = get_provider_default_url(provider)
        api_base_url = default_base_url.strip() or None

    if model_type == "local" and not api_base_url:
        raise AgentConfigError(
            message=(
                f"Local model '{model_id}' for agent '{agent_name}' requires an OpenAI-compatible api_base_url"
            ),
            field="api_base_url",
            details={"provider": provider, "model_type": model_type},
        )

    api_key_raw = config.get("api_key")
    api_key = str(api_key_raw).strip() if api_key_raw is not None else ""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        api_key = "EMPTY"
        logger.warning(
            "Provider adapter for agent %s has no api_key. Falling back to placeholder 'EMPTY'.",
            agent_name,
        )

    client_kwargs: Dict[str, Any] = {"api_key": api_key}
    if api_base_url:
        client_kwargs["base_url"] = api_base_url

    llm_config = agent_spec.get("llm_config", {}) if isinstance(agent_spec, dict) else {}
    temperature = config.get("temperature", config.get("tempreture", llm_config.get("temperature")))
    max_tokens = config.get("max_tokens", llm_config.get("max_tokens"))

    logger.info(
        "Building OpenAI model bundle: agent=%s provider=%s model=%s base_url=%s",
        agent_name,
        provider,
        model_id,
        api_base_url or "<default>",
    )
    client = AsyncOpenAI(**client_kwargs)
    model = OpenAIChatCompletionsModel(model=model_id, openai_client=client)

    settings_kwargs: Dict[str, Any] = {}
    if temperature is not None:
        settings_kwargs["temperature"] = float(temperature)
    if max_tokens is not None:
        settings_kwargs["max_tokens"] = int(max_tokens)
    model_settings = ModelSettings(**settings_kwargs) if settings_kwargs and ModelSettings is not None else None

    return OpenAIModelBundle(
        model=model,
        model_settings=model_settings,
        provider=provider,
        model_id=model_id,
        api_base_url=api_base_url,
    )


__all__ = [
    "OpenAIModelBundle",
    "build_openai_model_bundle",
    "check_openai_provider_dependencies",
]
