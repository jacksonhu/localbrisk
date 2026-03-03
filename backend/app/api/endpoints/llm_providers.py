"""
LLM 提供商 API 端点

提供 LLM 配置的 RESTful API 接口，供前端获取模型配置信息。
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from agent_engine.llm.config import (
    ModelRegistry,
    get_endpoint_providers,
    get_local_providers,
    get_provider_models,
    get_provider_default_url,
)


router = APIRouter()


# ============================================================
# 响应模型
# ============================================================

class ProviderResponse(BaseModel):
    """提供商响应模型"""
    value: str
    label: str
    provider_type: str
    default_url: str = ""
    icon: str | None = None
    auth_type: str = "api_key"
    rate_limit: int | None = None
    timeout: int = 60
    description: str | None = None


class ModelResponse(BaseModel):
    """模型响应模型"""
    value: str
    label: str
    context_length: int | None = None
    max_tokens: int | None = None
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False


class DefaultUrlResponse(BaseModel):
    """默认 URL 响应模型"""
    default_url: str


class ProviderSummaryResponse(BaseModel):
    """提供商摘要响应模型"""
    endpoint_count: int
    local_count: int
    total_models: int
    providers: Dict[str, List[str]]


# ============================================================
# API 端点
# ============================================================

@router.get("/providers/endpoint", response_model=List[ProviderResponse])
async def list_endpoint_providers() -> List[Dict[str, Any]]:
    """
    获取 API 端点提供商列表
    
    返回所有支持的 API 端点 LLM 提供商，包括 OpenAI、Claude、通义千问等。
    """
    return get_endpoint_providers()


@router.get("/providers/local", response_model=List[ProviderResponse])
async def list_local_providers() -> List[Dict[str, Any]]:
    """
    获取本地模型提供商列表
    
    返回所有支持的本地部署模型提供商，如 Llama、Mistral、ChatGLM 等。
    """
    return get_local_providers()


@router.get("/providers", response_model=List[ProviderResponse])
async def list_all_providers() -> List[Dict[str, Any]]:
    """
    获取所有提供商列表
    
    返回所有支持的 LLM 提供商，包括 API 端点和本地模型两种类型。
    """
    registry = ModelRegistry()
    return [p.to_dict() for p in registry.get_all_providers()]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str) -> Dict[str, Any]:
    """
    获取指定提供商信息
    
    Args:
        provider_id: 提供商标识符 (如 openai, claude, qianwen 等)
        
    Returns:
        提供商详细配置信息
    """
    registry = ModelRegistry()
    provider = registry.get_provider(provider_id)
    if not provider:
        raise HTTPException(
            status_code=404, 
            detail=f"Provider '{provider_id}' not found"
        )
    return provider.to_dict()


@router.get("/providers/{provider_id}/models", response_model=List[ModelResponse])
async def list_provider_models(provider_id: str) -> List[Dict[str, Any]]:
    """
    获取指定提供商的模型列表
    
    Args:
        provider_id: 提供商标识符
        
    Returns:
        该提供商支持的所有模型列表
    """
    models = get_provider_models(provider_id)
    if not models:
        # 检查提供商是否存在
        registry = ModelRegistry()
        if not registry.is_valid_provider(provider_id):
            raise HTTPException(
                status_code=404, 
                detail=f"Provider '{provider_id}' not found"
            )
        # 提供商存在但没有模型（如本地模型提供商）
        return []
    return models


@router.get("/providers/{provider_id}/default-url", response_model=DefaultUrlResponse)
async def get_default_url(provider_id: str) -> Dict[str, str]:
    """
    获取提供商默认 API URL
    
    Args:
        provider_id: 提供商标识符
        
    Returns:
        提供商的默认 API 基础 URL
    """
    registry = ModelRegistry()
    if not registry.is_valid_provider(provider_id):
        raise HTTPException(
            status_code=404, 
            detail=f"Provider '{provider_id}' not found"
        )
    return {"default_url": get_provider_default_url(provider_id)}


@router.get("/providers/{provider_id}/models/{model_id}", response_model=ModelResponse)
async def get_model(provider_id: str, model_id: str) -> Dict[str, Any]:
    """
    获取指定模型信息
    
    Args:
        provider_id: 提供商标识符
        model_id: 模型标识符
        
    Returns:
        模型详细配置信息
    """
    registry = ModelRegistry()
    model = registry.get_model(provider_id, model_id)
    if not model:
        raise HTTPException(
            status_code=404, 
            detail=f"Model '{model_id}' not found in provider '{provider_id}'"
        )
    return model.to_dict()


@router.get("/summary", response_model=ProviderSummaryResponse)
async def get_summary() -> Dict[str, Any]:
    """
    获取提供商摘要信息
    
    返回所有提供商和模型的统计信息。
    """
    registry = ModelRegistry()
    return registry.get_provider_summary()


@router.get("/search/providers")
async def search_providers(q: str) -> List[Dict[str, Any]]:
    """
    搜索提供商
    
    Args:
        q: 搜索关键词
        
    Returns:
        匹配的提供商列表
    """
    registry = ModelRegistry()
    providers = registry.search_providers(q)
    return [p.to_dict() for p in providers]


@router.get("/search/models")
async def search_models(q: str) -> List[Dict[str, Any]]:
    """
    搜索模型
    
    Args:
        q: 搜索关键词
        
    Returns:
        匹配的模型列表（包含提供商信息）
    """
    registry = ModelRegistry()
    return registry.search_models(q)
