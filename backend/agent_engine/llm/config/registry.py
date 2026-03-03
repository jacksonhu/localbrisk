"""
LLM 模型注册表

提供模型和提供商的统一查询和管理功能。
"""

from typing import Dict, List, Optional, Any
from .providers import (
    ProviderConfig,
    ModelInfo,
    ENDPOINT_PROVIDERS,
    LOCAL_PROVIDERS,
    get_provider_by_id,
)


class ModelRegistry:
    """模型注册表 - 管理所有 LLM 提供商和模型"""
    
    _instance: Optional["ModelRegistry"] = None
    
    def __new__(cls) -> "ModelRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 提供商索引
        self._endpoint_providers: Dict[str, ProviderConfig] = {
            p.provider_id: p for p in ENDPOINT_PROVIDERS
        }
        self._local_providers: Dict[str, ProviderConfig] = {
            p.provider_id: p for p in LOCAL_PROVIDERS
        }
        
        # 模型索引
        self._models: Dict[str, Dict[str, ModelInfo]] = {}
        for provider in ENDPOINT_PROVIDERS:
            self._models[provider.provider_id] = {
                m.value: m for m in provider.models
            }
    
    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """获取提供商配置"""
        provider = self._endpoint_providers.get(provider_id)
        if provider:
            return provider
        return self._local_providers.get(provider_id)
    
    def get_endpoint_providers(self) -> List[ProviderConfig]:
        """获取所有 API 端点提供商"""
        return list(self._endpoint_providers.values())
    
    def get_local_providers(self) -> List[ProviderConfig]:
        """获取所有本地模型提供商"""
        return list(self._local_providers.values())
    
    def get_all_providers(self) -> List[ProviderConfig]:
        """获取所有提供商"""
        return self.get_endpoint_providers() + self.get_local_providers()
    
    def get_models(self, provider_id: str) -> List[ModelInfo]:
        """获取指定提供商的模型列表"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.models
        return []
    
    def get_model(self, provider_id: str, model_id: str) -> Optional[ModelInfo]:
        """获取指定模型信息"""
        models = self._models.get(provider_id, {})
        return models.get(model_id)
    
    def get_default_url(self, provider_id: str) -> str:
        """获取提供商默认 API URL"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.default_base_url
        return ""
    
    def search_providers(self, keyword: str) -> List[ProviderConfig]:
        """搜索提供商"""
        keyword_lower = keyword.lower()
        results = []
        for provider in self.get_all_providers():
            if (keyword_lower in provider.provider_id.lower() or
                keyword_lower in provider.name.lower()):
                results.append(provider)
        return results
    
    def search_models(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索模型"""
        keyword_lower = keyword.lower()
        results = []
        for provider_id, models in self._models.items():
            for model_id, model in models.items():
                if (keyword_lower in model.value.lower() or
                    keyword_lower in model.label.lower()):
                    results.append({
                        "provider_id": provider_id,
                        "model": model.to_dict()
                    })
        return results
    
    def is_valid_provider(self, provider_id: str) -> bool:
        """检查提供商是否有效"""
        return self.get_provider(provider_id) is not None
    
    def is_valid_model(self, provider_id: str, model_id: str) -> bool:
        """检查模型是否有效"""
        return self.get_model(provider_id, model_id) is not None
    
    def get_provider_summary(self) -> Dict[str, Any]:
        """获取提供商摘要信息"""
        return {
            "endpoint_count": len(self._endpoint_providers),
            "local_count": len(self._local_providers),
            "total_models": sum(len(models) for models in self._models.values()),
            "providers": {
                "endpoint": list(self._endpoint_providers.keys()),
                "local": list(self._local_providers.keys()),
            }
        }
