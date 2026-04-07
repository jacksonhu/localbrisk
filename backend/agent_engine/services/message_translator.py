"""Translate runtime events into StreamMessage semantics."""

import json
from typing import Any, Dict, List, Optional

from ..core.stream_protocol import TaskItem, TaskStatus


class MessageTranslator:
    """Translate raw runtime events into structured stream metadata."""

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
            "file_reader": "file",
            "office_reader": "file",
            "sql_executor": "database",
        }.items():
            if key in tool_name.lower():
                return icon
        return "tool"

    @staticmethod
    def parse_todo_args(args: Dict[str, Any]) -> List[TaskItem]:
        raw_todos = args.get("todos") or args.get("task_list") or []
        if isinstance(raw_todos, str):
            try:
                raw_todos = json.loads(raw_todos)
            except (json.JSONDecodeError, TypeError):
                return []

        tasks: List[TaskItem] = []
        for index, todo in enumerate(raw_todos):
            if not isinstance(todo, dict):
                continue
            status_str = todo.get("status", "pending")
            try:
                status = TaskStatus(status_str)
            except ValueError:
                status = TaskStatus.PENDING
            tasks.append(
                TaskItem(
                    id=str(todo.get("id", f"task-{index}")),
                    title=todo.get("content") or todo.get("title") or todo.get("description") or f"Task {index + 1}",
                    description=todo.get("description"),
                    status=status,
                )
            )
        return tasks

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
