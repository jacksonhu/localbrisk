"""
LLM 提供商配置

该模块包含所有支持的 LLM 提供商和模型配置，
从前端配置迁移而来，保持前后端一致性。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ProviderType(str, Enum):
    """提供商类型"""
    API_ENDPOINT = "api_endpoint"  # API 端点提供商
    LOCAL_MODEL = "local_model"   # 本地模型提供商


@dataclass
class ModelInfo:
    """模型信息"""
    value: str                              # 模型标识符
    label: str                              # 显示名称
    context_length: Optional[int] = None    # 上下文长度
    max_tokens: Optional[int] = None        # 最大输出 token 数
    supports_streaming: bool = True         # 是否支持流式输出
    supports_function_calling: bool = False # 是否支持函数调用
    supports_vision: bool = False           # 是否支持视觉输入
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
    """提供商配置"""
    provider_id: str                        # 提供商标识符
    name: str                               # 显示名称
    provider_type: ProviderType             # 提供商类型
    default_base_url: str = ""              # 默认 API 基础 URL
    models: List[ModelInfo] = field(default_factory=list)  # 支持的模型列表
    icon: Optional[str] = None              # 图标名称
    auth_type: str = "api_key"              # 认证类型
    headers: Dict[str, str] = field(default_factory=dict)  # 额外请求头
    rate_limit: Optional[int] = None        # 速率限制
    timeout: int = 60                       # 请求超时时间
    description: Optional[str] = None       # 描述
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
# API 端点提供商配置
# ============================================================

ENDPOINT_PROVIDERS: List[ProviderConfig] = [
    # OpenAI
    ProviderConfig(
        provider_id="openai",
        name="OpenAI",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://api.openai.com/v1",
        icon="Sparkles",
        description="OpenAI GPT 系列模型",
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
        description="Anthropic Claude 系列模型",
        models=[
            ModelInfo("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-opus-20240229", "Claude 3 Opus", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-sonnet-20240229", "Claude 3 Sonnet", context_length=200000, supports_function_calling=True, supports_vision=True),
            ModelInfo("claude-3-haiku-20240307", "Claude 3 Haiku", context_length=200000, supports_function_calling=True, supports_vision=True),
        ]
    ),
    
    # 通义千问 (Qwen)
    ProviderConfig(
        provider_id="qianwen",
        name="通义千问",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        icon="Brain",
        description="阿里云通义千问系列模型",
        models=[
            ModelInfo("qwen-turbo", "Qwen Turbo", context_length=8000, supports_function_calling=True),
            ModelInfo("qwen-plus", "Qwen Plus", context_length=32000, supports_function_calling=True),
            ModelInfo("qwen-max", "Qwen Max", context_length=32000, supports_function_calling=True),
            ModelInfo("qwen-max-longcontext", "Qwen Max Long Context", context_length=30000, supports_function_calling=True),
        ]
    ),
    
    # 百度千帆 (Qianfan)
    ProviderConfig(
        provider_id="qianfan",
        name="百度千帆",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
        icon="Globe",
        description="百度千帆文心一言系列模型",
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
        description="Google Gemini 系列模型",
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
        description="DeepSeek 系列模型",
        models=[
            ModelInfo("deepseek-chat", "DeepSeek Chat", context_length=64000, supports_function_calling=True),
            ModelInfo("deepseek-coder", "DeepSeek Coder", context_length=64000, supports_function_calling=True),
        ]
    ),
    
    # 智谱 AI (Zhipu)
    ProviderConfig(
        provider_id="zhipu",
        name="智谱 AI",
        provider_type=ProviderType.API_ENDPOINT,
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        icon="Brain",
        description="智谱 AI GLM 系列模型",
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
        description="Moonshot Kimi 系列模型",
        models=[
            ModelInfo("moonshot-v1-8k", "Moonshot V1 8K", context_length=8000, supports_function_calling=True),
            ModelInfo("moonshot-v1-32k", "Moonshot V1 32K", context_length=32000, supports_function_calling=True),
            ModelInfo("moonshot-v1-128k", "Moonshot V1 128K", context_length=128000, supports_function_calling=True),
        ]
    ),
]


# ============================================================
# 本地模型提供商配置
# ============================================================

LOCAL_PROVIDERS: List[ProviderConfig] = [
    ProviderConfig(
        provider_id="qianwen",
        name="通义千问 (Qwen)",
        provider_type=ProviderType.LOCAL_MODEL,
        description="阿里云通义千问本地模型"
    ),
    ProviderConfig(
        provider_id="deepseek",
        name="DeepSeek",
        provider_type=ProviderType.LOCAL_MODEL,
        description="DeepSeek 本地模型"
    ),
    ProviderConfig(
        provider_id="llama",
        name="Llama",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Meta Llama 系列本地模型"
    ),
    ProviderConfig(
        provider_id="mistral",
        name="Mistral",
        provider_type=ProviderType.LOCAL_MODEL,
        description="Mistral AI 本地模型"
    ),
    ProviderConfig(
        provider_id="chatglm",
        name="ChatGLM",
        provider_type=ProviderType.LOCAL_MODEL,
        description="智谱 AI ChatGLM 本地模型"
    ),
    ProviderConfig(
        provider_id="baichuan",
        name="百川",
        provider_type=ProviderType.LOCAL_MODEL,
        description="百川智能本地模型"
    ),
    ProviderConfig(
        provider_id="internlm",
        name="InternLM",
        provider_type=ProviderType.LOCAL_MODEL,
        description="上海人工智能实验室 InternLM 本地模型"
    ),
    ProviderConfig(
        provider_id="qwen2",
        name="Qwen2",
        provider_type=ProviderType.LOCAL_MODEL,
        description="阿里云 Qwen2 系列本地模型"
    ),
    ProviderConfig(
        provider_id="other",
        name="其他",
        provider_type=ProviderType.LOCAL_MODEL,
        description="其他本地模型"
    ),
]


# ============================================================
# 便捷函数
# ============================================================

def get_endpoint_providers() -> List[Dict[str, Any]]:
    """获取 API 端点提供商列表"""
    return [provider.to_dict() for provider in ENDPOINT_PROVIDERS]


def get_local_providers() -> List[Dict[str, Any]]:
    """获取本地模型提供商列表"""
    return [provider.to_dict() for provider in LOCAL_PROVIDERS]


def get_all_providers() -> List[Dict[str, Any]]:
    """获取所有提供商列表"""
    return get_endpoint_providers() + get_local_providers()


def get_provider_by_id(provider_id: str) -> Optional[ProviderConfig]:
    """根据 ID 获取提供商配置"""
    for provider in ENDPOINT_PROVIDERS + LOCAL_PROVIDERS:
        if provider.provider_id == provider_id:
            return provider
    return None


def get_provider_models(provider_id: str) -> List[Dict[str, Any]]:
    """获取指定提供商的模型列表"""
    provider = get_provider_by_id(provider_id)
    if provider:
        return [model.to_dict() for model in provider.models]
    return []


def get_provider_default_url(provider_id: str) -> str:
    """获取提供商默认 API URL"""
    provider = get_provider_by_id(provider_id)
    if provider:
        return provider.default_base_url
    return ""
