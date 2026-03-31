"""
LLM Package - Large Language Model Management Module

This module provides:
- Unified LLM provider configuration management
- Model instantiation and request debugging
- Consistent configuration data across frontend and backend
- LLM Client Factory

Note: This module is designed to be imported independently, without depending on other agent_engine submodules
"""

# Import directly from submodules to avoid circular dependencies
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
    # LLM Client Factory
    "LLMClientFactory",
    "get_llm_client_factory",
    "create_llm_client_for_agent",
]
