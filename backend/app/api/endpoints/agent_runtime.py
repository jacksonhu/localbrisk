"""
Agent Runtime API
Provides runtime management endpoints for Agent start, stop, status query, etc.

Uses StreamMessage protocol, supports THOUGHT/TASK_LIST/ARTIFACT/STATUS/ERROR/DONE message packets
"""

import logging
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent_engine.services import get_agent_runtime_service


logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================

class AgentLoadRequest(BaseModel):
    """Load Agent request"""
    business_unit_id: str = Field(..., description="BusinessUnit ID")
    agent_name: str = Field(..., description="Agent name")


class AgentExecuteRequest(BaseModel):
    """Execute Agent request"""
    input: str = Field(..., description="User input")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Execution context")


class LoadResponse(BaseModel):
    """Load response"""
    message: str
    agent_name: str
    business_unit_id: str
    status: str


class StatusResponse(BaseModel):
    """Status response"""
    execution_id: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class CancelResponse(BaseModel):
    """Cancel response"""
    message: str
    success: bool


class UnloadResponse(BaseModel):
    """Unload response"""
    message: str
    success: bool


class ClearContextResponse(BaseModel):
    """Clear context response"""
    message: str
    success: bool


class ConversationHistoryResponse(BaseModel):
    """Conversation history response"""
    agent_name: str
    thread_id: str
    history_file: str
    turns: list[dict[str, Any]]


# ==================== API Endpoints ====================

@router.post("/{business_unit_id}/agents/{agent_name}/load", response_model=LoadResponse)
async def load_agent(business_unit_id: str, agent_name: str):
    """Load Agent"""
    logger.info(f"Loading Agent: {business_unit_id}/{agent_name}")

    try:
        service = get_agent_runtime_service()
        state = await service.load_agent(business_unit_id, agent_name)

        return LoadResponse(
            message=f"Agent {agent_name} loaded successfully",
            agent_name=agent_name,
            business_unit_id=business_unit_id,
            status=state.status.value,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Agent config not found: {e}")
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Missing dependencies: {e}")
    except Exception as e:
        logger.exception(f"Failed to load  Agent failed: {e}")
        raise HTTPException(status_code=500, detail=f"Load Agent failed: {e}")


# ==================== Streaming Endpoints (StreamMessage Protocol) ====================

@router.post("/{business_unit_id}/agents/{agent_name}/execute/stream")
async def execute_agent_streaming(
    business_unit_id: str,
    agent_name: str,
    request: AgentExecuteRequest
):
    """Stream execution of Agent

    Uses StreamMessage protocol, frontend dispatches by type field:
    - THOUGHT  → left thought panel (typewriter effect)
    - TASK_LIST → left task list
    - ARTIFACT → right artifact display
    - STATUS   → transient status hint
    - ERROR    → error message
    - DONE     → execution completed
    """
    logger.info(f"Streaming execution of Agent: {business_unit_id}/{agent_name}")

    async def event_generator():
        try:
            service = get_agent_runtime_service()

            async for message in service.execute_agent_stream(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                user_input=request.input,
                context=request.context,
            ):
                yield message.to_sse()

        except Exception as e:
            logger.exception(f"Streaming execution failed: {e}")
            import time
            error_data = {
                "type": "ERROR",
                "payload": {
                    "message": str(e),
                    "error_type": type(e).__name__,
                    "retryable": True,
                },
                "execution_id": "",
                "timestamp": time.time(),
                "seq": 0,
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== Reconnection Snapshot Endpoints ====================

@router.get("/{business_unit_id}/agents/{agent_name}/execution/{execution_id}/snapshot")
async def get_execution_snapshot(
    business_unit_id: str,
    agent_name: str,
    execution_id: str
):
    """Get execution snapshot (for reconnection)

    Returns full snapshot for specified execution ID, including thought records, task list, and artifacts.
    Frontend calls this endpoint after reconnection to restore state.
    """
    logger.info(f"Fetching execution snapshot: {execution_id}")

    try:
        service = get_agent_runtime_service()
        snapshot = service.get_execution_snapshot(execution_id)

        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"Snapshot not found for execution ID {execution_id} "
            )

        return snapshot

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get snapshot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get snapshot: {e}")


# ==================== Management Endpoints ====================

@router.get("/{business_unit_id}/agents/{agent_name}/status", response_model=StatusResponse)
async def get_agent_status(business_unit_id: str, agent_name: str):
    """Get Agent Execute状态"""
    try:
        service = get_agent_runtime_service()
        status = await service.get_agent_status(business_unit_id, agent_name)

        return StatusResponse(
            execution_id=status.get("execution_id"),
            status=status.get("status", "unknown"),
            started_at=status.get("loaded_at"),
            completed_at=status.get("last_execution_at"),
        )
    except Exception as e:
        logger.exception(f"Failed to get 状态failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get状态failed: {e}")


@router.post("/{business_unit_id}/agents/{agent_name}/cancel", response_model=CancelResponse)
async def cancel_agent(business_unit_id: str, agent_name: str):
    """Cancel Agent execution"""
    logger.info(f"Cancelling Agent execution: {business_unit_id}/{agent_name}")

    try:
        service = get_agent_runtime_service()
        success = await service.cancel_agent(business_unit_id, agent_name)

        return CancelResponse(
            message="cancel request sent" if success else "no running task",
            success=success,
        )
    except Exception as e:
        logger.exception(f"Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {e}")


@router.get("/{business_unit_id}/agents/{agent_name}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    business_unit_id: str,
    agent_name: str,
    thread_id: Optional[str] = Query(default=None, description="Conversation thread ID; defaults to agent_name if not provided"),
):
    """Get Agent 本地会话历史."""
    logger.info(f"Fetching Agent conversation history: {business_unit_id}/{agent_name}, thread_id={thread_id or agent_name}")

    try:
        service = get_agent_runtime_service()
        history = await service.get_conversation_history(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            thread_id=thread_id,
        )
        return ConversationHistoryResponse(**history)
    except Exception as e:
        logger.exception(f"Failed to get  Agent 会话历史failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get Agent 会话历史failed: {e}")


@router.delete("/{business_unit_id}/agents/{agent_name}/context", response_model=ClearContextResponse)
async def clear_agent_context(
    business_unit_id: str,
    agent_name: str,
    thread_id: Optional[str] = Query(default=None, description="Conversation thread ID; defaults to agent_name if not provided"),
):
    """Clear Agent conversation context and local history."""
    logger.info(f"Clearing Agent conversation context: {business_unit_id}/{agent_name}, thread_id={thread_id or agent_name}")

    try:
        service = get_agent_runtime_service()
        success = await service.clear_agent_context(business_unit_id, agent_name, thread_id)

        return ClearContextResponse(
            message="conversation context cleared" if success else "No clearable context found",
            success=success,
        )
    except Exception as e:
        logger.exception(f"清理 Agent 对话Contextfailed: {e}")
        raise HTTPException(status_code=500, detail=f"清理 Agent 对话Contextfailed: {e}")


@router.delete("/{business_unit_id}/agents/{agent_name}/unload", response_model=UnloadResponse)
async def unload_agent(business_unit_id: str, agent_name: str):
    """Unload Agent"""
    logger.info(f"Unloading Agent: {business_unit_id}/{agent_name}")

    try:
        service = get_agent_runtime_service()
        success = await service.unload_agent(business_unit_id, agent_name)

        return UnloadResponse(
            message="Agent unloaded" if success else "Agent not loaded",
            success=success,
        )
    except Exception as e:
        logger.exception(f"卸载 Agent failed: {e}")
        raise HTTPException(status_code=500, detail=f"卸载 Agent failed: {e}")


@router.get("/agents/loaded")
async def list_loaded_agents():
    """List loaded Agents"""
    try:
        service = get_agent_runtime_service()
        agents = service.list_loaded_agents()
        return agents
    except Exception as e:
        logger.exception(f"Failed to get 列表failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get列表failed: {e}")
