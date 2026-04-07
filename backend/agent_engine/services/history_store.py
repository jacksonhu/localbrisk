"""Conversation history persistence for agent runtime."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class ConversationHistoryStore:
    """Persist and retrieve agent conversation history files."""

    def __init__(self, agent_path_resolver: Callable[[str, str], Path]):
        self._agent_path_resolver = agent_path_resolver

    @staticmethod
    def _sanitize_file_segment(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", value or "")
        return cleaned.strip("._") or "default"

    def get_history_file_path(self, business_unit_id: str, agent_name: str, thread_id: str) -> Path:
        """Return the history markdown path for a thread."""
        agent_path = self._agent_path_resolver(business_unit_id, agent_name)
        history_dir = agent_path / "output" / ".chathistory"
        history_dir.mkdir(parents=True, exist_ok=True)
        safe_agent_name = self._sanitize_file_segment(agent_name)
        safe_thread_id = self._sanitize_file_segment(thread_id)
        return history_dir / f"{safe_agent_name}_{safe_thread_id}.md"

    @staticmethod
    def build_default_history(agent_name: str, thread_id: str) -> Dict[str, Any]:
        """Build an empty history document payload."""
        return {
            "version": 1,
            "agent_name": agent_name,
            "thread_id": thread_id,
            "turns": [],
        }

    def read_history_doc(self, history_file: Path, agent_name: str, thread_id: str) -> Dict[str, Any]:
        """Read a history markdown file and return the embedded JSON payload."""
        if not history_file.exists():
            return self.build_default_history(agent_name, thread_id)

        try:
            content = history_file.read_text(encoding="utf-8")
            start_marker = "<!-- LOCALBRISK_CHAT_HISTORY_JSON_BEGIN -->"
            end_marker = "<!-- LOCALBRISK_CHAT_HISTORY_JSON_END -->"
            start = content.find(start_marker)
            end = content.find(end_marker)
            if start == -1 or end == -1 or end <= start:
                return self.build_default_history(agent_name, thread_id)

            json_text = content[start + len(start_marker):end].strip()
            parsed = json.loads(json_text) if json_text else {}
            if not isinstance(parsed, dict):
                return self.build_default_history(agent_name, thread_id)

            turns = parsed.get("turns")
            if not isinstance(turns, list):
                parsed["turns"] = []
            parsed.setdefault("version", 1)
            parsed.setdefault("agent_name", agent_name)
            parsed.setdefault("thread_id", thread_id)
            return parsed
        except Exception as exc:
            logger.warning("Failed to read history file %s, resetting content: %s", history_file, exc)
            return self.build_default_history(agent_name, thread_id)

    @staticmethod
    def render_history_markdown(history: Dict[str, Any]) -> str:
        """Render the history payload into a markdown container."""
        turns = history.get("turns") if isinstance(history, dict) else []
        turns = turns if isinstance(turns, list) else []
        return "\n".join(
            [
                "# LocalBrisk Agent Chat History",
                "",
                f"- agent_name: {history.get('agent_name', '')}",
                f"- thread_id: {history.get('thread_id', '')}",
                f"- turns: {len(turns)}",
                "",
                "<!-- LOCALBRISK_CHAT_HISTORY_JSON_BEGIN -->",
                json.dumps(history, ensure_ascii=False, indent=2),
                "<!-- LOCALBRISK_CHAT_HISTORY_JSON_END -->",
                "",
            ]
        )

    def write_history_doc(self, history_file: Path, history: Dict[str, Any]) -> None:
        """Write a history payload to a markdown file."""
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(self.render_history_markdown(history), encoding="utf-8")

    def persist_history_turn(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: str,
        user_input: str,
        stream_messages: List[Dict[str, Any]],
    ) -> None:
        """Append a conversation turn to the history file."""
        history_file = self.get_history_file_path(business_unit_id, agent_name, thread_id)
        history = self.read_history_doc(history_file, agent_name, thread_id)
        turns = history.get("turns")
        if not isinstance(turns, list):
            turns = []
            history["turns"] = turns

        turns.append(
            {
                "created_at": datetime.now().isoformat(),
                "user_input": user_input,
                "messages": stream_messages,
            }
        )
        self.write_history_doc(history_file, history)

    def get_conversation_history(self, business_unit_id: str, agent_name: str, thread_id: str) -> Dict[str, Any]:
        """Load conversation history for a specific thread."""
        history_file = self.get_history_file_path(business_unit_id, agent_name, thread_id)
        history = self.read_history_doc(history_file, agent_name, thread_id)
        return {
            "agent_name": agent_name,
            "thread_id": thread_id,
            "history_file": history_file.name,
            "turns": history.get("turns", []),
        }

    def clear_history(self, business_unit_id: str, agent_name: str, thread_id: str) -> bool:
        """Delete the local history file if it exists."""
        history_file = self.get_history_file_path(business_unit_id, agent_name, thread_id)
        if not history_file.exists():
            return True
        history_file.unlink()
        return True
