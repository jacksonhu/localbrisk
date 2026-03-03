"""
LLM 包 - 大语言模型管理模块

该模块提供:
- 统一的 LLM 提供商配置管理
- 模型实例化和请求调试
- 前后端一致的配置数据
- LLM 客户端工厂

注意: 此模块设计为可以独立导入，不依赖 agent_engine 的其他子模块
"""

# 直接从子模块导入，避免循环依赖
from agent_engine.llm.config.providers import (
    ProviderType,
    ModelInfo,
    ProviderConfig,
    get_endpoint_providers,
    get_local_providers,
    get_provider_models,
    get_provider_default_url,
    get_all_providers,
)
from agent_engine.llm.config.registry import ModelRegistry
from agent_engine.llm.client_factory import (
    LLMClientFactory,
    get_llm_client_factory,
    create_llm_client_for_agent,
)

__all__ = [
    "ProviderType",
    "ModelInfo", 
    "ProviderConfig",
    "ModelRegistry",
    "get_endpoint_providers",
    "get_local_providers",
    "get_provider_models",
    "get_provider_default_url",
    "get_all_providers",
    # LLM 客户端工厂
    "LLMClientFactory",
    "get_llm_client_factory",
    "create_llm_client_for_agent",
]
