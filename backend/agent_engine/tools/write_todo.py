"""Batch todo planning tool integrated with the persisted task board.

Provides :class:`WriteTodoTool` — a single-call tool that lets the agent
plan, create, and update multiple todo items at once.  Designed to be
invoked **early** when the agent receives a complex, multi-step request,
so it can lay out a structured plan before starting execution.

On-disk persistence is delegated to :class:`ProjectTaskBoard`; each todo
item maps 1-to-1 to a ``task_<id>.json`` file under ``output/.task/``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .task_board import ProjectTaskBoard

logger = logging.getLogger(__name__)


# ─────────────────────── input schema ───────────────────────

class TodoItem(BaseModel):
    """A single todo entry in a write_todo call."""

    id: Optional[int] = Field(
        default=None,
        description=(
            "Task ID. Leave empty (null) to auto-create a new task. "
            "Provide an existing ID to update that task's status."
        ),
    )
    content: str = Field(
        description="Short, actionable description of the task (max 200 chars).",
    )
    status: str = Field(
        default="pending",
        description="Task status: pending | in_progress | completed | deleted.",
    )


class WriteTodoInput(BaseModel):
    """Input schema for the write_todo tool."""

    todos: List[TodoItem] = Field(
        description=(
            "List of todo items to create or update. "
            "Items without an id are created; items with an existing id are updated."
        ),
    )
    merge: bool = Field(
        default=True,
        description=(
            "When true (default), the provided items are merged into the "
            "existing todo list — only the specified items are touched. "
            "When false, all existing tasks are marked deleted first, "
            "then the provided items become the new complete list."
        ),
    )


# ─────────────────────── tool description ───────────────────────

_DESCRIPTION = (
    "Plan and track tasks using a structured todo list. "
    "**When you receive a complex, multi-step request, call this tool FIRST "
    "to break the work into clear, actionable items before starting execution.** "
    "Each item is persisted and can be updated as you make progress.\n\n"
    "Usage patterns:\n"
    "- Planning: call with merge=false and a full list of new items to replace the board.\n"
    "- Progress update: call with merge=true and only the items whose status changed.\n"
    "- Batch create + start: set the first item to in_progress, rest to pending.\n\n"
    "Rules:\n"
    "- Only ONE item should be in_progress at a time.\n"
    "- Mark items completed IMMEDIATELY after finishing them.\n"
    "- Keep content concise and user-facing (avoid internal implementation details)."
)


# ─────────────────────── tool implementation ───────────────────────

class WriteTodoTool(BaseTool):
    """Batch todo planning tool backed by ProjectTaskBoard."""

    name: str = "write_todo"
    description: str = _DESCRIPTION
    args_schema: Type[BaseModel] = WriteTodoInput

    _board: Any = None

    def _ensure_board(self) -> ProjectTaskBoard:
        if self._board is None:
            raise RuntimeError("Task board is not initialized")
        return self._board

    def _run(self, todos: List[dict], merge: bool = True) -> str:
        return self._execute(todos, merge)

    async def _arun(self, todos: List[dict], merge: bool = True) -> str:
        return await asyncio.to_thread(self._execute, todos, merge)

    def _execute(self, todos: List[Any], merge: bool) -> str:
        """Core logic: reconcile the provided todo items against the board."""
        board = self._ensure_board()

        # Normalize raw dicts / TodoItem instances into a uniform list.
        items = _normalize_items(todos)
        if not items:
            return "❌ todos list cannot be empty."

        # When merge=false, mark all existing tasks as deleted first.
        if not merge:
            self._clear_board(board)

        results: List[dict[str, Any]] = []
        for item in items:
            try:
                result = self._upsert_item(board, item)
                results.append(result)
            except Exception as exc:
                logger.warning("Failed to process todo item %s: %s", item, exc)
                results.append({"error": str(exc), "input": item})

        return self._format_output(results)

    # ─────────────── internal helpers ───────────────

    def _clear_board(self, board: ProjectTaskBoard) -> None:
        """Mark every existing task as deleted (used when merge=false)."""
        for fp in sorted(board.root.glob("task_*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                task_id = int(data["id"])
                if data.get("status") != "deleted":
                    board.update(task_id, status="deleted")
            except Exception as exc:
                logger.debug("Skipping task file %s during clear: %s", fp.name, exc)

    def _upsert_item(self, board: ProjectTaskBoard, item: dict[str, Any]) -> dict[str, Any]:
        """Create or update a single todo item on the board."""
        task_id = item.get("id")
        content = item.get("content", "")
        status = item.get("status", "pending")

        if task_id is not None:
            # Update existing task.
            raw = board.update(task_id, status=status)
            result = json.loads(raw) if raw.startswith("{") else {"id": task_id, "status": status, "message": raw}
            result["action"] = "updated"
            return result

        # Create new task.
        raw = board.create(subject=content)
        result = json.loads(raw)
        new_id = result["id"]

        # If the caller requested a non-default status, apply it immediately.
        if status and status != "pending":
            board.update(new_id, status=status)
            result["status"] = status

        result["action"] = "created"
        return result

    @staticmethod
    def _format_output(results: List[dict[str, Any]]) -> str:
        """Build a concise, human-readable summary of all operations."""
        if not results:
            return "No items processed."

        lines: List[str] = []
        for r in results:
            if "error" in r:
                lines.append(f"  ❌ Error: {r['error']}")
                continue
            action = r.get("action", "processed")
            task_id = r.get("id", "?")
            status = r.get("status", "?")
            subject = r.get("subject", "")
            marker = _status_marker(status)
            lines.append(f"  {marker} #{task_id}: {subject} ({action})")

        header = f"Todo list updated — {len(results)} item(s):"
        return "\n".join([header, *lines])


# ─────────────────────── module-level helpers ───────────────────────

_STATUS_MARKERS = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "completed": "[x]",
    "deleted": "[-]",
}


def _status_marker(status: str) -> str:
    return _STATUS_MARKERS.get(status, "[?]")


def _normalize_items(raw: Any) -> List[dict[str, Any]]:
    """Accept a list of dicts or TodoItem-like objects and return plain dicts."""
    if not isinstance(raw, list):
        return []
    items: List[dict[str, Any]] = []
    for entry in raw:
        if isinstance(entry, dict):
            items.append(entry)
        elif hasattr(entry, "model_dump"):
            items.append(entry.model_dump())
        elif hasattr(entry, "dict"):
            items.append(entry.dict())
        else:
            logger.warning("Skipping unrecognized todo item: %s", type(entry))
    return items


# ─────────────────────── factory ───────────────────────

def create_write_todo_tool(board: ProjectTaskBoard) -> WriteTodoTool:
    """Create a write_todo tool bound to an existing ProjectTaskBoard instance."""
    tool = WriteTodoTool()
    tool._board = board
    return tool


__all__ = [
    "TodoItem",
    "WriteTodoInput",
    "WriteTodoTool",
    "create_write_todo_tool",
]
