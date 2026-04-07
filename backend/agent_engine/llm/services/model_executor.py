"""Model execution service for endpoint and placeholder local models."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

from ...core.exceptions import LocalModelNotImplementedError, serialize_exception
from ...monitoring import emit_runtime_event, get_logging_context, scoped_logging_context

logger = logging.getLogger(__name__)


@dataclass
class ModelExecutionResult:
    """Structured model execution result."""

    execution_id: str
    model_name: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    error_type: Optional[str] = None
    suggestion: Optional[str] = None
    retryable: bool = False
    placeholder: bool = False
    execution_time_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None


@dataclass
class LoadedModel:
    """Loaded model descriptor stored in runtime memory."""

    business_unit_id: str
    agent_name: str
    model_name: str
    model_type: str
    provider: Optional[str] = None
    model_id: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    current_execution_id: Optional[str] = None
    is_executing: bool = False


class ModelExecutorService:
    """Manage model runtime loading, execution, and cleanup."""

    def __init__(self):
        self._loaded_models: Dict[str, LoadedModel] = {}
        self._lock = None

    def _get_model_key(self, business_unit_id: str, agent_name: str, model_name: str) -> str:
        """Generate a stable runtime key for a model."""
        return f"{business_unit_id}:{agent_name}:{model_name}"

    @staticmethod
    def _context_value(context: Optional[Dict[str, Any]], key: str) -> Optional[str]:
        if not isinstance(context, dict):
            return None
        raw = context.get(key)
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    def _build_observability_context(
        self,
        *,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
        context: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
        component: str,
        ensure_request_id: bool = False,
    ) -> Dict[str, Any]:
        current = get_logging_context()
        request_id = self._context_value(context, "request_id") or current.get("request_id")
        if ensure_request_id and not request_id:
            request_id = str(uuid.uuid4())
        session_id = self._context_value(context, "session_id") or current.get("session_id") or execution_id or model_name
        payload = {
            "request_id": request_id,
            "session_id": session_id,
            "business_unit_id": business_unit_id,
            "agent_id": agent_name,
            "model_name": model_name,
            "execution_id": execution_id,
            "component": component,
        }
        return {key: value for key, value in payload.items() if value is not None and value != ""}

    @staticmethod
    def _not_loaded_error() -> Dict[str, Any]:
        return {
            "message": "Model is not loaded",
            "error_code": "MODEL_NOT_LOADED",
            "error_type": "ModelNotLoadedError",
            "suggestion": "Load the model before executing it",
            "retryable": False,
            "placeholder": False,
        }

    @staticmethod
    def _normalize_execution_error(exc: Exception) -> Dict[str, Any]:
        payload = serialize_exception(exc)
        return {
            "message": payload.get("message", str(exc)),
            "error_code": payload.get("error_code"),
            "error_type": payload.get("error_type", type(exc).__name__),
            "suggestion": payload.get("suggestion"),
            "retryable": bool(payload.get("retryable", False)),
            "placeholder": payload.get("error_code") == "LOCAL_MODEL_NOT_IMPLEMENTED",
        }

    @staticmethod
    def _build_error_result(
        execution_id: str,
        model_name: str,
        error_payload: Dict[str, Any],
    ) -> ModelExecutionResult:
        return ModelExecutionResult(
            execution_id=execution_id,
            model_name=model_name,
            status="error",
            error=error_payload.get("message"),
            error_code=error_payload.get("error_code"),
            error_type=error_payload.get("error_type"),
            suggestion=error_payload.get("suggestion"),
            retryable=bool(error_payload.get("retryable", False)),
            placeholder=bool(error_payload.get("placeholder", False)),
        )

    @staticmethod
    def _build_error_event(
        execution_id: str,
        error_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "event_type": "error",
            "execution_id": execution_id,
            "error": error_payload.get("message"),
            "error_code": error_payload.get("error_code"),
            "error_type": error_payload.get("error_type"),
            "suggestion": error_payload.get("suggestion"),
            "retryable": bool(error_payload.get("retryable", False)),
            "placeholder": bool(error_payload.get("placeholder", False)),
        }

    async def load_model(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
        model_config: Any,
    ) -> LoadedModel:
        """Load model metadata into runtime memory."""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            component="model_runtime.load",
        )

        with scoped_logging_context(**operation_context):
            if key in self._loaded_models:
                logger.info("Model already loaded: %s", key)
                emit_runtime_event("model.load.reused")
                return self._loaded_models[key]

            loaded_model = LoadedModel(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                model_name=model_name,
                model_type=getattr(model_config, "model_type", "endpoint"),
                provider=getattr(model_config, "endpoint_provider", None) or getattr(model_config, "local_provider", None),
                model_id=getattr(model_config, "model_id", None),
                api_base_url=getattr(model_config, "api_base_url", None),
                api_key=getattr(model_config, "api_key", None),
            )

            self._loaded_models[key] = loaded_model
            logger.info("Model loaded successfully: %s", key)
            emit_runtime_event(
                "model.load.completed",
                model_type=loaded_model.model_type,
                provider=loaded_model.provider,
            )
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
        system_prompt: Optional[str] = None,
    ) -> ModelExecutionResult:
        """Execute a loaded model synchronously."""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        execution_id = str(uuid.uuid4())
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            context=context,
            execution_id=execution_id,
            component="model_runtime.execute",
            ensure_request_id=True,
        )

        with scoped_logging_context(**operation_context):
            if key not in self._loaded_models:
                error_payload = self._not_loaded_error()
                emit_runtime_event(
                    "model.execution.failed",
                    level=logging.ERROR,
                    error_code=error_payload["error_code"],
                    error_type=error_payload["error_type"],
                    message=error_payload["message"],
                )
                return self._build_error_result(execution_id, model_name, error_payload)

            model = self._loaded_models[key]
            model.current_execution_id = execution_id
            model.is_executing = True
            start_time = time.time()
            emit_runtime_event(
                "model.execution.started",
                model_type=model.model_type,
                provider=model.provider,
                input_length=len(input_text),
            )

            try:
                if model.model_type == "endpoint":
                    output, usage = await self._call_endpoint_model(
                        model,
                        input_text,
                        temperature,
                        max_tokens,
                        system_prompt,
                    )
                else:
                    output, usage = await self._call_local_model(
                        model,
                        input_text,
                        temperature,
                        max_tokens,
                        system_prompt,
                    )

                execution_time_ms = int((time.time() - start_time) * 1000)
                emit_runtime_event(
                    "model.execution.completed",
                    duration_ms=execution_time_ms,
                    model_type=model.model_type,
                    provider=model.provider,
                )
                return ModelExecutionResult(
                    execution_id=execution_id,
                    model_name=model_name,
                    status="success",
                    output=output,
                    execution_time_ms=execution_time_ms,
                    usage=usage,
                )
            except Exception as exc:
                error_payload = self._normalize_execution_error(exc)
                logger.error("Model execution failed for %s: %s", key, exc, exc_info=True)
                emit_runtime_event(
                    "model.execution.failed",
                    level=logging.ERROR,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_code=error_payload.get("error_code"),
                    error_type=error_payload.get("error_type"),
                    message=error_payload.get("message"),
                    suggestion=error_payload.get("suggestion"),
                    placeholder=error_payload.get("placeholder"),
                )
                result = self._build_error_result(execution_id, model_name, error_payload)
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                return result
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
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a loaded model with SSE-friendly event payloads."""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        execution_id = str(uuid.uuid4())
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            context=context,
            execution_id=execution_id,
            component="model_runtime.stream",
            ensure_request_id=True,
        )

        with scoped_logging_context(**operation_context):
            if key not in self._loaded_models:
                error_payload = self._not_loaded_error()
                emit_runtime_event(
                    "model.execution.failed",
                    level=logging.ERROR,
                    error_code=error_payload["error_code"],
                    error_type=error_payload["error_type"],
                    message=error_payload["message"],
                    mode="stream",
                )
                yield self._build_error_event(execution_id, error_payload)
                return

            model = self._loaded_models[key]
            model.current_execution_id = execution_id
            model.is_executing = True
            start_time = time.time()
            emit_runtime_event(
                "model.execution.started",
                mode="stream",
                model_type=model.model_type,
                provider=model.provider,
                input_length=len(input_text),
            )

            try:
                yield {
                    "event_type": "state_change",
                    "execution_id": execution_id,
                    "status": "running",
                    "message": f"Starting execution with model {model_name}",
                }
                yield {
                    "event_type": "thinking",
                    "execution_id": execution_id,
                    "thinking": f"Processing with {model.provider or 'model'}...",
                }

                if model.model_type == "endpoint":
                    async for event in self._stream_endpoint_model(
                        model,
                        input_text,
                        temperature,
                        max_tokens,
                        system_prompt,
                    ):
                        yield event
                else:
                    async for event in self._stream_local_model(
                        model,
                        input_text,
                        temperature,
                        max_tokens,
                        system_prompt,
                    ):
                        yield event

                execution_time_ms = int((time.time() - start_time) * 1000)
                emit_runtime_event(
                    "model.execution.completed",
                    mode="stream",
                    duration_ms=execution_time_ms,
                    model_type=model.model_type,
                    provider=model.provider,
                )
                yield {
                    "event_type": "state_change",
                    "execution_id": execution_id,
                    "status": "success",
                }
            except Exception as exc:
                error_payload = self._normalize_execution_error(exc)
                logger.error("Streaming model execution failed for %s: %s", key, exc, exc_info=True)
                emit_runtime_event(
                    "model.execution.failed",
                    level=logging.ERROR,
                    mode="stream",
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_code=error_payload.get("error_code"),
                    error_type=error_payload.get("error_type"),
                    message=error_payload.get("message"),
                    suggestion=error_payload.get("suggestion"),
                    placeholder=error_payload.get("placeholder"),
                )
                yield self._build_error_event(execution_id, error_payload)
                yield {
                    "event_type": "state_change",
                    "execution_id": execution_id,
                    "status": "failed",
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
        system_prompt: Optional[str],
    ) -> tuple[str, Optional[Dict[str, int]]]:
        """Call an endpoint model using an OpenAI-compatible API."""
        import httpx

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})

        request_body: Dict[str, Any] = {
            "model": model.model_id,
            "messages": messages,
        }
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens

        api_url = model.api_base_url or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = f"{api_url.rstrip('/')}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=request_body, headers=headers)
            response.raise_for_status()
            result = response.json()

        output = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage")
        return output, usage

    async def _call_local_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str],
    ) -> tuple[str, Optional[Dict[str, int]]]:
        """Raise a stable placeholder error for local model execution."""
        del input_text, temperature, max_tokens, system_prompt
        raise LocalModelNotImplementedError(provider=model.provider, model_name=model.model_name)

    async def _stream_endpoint_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream an endpoint model using an OpenAI-compatible API."""
        import httpx
        import json

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": input_text})

        request_body: Dict[str, Any] = {
            "model": model.model_id,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            request_body["temperature"] = temperature
        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens

        api_url = model.api_base_url or "https://api.openai.com/v1"
        if not api_url.endswith("/chat/completions"):
            api_url = f"{api_url.rstrip('/')}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"

        full_content = ""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", api_url, json=request_body, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except Exception:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if not content:
                        continue
                    full_content += content
                    yield {
                        "event_type": "llm_response",
                        "data": {
                            "content": full_content,
                            "delta": content,
                        },
                    }

        yield {
            "event_type": "message_received",
            "message": full_content,
        }

    async def _stream_local_model(
        self,
        model: LoadedModel,
        input_text: str,
        temperature: Optional[float],
        max_tokens: Optional[int],
        system_prompt: Optional[str],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Raise a stable placeholder error for local model streaming."""
        del input_text, temperature, max_tokens, system_prompt
        raise LocalModelNotImplementedError(provider=model.provider, model_name=model.model_name)
        yield  # pragma: no cover

    async def get_status(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Return runtime status for a model."""
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
        model_name: str,
    ) -> bool:
        """Cancel an active model execution."""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            component="model_runtime.cancel",
        )
        with scoped_logging_context(**operation_context):
            if key not in self._loaded_models:
                return False

            model = self._loaded_models[key]
            if not model.is_executing:
                return False

            model.is_executing = False
            model.current_execution_id = None
            emit_runtime_event("model.execution.cancelled")
            return True

    async def cleanup_model(
        self,
        business_unit_id: str,
        agent_name: str,
        model_name: str,
    ) -> bool:
        """Remove a loaded model from runtime memory."""
        key = self._get_model_key(business_unit_id, agent_name, model_name)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            model_name=model_name,
            component="model_runtime.unload",
        )
        with scoped_logging_context(**operation_context):
            if key not in self._loaded_models:
                return False

            del self._loaded_models[key]
            logger.info("Model unloaded: %s", key)
            emit_runtime_event("model.unload.completed")
            return True

    def list_loaded_models(self) -> list:
        """Return all loaded models."""
        return [
            {
                "business_unit_id": model.business_unit_id,
                "agent_name": model.agent_name,
                "model_name": model.model_name,
                "model_type": model.model_type,
                "provider": model.provider,
                "is_executing": model.is_executing,
                "loaded_at": model.loaded_at.isoformat(),
            }
            for model in self._loaded_models.values()
        ]


_model_executor_service: Optional[ModelExecutorService] = None



def get_model_executor_service() -> ModelExecutorService:
    """Return the shared model executor service instance."""
    global _model_executor_service
    if _model_executor_service is None:
        _model_executor_service = ModelExecutorService()
    return _model_executor_service
