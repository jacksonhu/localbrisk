"""
LLM Provider API Endpoints

Provides RESTful API for LLM config, used by frontend to get model configuration.
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
# Response models
# ============================================================

class ProviderResponse(BaseModel):
    """Provider response model"""
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
    """Model response model"""
    value: str
    label: str
    context_length: int | None = None
    max_tokens: int | None = None
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False


class DefaultUrlResponse(BaseModel):
    """Default URL response model"""
    default_url: str


class ProviderSummaryResponse(BaseModel):
    """provider摘要response模型"""
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
    Get API endpoint provider列表
    
    返回所有支持的 API 端点 LLM provider, 包括 OpenAI、Claude、Qwen等.
    """
    return get_endpoint_providers()


@router.get("/providers/local", response_model=List[ProviderResponse])
async def list_local_providers() -> List[Dict[str, Any]]:
    """
    GetLocal model provider列表
    
    返回所有支持的本地部署模型provider, 如 Llama、Mistral、ChatGLM 等.
    """
    return get_local_providers()


@router.get("/providers", response_model=List[ProviderResponse])
async def list_all_providers() -> List[Dict[str, Any]]:
    """
    Get所有provider列表
    
    返回所有支持的 LLM provider, 包括 API 端点和本地模型两种类型.
    """
    registry = ModelRegistry()
    return [p.to_dict() for p in registry.get_all_providers()]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str) -> Dict[str, Any]:
    """
    Get指定provider信息
    
    Args:
        provider_id: provider标识符 (如 openai, claude, qianwen 等)
        
    Returns:
        provider详细配置信息
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
    Get指定provider的model list
    
    Args:
        provider_id: provider标识符
        
    Returns:
        该provider支持的所有model list
    """
    models = get_provider_models(provider_id)
    if not models:
        # Checkproviderexists
        registry = ModelRegistry()
        if not registry.is_valid_provider(provider_id):
            raise HTTPException(
                status_code=404, 
                detail=f"Provider '{provider_id}' not found"
            )
        # provider存在但没有模型 (如Local model provider)
        return []
    return models


@router.get("/providers/{provider_id}/default-url", response_model=DefaultUrlResponse)
async def get_default_url(provider_id: str) -> Dict[str, str]:
    """
    Getprovider默认 API URL
    
    Args:
        provider_id: provider标识符
        
    Returns:
        provider的默认 API 基础 URL
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
    Get指定model info
    
    Args:
        provider_id: provider标识符
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
    Getprovider摘要信息
    
    返回所有provider和模型的统计信息.
    """
    registry = ModelRegistry()
    return registry.get_provider_summary()


@router.get("/search/providers")
async def search_providers(q: str) -> List[Dict[str, Any]]:
    """
    搜索provider
    
    Args:
        q: 搜索关键词
        
    Returns:
        匹配的provider列表
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
        匹配的model list (containsprovider信息)
    """
    registry = ModelRegistry()
    return registry.search_models(q)
