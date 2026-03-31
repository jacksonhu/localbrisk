"""
LLM Model Registry

Provides unified query and management for models and providers.
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
    """Model registry - manages all LLM providers and models"""
    
    _instance: Optional["ModelRegistry"] = None
    
    def __new__(cls) -> "ModelRegistry":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Provider index
        self._endpoint_providers: Dict[str, ProviderConfig] = {
            p.provider_id: p for p in ENDPOINT_PROVIDERS
        }
        self._local_providers: Dict[str, ProviderConfig] = {
            p.provider_id: p for p in LOCAL_PROVIDERS
        }
        
        # Model index
        self._models: Dict[str, Dict[str, ModelInfo]] = {}
        for provider in ENDPOINT_PROVIDERS:
            self._models[provider.provider_id] = {
                m.value: m for m in provider.models
            }
    
    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get provider config"""
        provider = self._endpoint_providers.get(provider_id)
        if provider:
            return provider
        return self._local_providers.get(provider_id)
    
    def get_endpoint_providers(self) -> List[ProviderConfig]:
        """Get all API endpoint providers"""
        return list(self._endpoint_providers.values())
    
    def get_local_providers(self) -> List[ProviderConfig]:
        """Get all local model providers"""
        return list(self._local_providers.values())
    
    def get_all_providers(self) -> List[ProviderConfig]:
        """Get all providers"""
        return self.get_endpoint_providers() + self.get_local_providers()
    
    def get_models(self, provider_id: str) -> List[ModelInfo]:
        """Get model list for specified provider"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.models
        return []
    
    def get_model(self, provider_id: str, model_id: str) -> Optional[ModelInfo]:
        """Get 指定model info"""
        models = self._models.get(provider_id, {})
        return models.get(model_id)
    
    def get_default_url(self, provider_id: str) -> str:
        """Get provider default API URL"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.default_base_url
        return ""
    
    def search_providers(self, keyword: str) -> List[ProviderConfig]:
        """Search providers"""
        keyword_lower = keyword.lower()
        results = []
        for provider in self.get_all_providers():
            if (keyword_lower in provider.provider_id.lower() or
                keyword_lower in provider.name.lower()):
                results.append(provider)
        return results
    
    def search_models(self, keyword: str) -> List[Dict[str, Any]]:
        """Search models"""
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
        """Check if provider is valid"""
        return self.get_provider(provider_id) is not None
    
    def is_valid_model(self, provider_id: str, model_id: str) -> bool:
        """Check if model is valid"""
        return self.get_model(provider_id, model_id) is not None
    
    def get_provider_summary(self) -> Dict[str, Any]:
        """Get provider summary"""
        return {
            "endpoint_count": len(self._endpoint_providers),
            "local_count": len(self._local_providers),
            "total_models": sum(len(models) for models in self._models.values()),
            "providers": {
                "endpoint": list(self._endpoint_providers.keys()),
                "local": list(self._local_providers.keys()),
            }
        }
