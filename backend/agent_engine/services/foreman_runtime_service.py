"""Foreman runtime service — execution orchestration and SSE aggregation.

This is the **engine layer** service. It owns:

- Rule-based coordinator (agent routing per round)
- Context prefix injection (recent timeline → user_input enrichment)
- Serial member execution via ``AgentRuntimeService.execute_agent_stream()``
- SSE middle-consumer: consumes single-agent ``StreamMessage``, writes to
  the unified timeline, injects ``agent_name`` into payload, and re-yields
  with Foreman envelope events (``round_started`` / ``member_started`` /
  ``member_done`` / ``round_completed``).

Thread sharing: Foreman does **not** pass ``thread_id`` in ``context``,
so each member Agent falls back to its default ``agent_name`` thread.
This means Foreman conversations and AgentChat share the same runtime
session / history for each Agent.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from ..core.stream_protocol import (
    MessageType,
    StreamMessage,
    StreamMessageBuilder,
)

logger = logging.getLogger(__name__)

# Maximum number of recent timeline messages injected as context prefix.
_CONTEXT_PREFIX_LIMIT = 10
# Maximum character length for the context prefix block.
_CONTEXT_PREFIX_MAX_CHARS = 4096


class ForemanRuntimeService:
    """Orchestrate multi-agent execution rounds for Foreman conversations."""

    def __init__(self) -> None:
        self._runtime = None
        logger.info("ForemanRuntimeService initialized")

    # ──────────────────── lazy runtime accessor ────────────────────

    def _get_runtime(self):
        """Return the shared AgentRuntimeService singleton."""
        if self._runtime is None:
            from .agent_runtime_service import get_agent_runtime_service
            self._runtime = get_agent_runtime_service()
        return self._runtime

    # ──────────────────── SSE envelope helpers ────────────────────

    @staticmethod
    def _foreman_event(
        builder: StreamMessageBuilder,
        event_kind: str,
        *,
        round_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        text: Optional[str] = None,
    ) -> StreamMessage:
        """Build a Foreman envelope event using the STATUS message type."""
        status_text = text or event_kind.replace("_", " ").capitalize()
        msg = builder.status(text=status_text, icon="foreman")
        # Inject Foreman-specific fields into the payload dict.
        msg.payload["event_kind"] = event_kind
        if round_id:
            msg.payload["round_id"] = round_id
        if agent_name:
            msg.payload["agent_name"] = agent_name
        return msg

    # ──────────────────── rule-based coordinator ────────────────────

    @staticmethod
    def _select_agents(
        members: list,
        mentions: Optional[List[str]],
    ) -> list:
        """Select which members to execute in this round.

        MVP rules:
        - If mentions provided, select mentioned members first.
        - Otherwise, select the first member (direct chat) or first member for
          group chat as the default responder.
        """
        if not members:
            return []

        if mentions:
            mentioned = [m for m in members if m.agent_name in mentions]
            if mentioned:
                return mentioned

        # Default: first member answers.
        return [members[0]]

    # ──────────────────── context prefix builder ────────────────────

    def _build_context_prefix(
        self,
        conversation_id: str,
        user_input: str,
    ) -> str:
        """Prepend recent timeline context to the user input.

        This gives the member Agent awareness of the broader conversation
        without modifying its underlying thread history.
        """
        from app.services.foreman_session_store import get_foreman_session_store
        store = get_foreman_session_store()

        messages = store.read_timeline(conversation_id, limit=_CONTEXT_PREFIX_LIMIT)
        if not messages:
            return user_input

        # Build a compact context block.
        lines: List[str] = ["[Recent conversation context]"]
        total_chars = 0
        for msg in messages:
            line = f"{msg.sender_name} ({msg.role}): {msg.content}"
            if total_chars + len(line) > _CONTEXT_PREFIX_MAX_CHARS:
                break
            lines.append(line)
            total_chars += len(line)

        if len(lines) <= 1:
            return user_input

        lines.append("[End of context]")
        lines.append("")
        lines.append(user_input)
        return "\n".join(lines)

    # ──────────────────── main execution round ────────────────────

    async def execute_round(
        self,
        conversation,
        user_input: str,
        mentions: Optional[List[str]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """Execute one user message round across selected members.

        Yields Foreman envelope events and member Agent StreamMessages.
        Writes all messages to the unified timeline.
        """
        from app.services.foreman_session_store import get_foreman_session_store
        store = get_foreman_session_store()

        conversation_id = conversation.conversation_id
        round_id = str(uuid.uuid4())[:8]
        builder = StreamMessageBuilder(execution_id=f"fm_{round_id}")

        # 1. Write user message to timeline.
        from app.models.foreman import TimelineMessage
        user_msg = TimelineMessage(
            conversation_id=conversation_id,
            round_id=round_id,
            role="user",
            sender_id="user",
            sender_name="You",
            content=user_input,
            mentioned_agents=mentions,
        )
        store.append_timeline(conversation_id, user_msg)
        store.update_conversation_preview(conversation_id, user_input)

        # 2. Select members for this round.
        selected = self._select_agents(conversation.members, mentions)
        if not selected:
            yield self._foreman_event(builder, "round_completed", round_id=round_id, text="No agents available")
            return

        # 3. Round started envelope.
        yield self._foreman_event(builder, "round_started", round_id=round_id)

        runtime = self._get_runtime()

        # 4. Execute each selected member serially.
        for member in selected:
            yield self._foreman_event(
                builder, "member_started",
                round_id=round_id, agent_name=member.agent_name,
            )

            # Build enriched input with conversation context for group chats.
            enriched_input = user_input
            if conversation.conversation_type == "group":
                enriched_input = self._build_context_prefix(conversation_id, user_input)

            # Accumulate agent final output for timeline persistence.
            accumulated_content = ""
            member_done_type_seen = False

            try:
                async for msg in runtime.execute_agent_stream(
                    business_unit_id=member.business_unit_id,
                    agent_name=member.agent_name,
                    user_input=enriched_input,
                    # NOTE: no thread_id → defaults to agent_name (shared with AgentChat)
                ):
                    # Inject Foreman routing fields.
                    msg.payload["agent_name"] = member.agent_name
                    msg.payload["conversation_id"] = conversation_id
                    msg.payload["round_id"] = round_id

                    # Accumulate thought content for the timeline record.
                    if msg.type == MessageType.THOUGHT:
                        content = msg.payload.get("content", "")
                        mode = msg.payload.get("mode", "append")
                        if mode == "replace":
                            accumulated_content = content
                        else:
                            accumulated_content += content

                    # Track DONE to know execution finished.
                    if msg.type == MessageType.DONE:
                        member_done_type_seen = True

                    yield msg

            except Exception as exc:
                logger.error(
                    "Foreman member execution failed: conversation=%s agent=%s error=%s",
                    conversation_id, member.agent_name, exc,
                )
                # Yield an error event and continue to next member.
                yield builder.error(
                    message=f"Agent {member.display_name} execution failed: {exc}",
                    error_type=type(exc).__name__,
                    retryable=True,
                )

            # Write agent response to unified timeline.
            if accumulated_content.strip():
                agent_msg = TimelineMessage(
                    conversation_id=conversation_id,
                    round_id=round_id,
                    role="agent",
                    sender_id=member.agent_name,
                    sender_name=member.display_name,
                    content=accumulated_content.strip(),
                )
                store.append_timeline(conversation_id, agent_msg)
                store.update_conversation_preview(conversation_id, accumulated_content.strip()[:120])

            yield self._foreman_event(
                builder, "member_done",
                round_id=round_id, agent_name=member.agent_name,
            )

        # 5. Round completed envelope.
        yield self._foreman_event(builder, "round_completed", round_id=round_id)

    # ──────────────────── context management ────────────────────

    async def clear_member_contexts(self, conversation) -> List[Dict[str, Any]]:
        """Clear runtime context for all members in a conversation."""
        runtime = self._get_runtime()
        results = []
        for member in conversation.members:
            try:
                success = await runtime.clear_agent_context(
                    member.business_unit_id,
                    member.agent_name,
                )
                results.append({
                    "agent_name": member.agent_name,
                    "success": success,
                })
            except Exception as exc:
                logger.warning(
                    "Failed to clear context for %s: %s", member.agent_name, exc,
                )
                results.append({
                    "agent_name": member.agent_name,
                    "success": False,
                    "error": str(exc),
                })
        return results


# ──────────────────── singleton accessor ────────────────────

_runtime_service_instance: Optional[ForemanRuntimeService] = None


def get_foreman_runtime_service() -> ForemanRuntimeService:
    """Return the global ForemanRuntimeService singleton."""
    global _runtime_service_instance
    if _runtime_service_instance is None:
        _runtime_service_instance = ForemanRuntimeService()
    return _runtime_service_instance
