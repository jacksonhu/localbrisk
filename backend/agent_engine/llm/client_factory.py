"""
LLM Client Factory

Creates LangChain LLM clients based on LLM config in AgentRuntimeConfig
"""

import logging
import os
from typing import Any, Optional, Dict

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from ..core.config import AgentRuntimeConfig, ModelReference
from ..core.exceptions import AgentConfigError

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """LLM client factory
    
    Creates LangChain LLM clients based on model configuration
    """
    
    def __init__(self):
        logger.debug("Initializing LLMClientFactory")
        # Model resolver: used to get model config from catalog
        self._model_resolver: Optional[callable] = None
    
    def set_model_resolver(self, resolver: callable):
        """Set model resolver
        
        Args:
            resolver: Function that accepts (business_unit_id, agent_name, model_name) and returns model config
        """
        logger.debug("Setting model resolver")
        self._model_resolver = resolver
    
    async def create_client(
        self,
        config: AgentRuntimeConfig,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseChatModel]:
        """Create LLM client
        
        Args:
            config: Agent runtime config
            model_config: Optional model config (if already resolved)
            
        Returns:
            LangChain BaseChatModel instance
        """
        # Getmodel reference
        model_ref = config.get_model_reference()
        if not model_ref:
            logger.warning(f"Agent {config.agent_name} has no LLM model configured")
            return None
        
        logger.info(f"Creating  LLM 客户端: agent={config.agent_name}, model_ref={model_ref.full_reference}")
        
        # 如果没有提供model config, 尝试Parse
        if model_config is None:
            logger.debug("model config未提供, starting resolution...")
            model_config = await self._resolve_model_config(
                config.business_unit_id,
                config.agent_name,
                model_ref
            )
        
        if not model_config:
            logger.error(f"Unable to resolve model config: {model_ref.full_reference}")
            raise AgentConfigError(
                message=f"Unable to resolve model config: {model_ref.full_reference}",
                details={"model_reference": model_ref.full_reference}
            )
        
        logger.debug(f"Model config: type={model_config.get('model_type')}, provider={model_config.get('endpoint_provider')}")
        
        # 根据模型类型Create客户端
        model_type = model_config.get("model_type", "endpoint")
        
        if model_type == "endpoint":
            return self._create_endpoint_client(model_config, config)
        elif model_type == "local":
            return self._create_local_client(model_config, config)
        else:
            logger.error(f"Unsupported model type: {model_type}")
            raise AgentConfigError(
                message=f"Unsupported model type: {model_type}",
                details={"model_type": model_type}
            )
    
    async def _resolve_model_config(
        self,
        business_unit_id: str,
        agent_name: str,
        model_ref: ModelReference
    ) -> Optional[Dict[str, Any]]:
        """Parse model config
        
        Args:
            business_unit_id: Business Unit ID
            agent_name: Agent name
            model_ref: model reference
            
        Returns:
            model config dict
        """
        if not self._model_resolver:
            logger.error("Model resolver not configured")
            return None
        
        try:
            logger.info(f"Resolving model config: business_unit={business_unit_id}, agent={agent_name}, model={model_ref.model_name}")
            result = await self._model_resolver(
                business_unit_id,
                agent_name,
                model_ref.model_name
            )
            if result is None:
                logger.error(f"Model not found: {model_ref.full_reference}.Please check: 1) Agent '{agent_name}' exists, 2) Model '{model_ref.model_name}' exists于该 Agent 下")
            else:
                logger.debug(f"Model config resolved: provider={result.get('endpoint_provider')}, model_id={result.get('model_id')}")
            return result
        except Exception as e:
            logger.error(f"Failed to resolve model config: {e}", exc_info=True)
            return None
    
    def _create_endpoint_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig
    ) -> BaseChatModel:
        """Create  API endpoint LLM client
        
        Args:
            model_config: model config
            runtime_config: Agent runtime config
            
        Returns:
            LangChain ChatModel 实例
        """
        provider = model_config.get("endpoint_provider", "openai")
        api_key_raw = model_config.get("api_key")
        api_key = str(api_key_raw).strip() if api_key_raw is not None else ""
        api_base_url = model_config.get("api_base_url")
        model_id = model_config.get("model_id", "gpt-4o-mini")

        # 兼容“无鉴权本地网关”场景:OpenAI SDK requires at least one of api_key/auth_token
        # If no key configured, try env var, then fall back to placeholder key.
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            api_key = "EMPTY"
            logger.warning(
                "模型未配置 api_key, 已using placeholder value 'EMPTY' 初始化客户端."
                "若目标端点需要鉴权, 请在model config中填写真实 api_key."
            )
        
        # Get LLM params from runtime_config
        llm_config = runtime_config.llm_config
        temperature = llm_config.temperature if llm_config else 0.2
        max_tokens = llm_config.max_tokens if llm_config else 40960
        
        logger.info(f"Creating  API 客户端: provider={provider}, model={model_id}, temperature={temperature}, max_tokens={max_tokens}")
        logger.debug(f"API 配置: base_url={api_base_url}, api_key={'*' * 8 + api_key[-4:] if api_key and len(api_key) > 4 else '***'}")
        
        # Use ChatOpenAI as unified interface (most APIs are OpenAI-compatible)
        # 根据不同provider调整配置
        # 注意:这里Using LangChain's `streaming=True`, to avoid passing underlying SDK `stream=True`
        # to non-streaming call path which would return AsyncStream.
        client_kwargs = {
            "model": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": True,
        }
        
        client_kwargs["api_key"] = api_key
        
        if api_base_url:
            client_kwargs["base_url"] = api_base_url
        
        # 针对特定provider的配置调整
        if provider == "claude":
            logger.debug("使用 Anthropic Claude provider")
            # Anthropic requires special handling
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
                logger.warning("langchain_anthropic not installed, using OpenAI-compatible mode")
        
        # Default使用 OpenAI 兼容接口
        logger.info(f"Creating  ChatOpenAI 客户端 (provider={provider})")
        return ChatOpenAI(**client_kwargs)
    
    def _create_local_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig
    ) -> BaseChatModel:
        """Create local model LLM client
        
        Args:
            model_config: model config
            runtime_config: Agent runtime config
            
        Returns:
            LangChain ChatModel 实例
        """
        logger.error("Local model support not yet implemented")
        # TODO: 实现本地模型支持 (如 llama.cpp, HuggingFace 等)
        raise AgentConfigError(
            message="Local model support not yet implemented",
            details={"model_type": "local"}
        )


# Global factory instance
_factory_instance: Optional[LLMClientFactory] = None


def get_llm_client_factory() -> LLMClientFactory:
    """Get 全局 LLM Client Factory实例"""
    global _factory_instance
    if _factory_instance is None:
        logger.debug("Creating global LLMClientFactory instance")
        _factory_instance = LLMClientFactory()
    return _factory_instance


async def create_llm_client_for_agent(config: AgentRuntimeConfig) -> Optional[BaseChatModel]:
    """Convenience function to create LLM client for an Agent
    
    Args:
        config: Agent runtime config
        
    Returns:
        LangChain BaseChatModel instance
    """
    factory = get_llm_client_factory()
    return await factory.create_client(config)
