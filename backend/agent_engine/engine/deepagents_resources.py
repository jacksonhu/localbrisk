"""Resource tracking helpers for DeepAgents engine."""

from __future__ import annotations

from typing import Any, Dict


class AgentResourceRegistry:
    """Track build-time resources bound to compiled agent instances."""

    def __init__(self):
        self.checkpointer_contexts: Dict[int, Any] = {}
        self.text2sql_services: Dict[int, Any] = {}

    def register(self, agent: Any, checkpointer_context: Any, text2sql_service: Any = None) -> None:
        """Register resources associated with a built agent."""
        self.checkpointer_contexts[id(agent)] = checkpointer_context
        if text2sql_service is not None:
            self.text2sql_services[id(agent)] = text2sql_service
