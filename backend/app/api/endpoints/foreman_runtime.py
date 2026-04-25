"""Foreman REST and SSE endpoints.

Provides the ``/api/foreman`` route group for multi-agent conversation
management, agent directory listing, member management, timeline retrieval,
and streaming message execution.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.foreman import (
    AddMembersRequest,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    CreateConversationRequest,
    ForemanAgentInfo,
    SendMessageRequest,
    TimelineResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────── lazy service accessors ────────────────────

def _get_foreman_service():
    from app.services.foreman_service import get_foreman_service
    return get_foreman_service()


def _get_foreman_runtime_service():
    from agent_engine.services.foreman_runtime_service import get_foreman_runtime_service
    return get_foreman_runtime_service()


# ──────────────────── agent directory ────────────────────

@router.get("/agents", response_model=list[ForemanAgentInfo])
async def list_foreman_agents():
    """Return the full agent directory across all business units."""
    try:
        service = _get_foreman_service()
        return service.list_all_agents()
    except Exception as exc:
        logger.exception("Failed to list Foreman agents: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {exc}")


# ──────────────────── conversation CRUD ────────────────────

@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(request: CreateConversationRequest):
    """Create a direct or group conversation."""
    try:
        service = _get_foreman_service()
        return service.create_conversation(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to create conversation: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {exc}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations():
    """Return all Foreman conversations (lightweight summaries)."""
    try:
        service = _get_foreman_service()
        summaries = service.list_conversations()
        return ConversationListResponse(conversations=summaries)
    except Exception as exc:
        logger.exception("Failed to list conversations: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {exc}")


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """Return conversation details including members."""
    try:
        service = _get_foreman_service()
        detail = service.get_conversation(conversation_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return detail
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {exc}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and its timeline data."""
    try:
        service = _get_foreman_service()
        if not service.delete_conversation(conversation_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted", "success": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete conversation %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {exc}")


# ──────────────────── member management ────────────────────

@router.post("/conversations/{conversation_id}/members", response_model=ConversationDetail)
async def add_members(conversation_id: str, request: AddMembersRequest):
    """Add agents to a conversation. Upgrades direct chat to group if needed."""
    try:
        service = _get_foreman_service()
        detail = service.add_members(conversation_id, request)
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return detail
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to add members to %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to add members: {exc}")


# ──────────────────── timeline ────────────────────

@router.get("/conversations/{conversation_id}/messages", response_model=TimelineResponse)
async def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Return paginated timeline messages for a conversation."""
    try:
        service = _get_foreman_service()
        detail = service.get_conversation(conversation_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        from app.services.foreman_session_store import get_foreman_session_store
        store = get_foreman_session_store()
        messages = store.read_timeline(conversation_id, limit=limit, offset=offset)
        total = store.count_timeline(conversation_id)
        return TimelineResponse(conversation_id=conversation_id, messages=messages, total=total)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get messages for %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {exc}")


# ──────────────────── streaming execution ────────────────────

@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """Send a user message and stream back agent responses via SSE."""
    logger.info("Foreman stream request for conversation %s", conversation_id)

    service = _get_foreman_service()
    detail = service.get_conversation(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    runtime = _get_foreman_runtime_service()

    async def event_generator():
        try:
            async for message in runtime.execute_round(
                conversation=detail,
                user_input=request.content,
                mentions=request.mentions,
            ):
                yield message.to_sse()
        except Exception as exc:
            logger.exception("Foreman streaming failed for %s: %s", conversation_id, exc)
            error_data = {
                "type": "ERROR",
                "payload": {
                    "message": str(exc),
                    "error_type": type(exc).__name__,
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


# ──────────────────── context management ────────────────────

@router.delete("/conversations/{conversation_id}/context")
async def clear_conversation_context(conversation_id: str):
    """Clear runtime context for all members in a conversation."""
    try:
        service = _get_foreman_service()
        detail = service.get_conversation(conversation_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        runtime = _get_foreman_runtime_service()
        results = await runtime.clear_member_contexts(detail)
        return {"message": "Context cleared", "results": results}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to clear context for %s: %s", conversation_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to clear context: {exc}")
