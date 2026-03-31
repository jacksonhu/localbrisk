"""
LLM Provider Configuration

This module contains all supported LLM provider and model configurations,
migrated from frontend to maintain frontend-backend consistency.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ProviderType(str, Enum):
    """Provider type"""
    API_ENDPOINT = "api_endpoint"  # API endpoint provider
    LOCAL_MODEL = "local_model"   # Local model provider


@dataclass
class ModelInfo:
    """Model info"""
    value: str                              # Model identifier
    label: str                              # Display name
    context_length: Optional[int] = None    # Context length
    max_tokens: Optional[int] = None        # Max output tokens
    supports_streaming: bool = True         # Supports streaming output
    supports_function_calling: bool = False # Supports function calling
    supports_vision: bool = False           # Supports vision input
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "value": self.value,
            "label": self.label,
            "context_length": self.context_length,
            "max_tokens": self.max_tokens,
            "supports_streaming": self.supports_streaming,
            "supports_function_calling": self.supports_function_calling,
            "supports_vision": self.supports_vision,
        }


@dataclass
class ProviderConfig:
    """Provider config"""
    provider_id: str                        # Provider identifier
    name: str                               # Display name
    provider_type: ProviderType             # Provider type
    default_base_url: str = ""              # Default API base URL
    models: List[ModelInfo] = field(default_factory=list)  # Supported model list
    icon: Optional[str] = None              # Icon name
    auth_type: str = "api_key"              # Auth type
    headers: Dict[str, str] = field(default_factory=dict)  # Extra headers
    rate_limit: Optional[int] = None        # Rate limit
    timeout: int = 60                       # Request timeout
    description: Optional[str] = None       # Description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "value": self.provider_id,
            "label": self.name,
            "provider_type": self.provider_type.value,
            "default_url": self.default_base_url,
            "icon": self.icon,
            "auth_type": self.auth_type,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "description": self.description,
        }


# ============================================================
# API Endpoint Provider Configurations
# ============================================================

ENDPOINT_PROVIDERS: List[ProviderConfig] = [
    # OpenAI
    ProviderConfig(
        provider_id="openai",
        name="OpenAI",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://api.openai.com/v1",
        icon="Sparkles",
        description="OpenAI GPT series models",
        models=[
            ModelInfo("gpt-4o", "GPT-4o", context_length=128000, supports_function_calling=True, supports_vision=True),
            ModelInfo("gpt-4o-mini", "GPT-4o Mini", context_length=128000, supports_function_calling=True, supports_vision=True),
            ModelInfo("gpt-4-turbo", "GPT-4 Turbo", context_length=128000, supports_function_calling=True, supports_vision=True),
            ModelInfo("gpt-4", "GPT-4", context_length=8192, supports_function_calling=True),
            ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", context_length=16385, supports_function_calling=True),
        ]
    ),
    
    # Claude (Anthropic)
    ProviderConfig(
        provider_id="claude",
        name="Claude",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://api.anthropic.com/v1",
        icon="Bot",
        description="Anthropic Claude series models",
        models=[
            ModelInfo("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-opus-20240229", "Claude 3 Opus", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-sonnet-20240229", "Claude 3 Sonnet", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-haiku-20240307", "Claude 3 Haiku", context_length=200000, supports_function_calling=True, supports_vision=True),
        ]
    ),
    
    # Qwen (Qwen)
    ProviderConfig(
        provider_id="qianwen",
        name="Qwen",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        icon="Brain",
        description="Alibaba Cloud Qwen series models",
        models=[
            ModelInfo("qwen-turbo", "Qwen Turbo", context_length=8000, supports_function_calling=True),
            ModelInfo("qwen-plus", "Qwen Plus", context_length=32000, supports_function_calling=True),
            ModelInfo("qwen-max", "Qwen Max", context_length=32000, supports_function_calling=True),
            ModelInfo("qwen-max-longcontext", "Qwen Max Long Context", context_length=30000, supports_function_calling=True),
        ]
    ),
    
    # Baidu Qianfan (Qianfan)
    ProviderConfig(
        provider_id="qianfan",
        name="Baidu Qianfan",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
        icon="Globe",
        description="Baidu Qianfan ERNIE series models",
        models=[
            ModelInfo("ernie-4.0-8k", "ERNIE 4.0", context_length=8192, supports_function_calling=True),
            ModelInfo("ernie-3.5-8k", "ERNIE 3.5", context_length=8192, supports_function_calling=True),
            ModelInfo("ernie-speed-128k", "ERNIE Speed", context_length=128000),
            ModelInfo("ernie-lite-8k", "ERNIE Lite", context_length=8192),
        ]
    ),
    
    # Gemini (Google)
    ProviderConfig(
        provider_id="gemini",
        name="Gemini",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://generativelanguage.googleapis.com/v1",
        icon="Zap",
        description="Google Gemini series models",
        models=[
            ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", context_length=1000000, supports_function_calling=True, supports_vision=True),
            ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", context_length=1000000, supports_function_calling=True, supports_vision=True),
            ModelInfo("gemini-1.0-pro", "Gemini 1.0 Pro", context_length=32000, supports_function_calling=True),
        ]
    ),
    
    # DeepSeek
    ProviderConfig(
        provider_id="deepseek",
        name="DeepSeek",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://api.deepseek.com/v1",
        icon="MessageSquare",
        description="DeepSeek series models",
        models=[
            ModelInfo("deepseek-chat", "DeepSeek Chat", context_length=64000, supports_function_calling=True),
            ModelInfo("deepseek-coder", "DeepSeek Coder", context_length=64000, supports_function_calling=True),
        ]
    ),
    
    # Zhipu AI (Zhipu)
    ProviderConfig(
        provider_id="zhipu",
        name="Zhipu AI",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        icon="Brain",
        description="Zhipu AI GLM series models",
        models=[
            ModelInfo("glm-4", "GLM-4", context_length=128000, supports_function_calling=True),
            ModelInfo("glm-4-flash", "GLM-4 Flash", context_length=128000, supports_function_calling=True),
            ModelInfo("glm-3-turbo", "GLM-3 Turbo", context_length=128000),
        ]
    ),
    
    # Moonshot (月之暗面)
    ProviderConfig(
        provider_id="moonshot",
        name="Moonshot",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://api.moonshot.cn/v1",
        icon="Sparkles",
        description="Moonshot Kimi series models",
        models=[
            ModelInfo("moonshot-v1-8k", "Moonshot V1 8K", context_length=8000, supports_function_calling=True),
            ModelInfo("moonshot-v1-32k", "Moonshot V1 32K", context_length=32000, supports_function_calling=True),
            ModelInfo("moonshot-v1-128k", "Moonshot V1 128K", context_length=128000, supports_function_calling=True),
        ]
    ),
]


# ============================================================
# Local Model Provider Configurations
# ============================================================

LOCAL_PROVIDERS: List[ProviderConfig] = [
    ProviderConfig(
        provider_id="qianwen",
        name="Qwen (Qwen)",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Alibaba Cloud Qwen local models"
    ),
    ProviderConfig(
        provider_id="deepseek",
        name="DeepSeek",
        provider_type=ProviderType.LOCAL_MODEL,
        description="DeepSeek local models"
    ),
    ProviderConfig(
        provider_id="llama",
        name="Llama",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Meta Llama series local models"
    ),
    ProviderConfig(
        provider_id="mistral",
        name="Mistral",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Mistral AI local models"
    ),
    ProviderConfig(
        provider_id="chatglm",
        name="ChatGLM",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Zhipu AI ChatGLM local models"
    ),
    ProviderConfig(
        provider_id="baichuan",
        name="Baichuan",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Baichuan Intelligence local models"
    ),
    ProviderConfig(
        provider_id="internlm",
        name="InternLM",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Shanghai AI Lab InternLM local models"
    ),
    ProviderConfig(
        provider_id="qwen2",
        name="Qwen2",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Alibaba Cloud Qwen2 series local models"
    ),
    ProviderConfig(
        provider_id="other",
        name="Other",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Other local models"
    ),
]


# ============================================================
# Convenience Functions
# ============================================================

def get_endpoint_providers() -> List[Dict[str, Any]]:
    """Get  API endpoint provider列表"""
    return [provider.to_dict() for provider in ENDPOINT_PROVIDERS]


def get_local_providers() -> List[Dict[str, Any]]:
    """Get Local model provider列表"""
    return [provider.to_dict() for provider in LOCAL_PROVIDERS]


def get_all_providers() -> List[Dict[str, Any]]:
    """Get all providers列表"""
    return get_endpoint_providers() + get_local_providers()


def get_provider_by_id(provider_id: str) -> Optional[ProviderConfig]:
    """Get provider config by ID"""
    for provider in ENDPOINT_PROVIDERS + LOCAL_PROVIDERS:
        if provider.provider_id == provider_id:
            return provider
    return None


def get_provider_models(provider_id: str) -> List[Dict[str, Any]]:
    """Get model list for specified provider"""
    provider = get_provider_by_id(provider_id)
    if provider:
        return [model.to_dict() for model in provider.models]
    return []


def get_provider_default_url(provider_id: str) -> str:
    """Get provider default API URL"""
    provider = get_provider_by_id(provider_id)
    if provider:
        return provider.default_base_url
    return ""
