"""
LLM 客户端工厂

负责根据 AgentRuntimeConfig 中的 LLM 配置创建对应的 LangChain LLM 客户端
"""

import logging
from typing import Any, Optional, Dict

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from ..core.config import AgentRuntimeConfig, ModelReference
from ..core.exceptions import AgentConfigError

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """LLM 客户端工厂
    
    根据模型配置创建对应的 LangChain LLM 客户端
    """
    
    def __init__(self):
        logger.debug("初始化 LLMClientFactory")
        # 模型解析器：用于从 catalog 获取模型配置
        self._model_resolver: Optional[callable] = None
    
    def set_model_resolver(self, resolver: callable):
        """设置模型解析器
        
        Args:
            resolver: 接收 (business_unit_id, agent_name, model_name) 返回模型配置的函数
        """
        logger.debug("设置模型解析器")
        self._model_resolver = resolver
    
    async def create_client(
        self,
        config: AgentRuntimeConfig,
        model_config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseChatModel]:
        """创建 LLM 客户端
        
        Args:
            config: Agent 运行时配置
            model_config: 可选的模型配置（如果已解析）
            
        Returns:
            LangChain BaseChatModel 实例
        """
        # 获取模型引用
        model_ref = config.get_model_reference()
        if not model_ref:
            logger.warning(f"Agent {config.agent_name} 未配置 LLM 模型")
            return None
        
        logger.info(f"创建 LLM 客户端: agent={config.agent_name}, model_ref={model_ref.full_reference}")
        
        # 如果没有提供模型配置，尝试解析
        if model_config is None:
            logger.debug("模型配置未提供，开始解析...")
            model_config = await self._resolve_model_config(
                config.business_unit_id,
                config.agent_name,
                model_ref
            )
        
        if not model_config:
            logger.error(f"无法解析模型配置: {model_ref.full_reference}")
            raise AgentConfigError(
                message=f"无法解析模型配置: {model_ref.full_reference}",
                details={"model_reference": model_ref.full_reference}
            )
        
        logger.debug(f"模型配置: type={model_config.get('model_type')}, provider={model_config.get('endpoint_provider')}")
        
        # 根据模型类型创建客户端
        model_type = model_config.get("model_type", "endpoint")
        
        if model_type == "endpoint":
            return self._create_endpoint_client(model_config, config)
        elif model_type == "local":
            return self._create_local_client(model_config, config)
        else:
            logger.error(f"不支持的模型类型: {model_type}")
            raise AgentConfigError(
                message=f"不支持的模型类型: {model_type}",
                details={"model_type": model_type}
            )
    
    async def _resolve_model_config(
        self,
        business_unit_id: str,
        agent_name: str,
        model_ref: ModelReference
    ) -> Optional[Dict[str, Any]]:
        """解析模型配置
        
        Args:
            business_unit_id: Business Unit ID
            agent_name: Agent 名称
            model_ref: 模型引用
            
        Returns:
            模型配置字典
        """
        if not self._model_resolver:
            logger.error("模型解析器未配置")
            return None
        
        try:
            logger.info(f"解析模型配置: business_unit={business_unit_id}, agent={agent_name}, model={model_ref.model_name}")
            result = await self._model_resolver(
                business_unit_id,
                agent_name,
                model_ref.model_name
            )
            if result is None:
                logger.error(f"模型未找到: {model_ref.full_reference}。请检查: 1) Agent '{agent_name}' 是否存在, 2) Model '{model_ref.model_name}' 是否存在于该 Agent 下")
            else:
                logger.debug(f"模型配置解析成功: provider={result.get('endpoint_provider')}, model_id={result.get('model_id')}")
            return result
        except Exception as e:
            logger.error(f"解析模型配置失败: {e}", exc_info=True)
            return None
    
    def _create_endpoint_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig
    ) -> BaseChatModel:
        """创建 API 端点 LLM 客户端
        
        Args:
            model_config: 模型配置
            runtime_config: Agent 运行时配置
            
        Returns:
            LangChain ChatModel 实例
        """
        provider = model_config.get("endpoint_provider", "openai")
        api_key = model_config.get("api_key")
        api_base_url = model_config.get("api_base_url")
        model_id = model_config.get("model_id", "gpt-4o-mini")
        
        # 从 runtime_config 获取 LLM 参数
        llm_config = runtime_config.llm_config
        temperature = llm_config.temperature if llm_config else 0.2
        max_tokens = llm_config.max_tokens if llm_config else 4096
        
        logger.info(f"创建 API 客户端: provider={provider}, model={model_id}, temperature={temperature}, max_tokens={max_tokens}")
        logger.debug(f"API 配置: base_url={api_base_url}, api_key={'*' * 8 + api_key[-4:] if api_key and len(api_key) > 4 else '***'}")
        
        # 使用 ChatOpenAI 作为统一接口（大多数 API 兼容 OpenAI 格式）
        # 根据不同提供商调整配置
        client_kwargs = {
            "model": model_id,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": True,
        }
        
        if api_key:
            client_kwargs["api_key"] = api_key
        
        if api_base_url:
            client_kwargs["base_url"] = api_base_url
        
        # 针对特定提供商的配置调整
        if provider == "claude":
            logger.debug("使用 Anthropic Claude 提供商")
            # Anthropic 需要特殊处理
            try:
                from langchain_anthropic import ChatAnthropic
                logger.info("创建 ChatAnthropic 客户端")
                return ChatAnthropic(
                    model=model_id,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except ImportError:
                logger.warning("langchain_anthropic 未安装，使用 OpenAI 兼容模式")
        
        # 默认使用 OpenAI 兼容接口
        logger.info(f"创建 ChatOpenAI 客户端 (provider={provider})")
        return ChatOpenAI(**client_kwargs)
    
    def _create_local_client(
        self,
        model_config: Dict[str, Any],
        runtime_config: AgentRuntimeConfig
    ) -> BaseChatModel:
        """创建本地模型 LLM 客户端
        
        Args:
            model_config: 模型配置
            runtime_config: Agent 运行时配置
            
        Returns:
            LangChain ChatModel 实例
        """
        logger.error("本地模型支持尚未实现")
        # TODO: 实现本地模型支持（如 llama.cpp, HuggingFace 等）
        raise AgentConfigError(
            message="本地模型支持尚未实现",
            details={"model_type": "local"}
        )


# 全局工厂实例
_factory_instance: Optional[LLMClientFactory] = None


def get_llm_client_factory() -> LLMClientFactory:
    """获取全局 LLM 客户端工厂实例"""
    global _factory_instance
    if _factory_instance is None:
        logger.debug("创建全局 LLMClientFactory 实例")
        _factory_instance = LLMClientFactory()
    return _factory_instance


async def create_llm_client_for_agent(config: AgentRuntimeConfig) -> Optional[BaseChatModel]:
    """为 Agent 创建 LLM 客户端的便捷函数
    
    Args:
        config: Agent 运行时配置
        
    Returns:
        LangChain BaseChatModel 实例
    """
    factory = get_llm_client_factory()
    return await factory.create_client(config)
