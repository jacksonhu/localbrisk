"""Foreman session file storage.

Persists Foreman conversation metadata and unified timeline under
``settings.DATA_DIR / 'foreman'``.

Storage layout::

    ~/.localbrisk/data/foreman/
        index.json                          # lightweight session index
        sessions/
            {conversation_id}/
                meta.json                   # full conversation metadata + members
                messages.jsonl              # append-only unified timeline
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.foreman import (
    ConversationDetail,
    ConversationMember,
    ConversationSummary,
    TimelineMessage,
)

logger = logging.getLogger(__name__)

_FOREMAN_ROOT_NAME = "foreman"
_INDEX_FILE = "index.json"
_META_FILE = "meta.json"
_MESSAGES_FILE = "messages.jsonl"


class ForemanSessionStore:
    """File-backed storage for Foreman conversations and timelines."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or (settings.DATA_DIR / _FOREMAN_ROOT_NAME)
        self._sessions_dir = self._base_dir / "sessions"
        self._index_path = self._base_dir / _INDEX_FILE
        self._ensure_dirs()
        logger.info("ForemanSessionStore initialized at %s", self._base_dir)

    # ──────────────────── directory helpers ────────────────────

    def _ensure_dirs(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, conversation_id: str) -> Path:
        return self._sessions_dir / conversation_id

    def _meta_path(self, conversation_id: str) -> Path:
        return self._session_dir(conversation_id) / _META_FILE

    def _messages_path(self, conversation_id: str) -> Path:
        return self._session_dir(conversation_id) / _MESSAGES_FILE

    # ──────────────────── index operations ────────────────────

    def _read_index(self) -> List[Dict[str, Any]]:
        """Read the lightweight session index."""
        if not self._index_path.exists():
            return []
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("Failed to read Foreman index, resetting: %s", exc)
            return []

    def _write_index(self, entries: List[Dict[str, Any]]) -> None:
        self._index_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _upsert_index_entry(self, summary: ConversationSummary) -> None:
        """Insert or update one entry in the index."""
        entries = self._read_index()
        updated = False
        payload = summary.model_dump()
        for i, entry in enumerate(entries):
            if entry.get("conversation_id") == summary.conversation_id:
                entries[i] = payload
                updated = True
                break
        if not updated:
            entries.insert(0, payload)
        self._write_index(entries)

    def _remove_index_entry(self, conversation_id: str) -> None:
        entries = [e for e in self._read_index() if e.get("conversation_id") != conversation_id]
        self._write_index(entries)

    # ──────────────────── conversation CRUD ────────────────────

    def list_conversations(self) -> List[ConversationSummary]:
        """Return all conversation summaries sorted by updated_at desc."""
        entries = self._read_index()
        summaries = []
        for entry in entries:
            try:
                summaries.append(ConversationSummary(**entry))
            except Exception:
                continue
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def get_conversation(self, conversation_id: str) -> Optional[ConversationDetail]:
        """Load full conversation detail from meta.json."""
        meta_path = self._meta_path(conversation_id)
        if not meta_path.exists():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return ConversationDetail(**data)
        except Exception as exc:
            logger.warning("Failed to load conversation %s: %s", conversation_id, exc)
            return None

    def save_conversation(self, detail: ConversationDetail) -> None:
        """Persist conversation detail and update the index."""
        session_dir = self._session_dir(detail.conversation_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self._meta_path(detail.conversation_id)
        meta_path.write_text(
            json.dumps(detail.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = ConversationSummary(
            conversation_id=detail.conversation_id,
            conversation_type=detail.conversation_type,
            title=detail.title,
            last_message_preview=detail.last_message_preview,
            member_count=len(detail.members),
            updated_at=detail.updated_at,
            created_at=detail.created_at,
        )
        self._upsert_index_entry(summary)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Remove a conversation and its data from disk."""
        session_dir = self._session_dir(conversation_id)
        if not session_dir.exists():
            return False
        import shutil
        shutil.rmtree(session_dir, ignore_errors=True)
        self._remove_index_entry(conversation_id)
        logger.info("Deleted Foreman conversation: %s", conversation_id)
        return True

    # ──────────────────── timeline operations ────────────────────

    def append_timeline(self, conversation_id: str, message: TimelineMessage) -> None:
        """Append one message to the JSONL timeline (append-only)."""
        messages_path = self._messages_path(conversation_id)
        messages_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(message.model_dump(), ensure_ascii=False) + "\n"
        with open(messages_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_timeline(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TimelineMessage]:
        """Read paginated timeline messages (newest-appended order)."""
        messages_path = self._messages_path(conversation_id)
        if not messages_path.exists():
            return []
        lines = messages_path.read_text(encoding="utf-8").strip().splitlines()
        # Apply pagination on the full list (oldest first).
        page = lines[offset : offset + limit]
        result: List[TimelineMessage] = []
        for line in page:
            try:
                result.append(TimelineMessage(**json.loads(line)))
            except Exception:
                continue
        return result

    def count_timeline(self, conversation_id: str) -> int:
        """Return the total number of timeline messages."""
        messages_path = self._messages_path(conversation_id)
        if not messages_path.exists():
            return 0
        return sum(1 for _ in open(messages_path, encoding="utf-8") if _.strip())

    def update_conversation_preview(self, conversation_id: str, preview: str) -> None:
        """Update the last_message_preview and updated_at on an existing conversation."""
        detail = self.get_conversation(conversation_id)
        if detail is None:
            return
        detail.last_message_preview = preview[:120] if preview else ""
        detail.updated_at = datetime.now().isoformat()
        self.save_conversation(detail)


# ──────────────────── singleton accessor ────────────────────

_store_instance: Optional[ForemanSessionStore] = None


def get_foreman_session_store() -> ForemanSessionStore:
    """Return the global ForemanSessionStore singleton."""
    global _store_instance
    if _store_instance is None:
        _store_instance = ForemanSessionStore()
    return _store_instance
