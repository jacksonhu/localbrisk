"""
Agent persisted task board.

Lightweight task storage based on `output/.task/task_<id>.json`.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


_ALLOWED_STATUS = {"pending", "in_progress", "completed", "deleted"}


@dataclass
class ProjectTaskBoard:
    """Persisted task board."""

    root: Path
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def _next_id(self) -> int:
        ids: list[int] = []
        for fp in self.root.glob("task_*.json"):
            try:
                ids.append(int(fp.stem.split("_")[1]))
            except (IndexError, ValueError):
                continue
        return (max(ids) if ids else 0) + 1

    def _path(self, task_id: int) -> Path:
        if task_id <= 0:
            raise ValueError("task_id must be positive")
        return self.root / f"task_{task_id}.json"

    def _load(self, task_id: int) -> dict[str, Any]:
        fp = self._path(task_id)
        if not fp.exists():
            raise ValueError(f"task {task_id} not found")
        return json.loads(fp.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        task_id = int(data["id"])
        fp = self._path(task_id)
        tmp_fp = fp.with_suffix(".json.tmp")
        tmp_fp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_fp.replace(fp)

    def create(self, subject: str, description: str = "") -> str:
        subject = (subject or "").strip()
        if not subject:
            raise ValueError("subject is required")
        if len(subject) > 200:
            raise ValueError("subject too long")

        with self._lock:
            task = {
                "id": self._next_id(),
                "subject": subject,
                "description": (description or "").strip(),
                "status": "pending",
                "owner": None,
                "blockedBy": [],
                "blocks": [],
            }
            self._save(task)
        return json.dumps(task, ensure_ascii=False, indent=2)

    def get(self, task_id: int) -> str:
        task = self._load(task_id)
        return json.dumps(task, ensure_ascii=False, indent=2)

    def update(
        self,
        task_id: int,
        status: Optional[str] = None,
        add_blocked_by: Optional[list[int]] = None,
        add_blocks: Optional[list[int]] = None,
    ) -> str:
        with self._lock:
            task = self._load(task_id)

            if status:
                normalized = status.lower()
                if normalized not in _ALLOWED_STATUS:
                    raise ValueError(f"invalid status: {status}")
                task["status"] = normalized

                if normalized == "completed":
                    for fp in self.root.glob("task_*.json"):
                        t = json.loads(fp.read_text(encoding="utf-8"))
                        if task_id in t.get("blockedBy", []):
                            t["blockedBy"] = [x for x in t["blockedBy"] if x != task_id]
                            self._save(t)

                if normalized == "deleted":
                    self._path(task_id).unlink(missing_ok=True)
                    return f"Task {task_id} deleted"

            if add_blocked_by:
                valid_ids = sorted({int(x) for x in add_blocked_by if int(x) > 0})
                task["blockedBy"] = sorted(set(task.get("blockedBy", []) + valid_ids))

            if add_blocks:
                valid_ids = sorted({int(x) for x in add_blocks if int(x) > 0})
                task["blocks"] = sorted(set(task.get("blocks", []) + valid_ids))

            self._save(task)

        return json.dumps(task, ensure_ascii=False, indent=2)

    def claim(self, task_id: int, owner: str = "lead") -> str:
        owner = (owner or "").strip() or "lead"
        if len(owner) > 64:
            raise ValueError("owner too long")

        with self._lock:
            task = self._load(task_id)
            task["owner"] = owner
            task["status"] = "in_progress"
            self._save(task)

        return f"Claimed task #{task_id} for {owner}"

    def list_all(self) -> str:
        items = []
        for fp in sorted(self.root.glob("task_*.json")):
            items.append(json.loads(fp.read_text(encoding="utf-8")))

        if not items:
            return "No tasks."

        lines = []
        for t in items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[x]",
                "deleted": "[-]",
            }.get(t.get("status", ""), "[?]")
            owner = f" @{t['owner']}" if t.get("owner") else ""
            blocked = f" blocked_by={t['blockedBy']}" if t.get("blockedBy") else ""
            lines.append(f"{marker} #{t['id']}: {t.get('subject', '')}{owner}{blocked}")
        return "\n".join(lines)
