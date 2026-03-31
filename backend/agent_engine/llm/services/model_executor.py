"""
Model Execution Service

Provides LLM model loading, execution, and management
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelExecutionResult:
    """Model execution result"""
    execution_id: str
    model_name: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None


@dataclass
class LoadedModel:
    """Loaded model info"""
    business_unit_id: str
    agent_name: str
    model_name: str
    model_type: str  # 'local' or 'endpoint'
    provider: Optional[str] = None
    model_id: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    
    # Execution status
    current_execution_id: Optional[str] = None
    is_executing: bool = False


class ModelExecutorService:
    """Model executor service
    
    Manages LLM model loading and execution
    """
    
    def __init__(self):
        self._loaded_models: Dict[str, LoadedModel] = {}
        self._lock = None  # asyncio.Lock will be created when needed
    
    def _get_model_key(self, business_unit_id: str, agent_name: str, model_name: str) -> str:
        """Generate unique key for a model"""
        return f"{business_unit_id}:{agent_name}:{model_name}"
    
    async def load_model(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
        model_config: Any
    ) -> LoadedModel:
        """Load model
        
        Args:
            business_unit_id: Business Unit ID
            agent_name: Agent name
            model_name: Model name
            model_config: Model config object
        
        Returns:
            LoadedModel: 已Load的model info
        """
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        # 如果已Load, 直接返回
        if key in self._loaded_models:
            logger.info(f"Model {model_name} already loaded")
            return self._loaded_models[key]
        
        # Create LoadedModel
        loaded_model = LoadedModel(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            model_type=getattr(model_config, 'model_type', 'endpoint'),
            provider=getattr(model_config, 'endpoint_provider', None) or getattr(model_config, 'local_provider', None),
            model_id=getattr(model_config, 'model_id', None),
            api_base_url=getattr(model_config, 'api_base_url', None),
            api_key=getattr(model_config, 'api_key', None),
        )
        
        self._loaded_models[key] = loaded_model
        logger.info(f"Model {model_name} loaded successfully")
        
        return loaded_model
    
    async def execute(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> ModelExecutionResult:
        """Sync Execute模型
        
        Args:
            business_unit_id: Business Unit ID
            agent_name: Agent name
            model_name: Model name
            input_text: User input
            context: Context
            temperature: Temperature parameter
            max_tokens: Max generation length
            system_prompt: System prompt
        
        Returns:
            ModelExecutionResult: Execute结果
        """
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        if key not in self._loaded_models:
            return ModelExecutionResult(
                execution_id=str(uuid.uuid4()),
                model_name=model_name,
                status="error",
                error="Model not loaded"
            )
        
        model = self._loaded_models[key]
        execution_id = str(uuid.uuid4())
        model.current_execution_id = execution_id
        model.is_executing = True
        start_time = time.time()
        
        try:
            # 根据模型类型调用不同的 API
            if model.model_type == 'endpoint':
                output, usage = await self._call_endpoint_model(
                    model, input_text, temperature, max_tokens, system_prompt
                )
            else:
                output, usage = await self._call_local_model(
                    model, input_text, temperature, max_tokens, system_prompt
                )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return ModelExecutionResult(
                execution_id=execution_id,
                model_name=model_name,
                status="success",
                output=output,
                execution_time_ms=execution_time_ms,
                usage=usage
            )
            
        except Exception as e:
            logger.error(f"Model execution failed: {e}")
            return ModelExecutionResult(
                execution_id=execution_id,
                model_name=model_name,
                status="error",
                error=str(e)
            )
        finally:
            model.is_executing = False
            model.current_execution_id = None
    
    async def execute_streaming(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
        input_text: str,
        context: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream execution of模型
        
        Args:
            business_unit_id: Business Unit ID
            agent_name: Agent name
            model_name: Model name
            input_text: User input
            context: Context
            temperature: Temperature parameter
            max_tokens: Max generation length
            system_prompt: System prompt
        
        Yields:
            Execute事件
        """
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        if key not in self._loaded_models:
            yield {
                "event_type": "error",
                "error": "Model not loaded"
            }
            return
        
        model = self._loaded_models[key]
        execution_id = str(uuid.uuid4())
        model.current_execution_id = execution_id
        model.is_executing = True
        
        try:
            # Send start event
            yield {
                "event_type": "state_change",
                "execution_id": execution_id,
                "status": "running",
                "message": f"Starting execution with model {model_name}"
            }
            
            # Send thinking event
            yield {
                "event_type": "thinking",
                "thinking": f"Processing with {model.provider or 'model'}..."
            }
            
            # 根据模型类型Execute
            if model.model_type == 'endpoint':
                async for event in self._stream_endpoint_model(
                    model, input_text, temperature, max_tokens, system_prompt
                ):
                    yield event
            else:
                async for event in self._stream_local_model(
                    model, input_text, temperature, max_tokens, system_prompt
                ):
                    yield event
            
            # Send completion event
            yield {
                "event_type": "state_change",
                "execution_id": execution_id,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Streaming execution failed: {e}")
            yield {
                "event_type": "error",
                "error": str(e)
            }
        finally:
            model.is_executing = False
            model.current_execution_id = None
    
    async def _call_endpoint_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> tuple[str, Optional[Dict[str, int]]]:
        """Call API endpoint model"""
        import httpx
        
        # Build消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})
        
        # Buildrequest体
        request_body: Dict[str, Any] = {
            "model": model.model_id,
            "messages": messages,
        }
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens
        
        # Determine API URL
        api_url = model.api_base_url or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = f"{api_url.rstrip('/')}/chat/completions"
        
        # 发送request
        headers = {
            "Content-Type": "application/json",
        }
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=request_body, headers=headers)
            response.raise_for_status()
            result = response.json()
        
        # Parseresponse
        output = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage")
        
        return output, usage
    
    async def _call_local_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> tuple[str, Optional[Dict[str, int]]]:
        """调用本地模型 (暂时返回模拟response)"""
        # TODO: 集成本地模型运行时 (如 llama.cpp, Ollama 等)
        return f"[Local Model Response] This is a placeholder response for: {input_text}", None
    
    async def _stream_endpoint_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式Call API endpoint model"""
        import httpx
        
        # Build消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})
        
        # Buildrequest体
        request_body: Dict[str, Any] = {
            "model": model.model_id,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens
        
        # Determine API URL
        api_url = model.api_base_url or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = f"{api_url.rstrip('/')}/chat/completions"
        
        # 发送request
        headers = {
            "Content-Type": "application/json",
        }
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"
        
        full_content = ""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", api_url, json=request_body, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                full_content += content
                                yield {
                                    "event_type": "llm_response",
                                    "data": {
                                        "content": full_content,
                                        "delta": content
                                    }
                                }
                        except:
                            continue
        
        # Send final message
        yield {
            "event_type": "message_received",
            "message": full_content
        }
    
    async def _stream_local_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式调用本地模型 (暂时返回模拟response)"""
        import asyncio
        
        # TODO: 集成本地模型运行时
        response = f"[Local Model Response] This is a placeholder streaming response for: {input_text}"
        
        # Simulate streaming output
        words = response.split()
        full_content = ""
        
        for word in words:
            full_content += word + " "
            yield {
                "event_type": "llm_response",
                "data": {
                    "content": full_content.strip(),
                    "delta": word + " "
                }
            }
            await asyncio.sleep(0.05)
        
        yield {
            "event_type": "message_received",
            "message": full_content.strip()
        }
    
    async def get_status(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get model execution状态"""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        if key not in self._loaded_models:
            return None
        
        model = self._loaded_models[key]
        
        return {
            "execution_id": model.current_execution_id,
            "status": "running" if model.is_executing else "idle",
            "model_name": model.model_name,
        }
    
    async def cancel(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str
    ) -> bool:
        """Cancel model execution"""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        if key not in self._loaded_models:
            return False
        
        model = self._loaded_models[key]
        if not model.is_executing:
            return False
        
        # TODO: 实现真正的取消逻辑
        model.is_executing = False
        model.current_execution_id = None
        
        return True
    
    async def cleanup_model(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str
    ) -> bool:
        """Clean up model resources"""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        
        if key not in self._loaded_models:
            return False
        
        del self._loaded_models[key]
        logger.info(f"Model {model_name} unloaded")
        
        return True
    
    def list_loaded_models(self) -> list:
        """List loaded models"""
        return [
            {
                "business_unit_id": m.business_unit_id,
                "agent_name": m.agent_name,
                "model_name": m.model_name,
                "model_type": m.model_type,
                "provider": m.provider,
                "is_executing": m.is_executing,
                "loaded_at": m.loaded_at.isoformat(),
            }
            for m in self._loaded_models.values()
        ]


# Global singleton
_model_executor_service: Optional[ModelExecutorService] = None


def get_model_executor_service() -> ModelExecutorService:
    """Get Model executor service单例"""
    global _model_executor_service
    if _model_executor_service is None:
        _model_executor_service = ModelExecutorService()
    return _model_executor_service
