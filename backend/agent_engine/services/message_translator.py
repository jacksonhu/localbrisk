"""Translate runtime events into StreamMessage semantics."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

from ..core.stream_protocol import TaskItem, TaskStatus


class MessageTranslator:
    """Translate raw runtime events into structured stream metadata."""

    INTERNAL_TASK_TOOL_NAMES = frozenset(
        {
            "write_todos",
            "todo_write",
            "task_create",
            "task_get",
            "task_update",
            "task_list",
            "claim_task",
        }
    )

    _TASK_STATUS_MAPPING = {
        "pending": TaskStatus.PENDING,
        "running": TaskStatus.RUNNING,
        "in_progress": TaskStatus.RUNNING,
        "completed": TaskStatus.COMPLETED,
        "failed": TaskStatus.FAILED,
        "cancelled": TaskStatus.CANCELLED,
        "canceled": TaskStatus.CANCELLED,
        "deleted": TaskStatus.CANCELLED,
    }
    _TASK_LIST_MARKER_STATUS = {
        "[ ]": TaskStatus.PENDING,
        "[>]": TaskStatus.RUNNING,
        "[x]": TaskStatus.COMPLETED,
        "[-]": TaskStatus.CANCELLED,
    }
    _TASK_LIST_LINE_RE = re.compile(r"^(?P<marker>\[[^\]]+\])\s+#(?P<id>\d+):\s*(?P<title>.+?)\s*$")
    _TASK_ID_RE = re.compile(r"(?:task\s+#?|#)(?P<id>\d+)", re.IGNORECASE)

    @staticmethod
    def detect_phase(node_name: str, content: str) -> str:
        lower = content[:50].lower()
        if "plan" in node_name.lower() or "plan" in lower:
            return "planning"
        if "reflect" in node_name.lower():
            return "reflecting"
        if "search" in lower or "搜索" in content:
            return "searching"
        if "code" in lower or "代码" in content:
            return "coding"
        return "analyzing"

    @staticmethod
    def detect_icon(node_name: str, content: str) -> str:
        lower = content[:100].lower()
        if "search" in lower:
            return "search"
        if "code" in lower:
            return "code"
        if "plan" in lower:
            return "plan"
        return "brain"

    @staticmethod
    def tool_icon(tool_name: str) -> str:
        for key, icon in {
            "search": "search",
            "web_search": "search",
            "code_executor": "code",
            "python_repl": "code",
            "run_command": "code",
            "shell": "code",
            "file_read": "file",
            "file_write": "file",
            "file_reader": "file",
            "file_operater": "file",
            "assetbundle_link": "database",
            "sql_executor": "database",
        }.items():
            if key in tool_name.lower():
                return icon
        return "tool"

    @classmethod
    def task_status_from_value(cls, value: Any) -> TaskStatus:
        normalized = str(value or "").strip().lower()
        return cls._TASK_STATUS_MAPPING.get(normalized, TaskStatus.PENDING)

    @classmethod
    def parse_todo_args(cls, args: Any) -> List[TaskItem]:
        if isinstance(args, list):
            raw_todos: Any = args
        elif isinstance(args, dict):
            raw_todos = args.get("todos") or args.get("task_list") or args.get("tasks") or []
        else:
            return []

        if isinstance(raw_todos, str):
            try:
                raw_todos = json.loads(raw_todos)
            except (json.JSONDecodeError, TypeError):
                return []

        if not isinstance(raw_todos, list):
            return []

        tasks: List[TaskItem] = []
        for index, todo in enumerate(raw_todos):
            task = cls._task_item_from_record(todo, fallback_id=f"task-{index}")
            if task is not None:
                tasks.append(task)
        return tasks

    @classmethod
    def sync_tasks_from_internal_tool(
        cls,
        tool_name: str,
        *,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_output: Any = None,
        existing_tasks: Optional[Iterable[TaskItem]] = None,
    ) -> Optional[List[TaskItem]]:
        normalized_name = str(tool_name or "").strip()
        if normalized_name not in cls.INTERNAL_TASK_TOOL_NAMES:
            return None

        existing_list = list(existing_tasks or [])

        if normalized_name in {"write_todos", "todo_write"}:
            tasks = cls.parse_todo_args(tool_args or {})
            return tasks or None

        if normalized_name == "task_list":
            tasks = cls._parse_task_list_text(tool_output)
            return tasks or None

        if normalized_name == "claim_task":
            task_id = cls._extract_task_id(tool_args, tool_output)
            if task_id is None:
                return None
            title = cls._lookup_existing_title(existing_list, task_id) or f"Task {task_id}"
            updated_task = TaskItem(id=str(task_id), title=title, status=TaskStatus.RUNNING)
            return cls._merge_task_items(existing_list, [updated_task])

        if cls._is_task_deleted(tool_output):
            task_id = cls._extract_task_id(tool_args, tool_output)
            if task_id is None:
                return None
            return [task for task in existing_list if task.id != str(task_id)]

        output_record = cls._parse_task_record(tool_output)
        if output_record is not None:
            task = cls._task_item_from_record(output_record)
            if task is not None:
                return cls._merge_task_items(existing_list, [task])

        if normalized_name == "task_update" and tool_args:
            task_id = cls._extract_task_id(tool_args, None)
            if task_id is None:
                return None
            title = cls._lookup_existing_title(existing_list, task_id) or f"Task {task_id}"
            updated_task = TaskItem(
                id=str(task_id),
                title=title,
                status=cls.task_status_from_value(tool_args.get("status")),
            )
            return cls._merge_task_items(existing_list, [updated_task])

        return None

    @staticmethod
    def current_task_id(tasks: Iterable[TaskItem]) -> Optional[str]:
        return next((task.id for task in tasks if task.status == TaskStatus.RUNNING), None)

    @staticmethod
    def progress_from_tasks(tasks: Iterable[TaskItem]) -> float:
        task_list = list(tasks)
        if not task_list:
            return 0.0
        completed = sum(1 for task in task_list if task.status == TaskStatus.COMPLETED)
        return completed / len(task_list)

    @classmethod
    def _task_item_from_record(cls, record: Any, fallback_id: Optional[str] = None) -> Optional[TaskItem]:
        if not isinstance(record, dict):
            return None

        raw_id = record.get("id", fallback_id)
        if raw_id is None:
            return None

        title = (
            record.get("subject")
            or record.get("content")
            or record.get("title")
            or record.get("description")
            or fallback_id
            or f"Task {raw_id}"
        )
        return TaskItem(
            id=str(raw_id),
            title=str(title),
            description=record.get("description"),
            status=cls.task_status_from_value(record.get("status", "pending")),
        )

    @classmethod
    def _parse_task_record(cls, payload: Any) -> Optional[Dict[str, Any]]:
        if payload is None:
            return None
        if isinstance(payload, dict):
            return payload if "id" in payload else None
        if isinstance(payload, str):
            text = payload.strip()
            if not text:
                return None
            try:
                decoded = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                return None
            return decoded if isinstance(decoded, dict) and "id" in decoded else None
        return None

    @classmethod
    def _parse_task_list_text(cls, payload: Any) -> List[TaskItem]:
        if not isinstance(payload, str):
            return []

        tasks: List[TaskItem] = []
        for line in payload.splitlines():
            match = cls._TASK_LIST_LINE_RE.match(line.strip())
            if not match:
                continue
            marker = match.group("marker")
            title = match.group("title")
            if " blocked_by=" in title:
                title = title.split(" blocked_by=", 1)[0]
            if " @" in title:
                title = title.rsplit(" @", 1)[0]
            tasks.append(
                TaskItem(
                    id=match.group("id"),
                    title=title.strip() or f"Task {match.group('id')}",
                    status=cls._TASK_LIST_MARKER_STATUS.get(marker, TaskStatus.PENDING),
                )
            )
        return tasks

    @classmethod
    def _extract_task_id(cls, tool_args: Optional[Dict[str, Any]], tool_output: Any) -> Optional[int]:
        if isinstance(tool_args, dict):
            raw_task_id = tool_args.get("task_id") or tool_args.get("id")
            if raw_task_id is not None:
                try:
                    return int(raw_task_id)
                except (TypeError, ValueError):
                    pass

        output_record = cls._parse_task_record(tool_output)
        if isinstance(output_record, dict):
            raw_task_id = output_record.get("id")
            if raw_task_id is not None:
                try:
                    return int(raw_task_id)
                except (TypeError, ValueError):
                    pass

        if isinstance(tool_output, str):
            match = cls._TASK_ID_RE.search(tool_output)
            if match:
                return int(match.group("id"))
        return None

    @staticmethod
    def _lookup_existing_title(existing_tasks: Iterable[TaskItem], task_id: int) -> Optional[str]:
        task_id_text = str(task_id)
        for task in existing_tasks:
            if task.id == task_id_text:
                return task.title
        return None

    @staticmethod
    def _merge_task_items(existing_tasks: Iterable[TaskItem], new_tasks: Iterable[TaskItem]) -> List[TaskItem]:
        merged: Dict[str, TaskItem] = {task.id: task for task in existing_tasks}
        for task in new_tasks:
            merged[task.id] = task
        return list(merged.values())

    @classmethod
    def _is_task_deleted(cls, payload: Any) -> bool:
        record = cls._parse_task_record(payload)
        if isinstance(record, dict):
            return str(record.get("status") or "").strip().lower() == "deleted"
        if isinstance(payload, str):
            return "deleted" in payload.lower()
        return False

    @staticmethod
    def extract_reason(args: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(args, dict):
            return None
        for key in ("reason", "why", "purpose", "intent"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def extract_expected_outcome(args: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(args, dict):
            return None
        for key in ("expected_outcome", "expected", "goal", "success_criteria"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
