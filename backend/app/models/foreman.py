"""Foreman conversation models.

Defines the data contracts for Foreman multi-agent chat: conversations,
members, timeline messages, and request/response schemas used by the
``/api/foreman`` endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# Agent directory item (returned by GET /api/foreman/agents)
# ============================================================

class ForemanAgentInfo(BaseModel):
    """Lightweight agent descriptor for the Foreman directory listing."""

    id: str = Field(..., description="Unique agent identifier (business_unit_id + agent_name)")
    business_unit_id: str
    business_unit_name: str
    name: str = Field(..., description="Agent directory name")
    display_name: str
    description: Optional[str] = None


# ============================================================
# Conversation member
# ============================================================

class ConversationMember(BaseModel):
    """One agent member inside a Foreman conversation."""

    member_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    business_unit_id: str
    agent_name: str
    display_name: str
    joined_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# Conversation models
# ============================================================

class ConversationSummary(BaseModel):
    """Lightweight conversation descriptor for the session list."""

    conversation_id: str
    conversation_type: Literal["direct", "group"] = "direct"
    title: str
    last_message_preview: str = ""
    member_count: int = 1
    updated_at: str = ""
    created_at: str = ""


class ConversationDetail(BaseModel):
    """Full conversation payload including members."""

    conversation_id: str
    conversation_type: Literal["direct", "group"] = "direct"
    title: str
    last_message_preview: str = ""
    coordinator_enabled: bool = False
    members: List[ConversationMember] = Field(default_factory=list)
    updated_at: str = ""
    created_at: str = ""


# ============================================================
# Timeline message
# ============================================================

class TimelineMessage(BaseModel):
    """One entry in the unified conversation timeline."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    conversation_id: str
    round_id: Optional[str] = None
    role: Literal["user", "agent", "system"] = "user"
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    mentioned_agents: Optional[List[str]] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# Request schemas
# ============================================================

class CreateConversationRequest(BaseModel):
    """Create a new single-chat or group-chat conversation."""

    agent_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of agent identifiers (business_unit_id/agent_name format)",
    )
    title: Optional[str] = None


class AddMembersRequest(BaseModel):
    """Add one or more agents to an existing conversation."""

    agent_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Agent identifiers to add",
    )


class SendMessageRequest(BaseModel):
    """User message sent into a conversation stream."""

    content: str = Field(..., min_length=1)
    mentions: Optional[List[str]] = None


# ============================================================
# Response helpers
# ============================================================

class ConversationListResponse(BaseModel):
    """Wrapper for the conversation list endpoint."""

    conversations: List[ConversationSummary]


class TimelineResponse(BaseModel):
    """Paginated timeline response."""

    conversation_id: str
    messages: List[TimelineMessage]
    total: int = 0
