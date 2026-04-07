"""Model runtime API endpoints."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_engine.llm.services.model_executor import get_model_executor_service
from agent_engine.monitoring import emit_runtime_event, scoped_logging_context
from app.services import business_unit_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ModelExecuteRequest(BaseModel):
    """Request payload for model execution."""

    input: str = Field(..., description="User input")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Execution context")
    temperature: Optional[float] = Field(default=None, description="Temperature parameter")
    max_tokens: Optional[int] = Field(default=None, description="Maximum generation length")
    system_prompt: Optional[str] = Field(default=None, description="System prompt")


class ModelExecutionResponse(BaseModel):
    """Structured response for synchronous model execution."""

    execution_id: str
    model_name: str
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    error_type: Optional[str] = None
    suggestion: Optional[str] = None
    retryable: bool = False
    placeholder: bool = False
    execution_time_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None


class ModelStatusResponse(BaseModel):
    """Runtime status for a loaded model."""

    execution_id: Optional[str] = None
    status: str
    model_name: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None



def _build_request_context(
    *,
    http_request: Request,
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    context: Optional[Dict[str, Any]] = None,
    component: str,
) -> Dict[str, Any]:
    request_id = http_request.headers.get("X-Request-ID")
    if not request_id and isinstance(context, dict):
        raw_request_id = context.get("request_id")
        if raw_request_id is not None:
            request_id = str(raw_request_id).strip() or None
    if not request_id:
        request_id = str(uuid.uuid4())

    session_id = None
    if isinstance(context, dict):
        raw_session_id = context.get("session_id")
        if raw_session_id is not None:
            session_id = str(raw_session_id).strip() or None
    session_id = session_id or request_id

    return {
        "request_id": request_id,
        "session_id": session_id,
        "business_unit_id": business_unit_id,
        "agent_id": agent_name,
        "model_name": model_name,
        "component": component,
    }


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/load")
async def load_model(business_unit_id: str, agent_name: str, model_name: str, http_request: Request):
    """Load a model configuration into runtime memory."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        component="model_runtime_api.load",
    )
    with scoped_logging_context(**operation_context):
        try:
            executor = get_model_executor_service()
            model = business_unit_service.agent_service.get_model(business_unit_id, agent_name, model_name)
            if not model:
                raise HTTPException(status_code=404, detail="Model not found")

            await executor.load_model(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                model_name=model_name,
                model_config=model,
            )
            emit_runtime_event("model.api.load.completed")
            logger.info("Loaded model runtime: %s/%s/%s", business_unit_id, agent_name, model_name)
            return {
                "message": "Model loaded successfully",
                "model_name": model_name,
                "business_unit_id": business_unit_id,
                "agent_name": agent_name,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Failed to load model runtime %s/%s/%s: %s",
                business_unit_id,
                agent_name,
                model_name,
                exc,
                exc_info=True,
            )
            emit_runtime_event(
                "model.api.load.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute", response_model=ModelExecutionResponse)
async def execute_model(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest,
    http_request: Request,
):
    """Execute a model synchronously."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        context=request.context,
        component="model_runtime_api.execute",
    )
    with scoped_logging_context(**operation_context):
        try:
            executor = get_model_executor_service()
            result = await executor.execute(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                model_name=model_name,
                input_text=request.input,
                context=request.context,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                system_prompt=request.system_prompt,
            )
            emit_runtime_event(
                "model.api.execute.completed",
                status=result.status,
                error_code=result.error_code,
                placeholder=result.placeholder,
            )
            return ModelExecutionResponse(
                execution_id=result.execution_id,
                model_name=result.model_name,
                status=result.status,
                output=result.output,
                error=result.error,
                error_code=result.error_code,
                error_type=result.error_type,
                suggestion=result.suggestion,
                retryable=result.retryable,
                placeholder=result.placeholder,
                execution_time_ms=result.execution_time_ms,
                usage=result.usage,
            )
        except Exception as exc:
            logger.error(
                "Failed to execute model %s/%s/%s: %s",
                business_unit_id,
                agent_name,
                model_name,
                exc,
                exc_info=True,
            )
            emit_runtime_event(
                "model.api.execute.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/execute/stream")
async def execute_model_streaming(
    business_unit_id: str,
    agent_name: str,
    model_name: str,
    request: ModelExecuteRequest,
    http_request: Request,
):
    """Execute a model with SSE streaming output."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        context=request.context,
        component="model_runtime_api.stream",
    )

    async def event_generator():
        event_count = 0
        with scoped_logging_context(**operation_context):
            try:
                executor = get_model_executor_service()
                async for event in executor.execute_streaming(
                    business_unit_id=business_unit_id,
                    agent_name=agent_name,
                    model_name=model_name,
                    input_text=request.input,
                    context=request.context,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    system_prompt=request.system_prompt,
                ):
                    event_count += 1
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                logger.info(
                    "Completed model streaming for %s/%s/%s with %s event(s)",
                    business_unit_id,
                    agent_name,
                    model_name,
                    event_count,
                )
                emit_runtime_event("model.api.stream.completed", event_count=event_count)
                yield 'data: {"event_type": "done"}\n\n'
            except Exception as exc:
                logger.error(
                    "Failed to stream model %s/%s/%s: %s",
                    business_unit_id,
                    agent_name,
                    model_name,
                    exc,
                    exc_info=True,
                )
                emit_runtime_event(
                    "model.api.stream.failed",
                    level=logging.ERROR,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
                error_event = {
                    "event_type": "error",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\\n\\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}/status", response_model=ModelStatusResponse)
async def get_model_status(business_unit_id: str, agent_name: str, model_name: str, http_request: Request):
    """Return runtime status for a model."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        component="model_runtime_api.status",
    )
    with scoped_logging_context(**operation_context):
        try:
            executor = get_model_executor_service()
            status = await executor.get_status(business_unit_id, agent_name, model_name)
            if not status:
                return ModelStatusResponse(status="not_loaded")
            return ModelStatusResponse(**status)
        except Exception as exc:
            logger.error(
                "Failed to get model status %s/%s/%s: %s",
                business_unit_id,
                agent_name,
                model_name,
                exc,
                exc_info=True,
            )
            emit_runtime_event(
                "model.api.status.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/cancel")
async def cancel_model(business_unit_id: str, agent_name: str, model_name: str, http_request: Request):
    """Cancel an active model execution."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        component="model_runtime_api.cancel",
    )
    with scoped_logging_context(**operation_context):
        try:
            executor = get_model_executor_service()
            success = await executor.cancel(business_unit_id, agent_name, model_name)
            return {
                "message": "Cancelled" if success else "No running execution",
                "success": success,
            }
        except Exception as exc:
            logger.error(
                "Failed to cancel model %s/%s/%s: %s",
                business_unit_id,
                agent_name,
                model_name,
                exc,
                exc_info=True,
            )
            emit_runtime_event(
                "model.api.cancel.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}/unload")
async def unload_model(business_unit_id: str, agent_name: str, model_name: str, http_request: Request):
    """Unload a model runtime."""
    operation_context = _build_request_context(
        http_request=http_request,
        business_unit_id=business_unit_id,
        agent_name=agent_name,
        model_name=model_name,
        component="model_runtime_api.unload",
    )
    with scoped_logging_context(**operation_context):
        try:
            executor = get_model_executor_service()
            success = await executor.cleanup_model(business_unit_id, agent_name, model_name)
            return {
                "message": "Unloaded" if success else "Model not found",
                "success": success,
            }
        except Exception as exc:
            logger.error(
                "Failed to unload model %s/%s/%s: %s",
                business_unit_id,
                agent_name,
                model_name,
                exc,
                exc_info=True,
            )
            emit_runtime_event(
                "model.api.unload.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/models/loaded")
async def list_loaded_models(http_request: Request):
    """Return all loaded models."""
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    with scoped_logging_context(
        request_id=request_id,
        session_id=request_id,
        component="model_runtime_api.list_loaded",
    ):
        try:
            return get_model_executor_service().list_loaded_models()
        except Exception as exc:
            logger.error("Failed to list loaded models: %s", exc, exc_info=True)
            emit_runtime_event(
                "model.api.list_loaded.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc
