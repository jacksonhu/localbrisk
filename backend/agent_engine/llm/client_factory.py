"""Factory for creating LangChain chat clients from agent model configuration."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..core.config import AgentRuntimeConfig, ModelReference
from ..core.exceptions import AgentConfigError, LocalModelNotImplementedError

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Create LangChain chat clients from runtime model configuration."""

    def __init__(self):
        logger.debug("Initializing LLMClientFactory")
        self._model_resolver: Optional[callable] = None

    def set_model_resolver(self, resolver: callable):
        """Set the async model resolver used to load catalog model config."""
        logger.debug("Setting model resolver")
        self._model_resolver = resolver

    async def create_client(
        self,
        config: AgentRuntimeConfig,
        model_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[BaseChatModel]:
        """Create an LLM client for the provided runtime config."""
        model_ref = config.get_model_reference()
        if not model_ref:
            logger.warning("Agent %s has no configured model reference", config.agent_name)
            return None

        logger.info(
            "Creating LLM client for agent=%s model_ref=%s",
            config.agent_name,
            model_ref.full_reference,
        )

        if model_config is None:
            logger.debug("Resolving model configuration from catalog")
            model_config = await self._resolve_model_config(
                config.business_unit_id,
                config.agent_name,
                model_ref,
            )

        if not model_config:
            logger.error("Unable to resolve model config: %s", model_ref.full_reference)
            raise AgentConfigError(
                message=f"Unable to resolve model config: {model_ref.full_reference}",
                details={"model_reference": model_ref.full_reference},
            )

        model_type = model_config.get("model_type", "endpoint")
        provider = model_config.get("endpoint_provider") or model_config.get("local_provider")
        logger.debug("Resolved model config: model_type=%s provider=%s", model_type, provider)

        if model_type == "endpoint":
            return self._create_endpoint_client(model_config, config)
        if model_type == "local":
            return self._create_local_client(model_config, config)

        logger.error("Unsupported model type: %s", model_type)
        raise AgentConfigError(
            message=f"Unsupported model type: {model_type}",
            details={"model_type": model_type},
        )

    async def _resolve_model_config(
        self,
        business_unit_id: str,
        agent_name: str,
        model_ref: ModelReference,
    ) -> Optional[Dict[str, Any]]:
        """Resolve model configuration from the catalog via the configured resolver."""
        if not self._model_resolver:
            logger.error("Model resolver is not configured")
            return None

        try:
            logger.info(
                "Resolving model config for business_unit=%s agent=%s model=%s",
                business_unit_id,
                agent_name,
                model_ref.model_name,
            )
            result = await self._model_resolver(
                business_unit_id,
                agent_name,
                model_ref.model_name,
            )
            if result is None:
                logger.error(
                    "Model not found for reference %s; verify the agent and model configuration",
                    model_ref.full_reference,
                )
            else:
                logger.debug(
                    "Model config resolved: provider=%s model_id=%s",
                    result.get("endpoint_provider") or result.get("local_provider"),
                    result.get("model_id"),
                )
            return result
        except Exception as exc:
            logger.error("Failed to resolve model config: %s", exc, exc_info=True)
            return None

    def _create_endpoint_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig,
    ) -> BaseChatModel:
        """Create an endpoint-backed LangChain chat client."""
        provider = model_config.get("endpoint_provider", "openai")
        api_key_raw = model_config.get("api_key")
        api_key = str(api_key_raw).strip() if api_key_raw is not None else ""
        api_base_url = model_config.get("api_base_url")
        model_id = model_config.get("model_id", "gpt-4o-mini")

        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            api_key = "EMPTY"
            logger.warning(
                "Model config has no api_key; using placeholder value 'EMPTY'. "
                "Configure a real api_key if the endpoint requires authentication."
            )

        llm_config = runtime_config.llm_config
        temperature = llm_config.temperature if llm_config else 0.2
        max_tokens = llm_config.max_tokens if llm_config else 40960

        logger.info(
            "Creating endpoint client: provider=%s model=%s temperature=%s max_tokens=%s",
            provider,
            model_id,
            temperature,
            max_tokens,
        )
        logger.debug(
            "Endpoint client config: base_url=%s api_key=%s",
            api_base_url,
            "*" * 8 + api_key[-4:] if api_key and len(api_key) > 4 else "***",
        )

        client_kwargs = {
            "model": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": True,
            "api_key": api_key,
        }
        if api_base_url:
            client_kwargs["base_url"] = api_base_url

        if provider == "claude":
            logger.debug("Using Anthropic Claude provider")
            try:
                from langchain_anthropic import ChatAnthropic

                logger.info("Creating ChatAnthropic client")
                return ChatAnthropic(
                    model=model_id,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=True,
                )
            except ImportError:
                logger.warning("langchain_anthropic is not installed; falling back to OpenAI-compatible mode")

        logger.info("Creating ChatOpenAI client for provider=%s", provider)
        return ChatOpenAI(**client_kwargs)

    def _create_local_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig,
    ) -> BaseChatModel:
        """Raise a stable placeholder error for local model runtime creation."""
        del runtime_config
        provider = model_config.get("local_provider") or model_config.get("endpoint_provider") or "local"
        model_name = model_config.get("model_id")
        logger.error(
            "Local model runtime placeholder reached: provider=%s model=%s",
            provider,
            model_name,
        )
        raise LocalModelNotImplementedError(
            provider=provider,
            model_name=model_name,
            details={"stage": "llm_client_factory"},
        )


_factory_instance: Optional[LLMClientFactory] = None



def get_llm_client_factory() -> LLMClientFactory:
    """Return the shared LLM client factory instance."""
    global _factory_instance
    if _factory_instance is None:
        logger.debug("Creating global LLMClientFactory instance")
        _factory_instance = LLMClientFactory()
    return _factory_instance


async def create_llm_client_for_agent(config: AgentRuntimeConfig) -> Optional[BaseChatModel]:
    """Convenience wrapper for creating an agent LLM client."""
    factory = get_llm_client_factory()
    return await factory.create_client(config)
