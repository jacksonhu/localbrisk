"""Foreman application service — CRUD, directory aggregation, member management.

This is the **application layer** service. It owns:

- Agent directory aggregation (with short TTL cache)
- Conversation create / read / delete
- Member management (add members, upgrade direct → group)

Runtime execution / SSE aggregation lives in
``agent_engine.services.foreman_runtime_service``.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models.foreman import (
    AddMembersRequest,
    ConversationDetail,
    ConversationMember,
    ConversationSummary,
    CreateConversationRequest,
    ForemanAgentInfo,
    TimelineMessage,
)
from app.services.foreman_session_store import ForemanSessionStore, get_foreman_session_store

logger = logging.getLogger(__name__)

# Agent directory cache TTL in seconds.
_AGENT_CACHE_TTL = 30.0


class ForemanService:
    """Foreman application-level service for conversations and directory."""

    def __init__(self) -> None:
        self._store: ForemanSessionStore = get_foreman_session_store()
        # Agent directory cache.
        self._agent_cache: List[ForemanAgentInfo] = []
        self._agent_cache_ts: float = 0.0
        logger.info("ForemanService initialized")

    # ──────────────────── agent directory ────────────────────

    def list_all_agents(self) -> List[ForemanAgentInfo]:
        """Aggregate agents across all business units with TTL caching."""
        now = time.time()
        if self._agent_cache and (now - self._agent_cache_ts) < _AGENT_CACHE_TTL:
            return self._agent_cache

        from app.services import business_unit_service

        agents: List[ForemanAgentInfo] = []
        for bu in business_unit_service.discover_business_units():
            for agent in bu.agents:
                agents.append(
                    ForemanAgentInfo(
                        id=f"{bu.id}/{agent.name}",
                        business_unit_id=bu.id,
                        business_unit_name=bu.display_name or bu.name,
                        name=agent.name,
                        display_name=agent.display_name or agent.name,
                        description=agent.description,
                    )
                )
        agents.sort(key=lambda a: a.display_name.lower())
        self._agent_cache = agents
        self._agent_cache_ts = now
        logger.info("Refreshed Foreman agent directory: %d agent(s)", len(agents))
        return agents

    def _resolve_agent(self, agent_id: str) -> Optional[ForemanAgentInfo]:
        """Resolve an agent_id (``business_unit_id/agent_name``) to its info."""
        for agent in self.list_all_agents():
            if agent.id == agent_id:
                return agent
        return None

    # ──────────────────── conversation CRUD ────────────────────

    def create_conversation(self, request: CreateConversationRequest) -> ConversationDetail:
        """Create a new direct or group conversation."""
        members: List[ConversationMember] = []
        for agent_id in request.agent_ids:
            agent = self._resolve_agent(agent_id)
            if agent is None:
                raise ValueError(f"Agent not found: {agent_id}")
            members.append(
                ConversationMember(
                    business_unit_id=agent.business_unit_id,
                    agent_name=agent.name,
                    display_name=agent.display_name,
                )
            )

        conversation_type = "group" if len(members) > 1 else "direct"
        title = request.title or self._build_title(conversation_type, members)
        now = datetime.now().isoformat()
        conversation_id = str(uuid.uuid4())[:12]

        detail = ConversationDetail(
            conversation_id=conversation_id,
            conversation_type=conversation_type,
            title=title,
            coordinator_enabled=(conversation_type == "group"),
            members=members,
            updated_at=now,
            created_at=now,
        )
        self._store.save_conversation(detail)

        # Write system welcome message.
        if conversation_type == "group":
            names = ", ".join(m.display_name for m in members)
            sys_msg = TimelineMessage(
                conversation_id=conversation_id,
                role="system",
                sender_id="system",
                sender_name="System",
                content=f"Group created with {len(members)} agents: {names}.",
            )
            self._store.append_timeline(conversation_id, sys_msg)
            self._store.update_conversation_preview(conversation_id, sys_msg.content)

        logger.info(
            "Created Foreman conversation: id=%s type=%s members=%d",
            conversation_id, conversation_type, len(members),
        )
        return detail

    def list_conversations(self) -> List[ConversationSummary]:
        return self._store.list_conversations()

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDetail]:
        return self._store.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        return self._store.delete_conversation(conversation_id)

    # ──────────────────── member management ────────────────────

    def add_members(
        self, conversation_id: str, request: AddMembersRequest
    ) -> Optional[ConversationDetail]:
        """Add agents to a conversation. Upgrades direct → group if needed."""
        detail = self._store.get_conversation(conversation_id)
        if detail is None:
            return None

        existing_keys = {(m.business_unit_id, m.agent_name) for m in detail.members}
        new_members: List[ConversationMember] = []

        for agent_id in request.agent_ids:
            agent = self._resolve_agent(agent_id)
            if agent is None:
                raise ValueError(f"Agent not found: {agent_id}")
            key = (agent.business_unit_id, agent.name)
            if key in existing_keys:
                continue
            new_members.append(
                ConversationMember(
                    business_unit_id=agent.business_unit_id,
                    agent_name=agent.name,
                    display_name=agent.display_name,
                )
            )
            existing_keys.add(key)

        if not new_members:
            return detail

        detail.members.extend(new_members)

        # Upgrade direct → group when members exceed 1.
        if detail.conversation_type == "direct" and len(detail.members) > 1:
            detail.conversation_type = "group"
            detail.coordinator_enabled = True
            detail.title = self._build_title("group", detail.members)

        detail.updated_at = datetime.now().isoformat()
        self._store.save_conversation(detail)

        # Write system message about new members.
        added_names = ", ".join(m.display_name for m in new_members)
        sys_msg = TimelineMessage(
            conversation_id=conversation_id,
            role="system",
            sender_id="system",
            sender_name="System",
            content=f"{added_names} joined the conversation.",
        )
        self._store.append_timeline(conversation_id, sys_msg)
        self._store.update_conversation_preview(conversation_id, sys_msg.content)

        logger.info(
            "Added %d member(s) to conversation %s (type=%s)",
            len(new_members), conversation_id, detail.conversation_type,
        )
        return detail

    # ──────────────────── helpers ────────────────────

    @staticmethod
    def _build_title(
        conversation_type: str,
        members: List[ConversationMember],
    ) -> str:
        names = [m.display_name for m in members]
        if conversation_type == "direct" or len(names) == 1:
            return names[0] if names else "Untitled"
        if len(names) <= 3:
            return " · ".join(names)
        return f"{' · '.join(names[:2])} +{len(names) - 2}"


# ──────────────────── singleton accessor ────────────────────

_service_instance: Optional[ForemanService] = None


def get_foreman_service() -> ForemanService:
    """Return the global ForemanService singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ForemanService()
    return _service_instance
