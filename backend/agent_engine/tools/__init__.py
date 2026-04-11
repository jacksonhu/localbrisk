"""Agent tool exports and default tool factory helpers."""

from typing import Optional

from .local_file_keyword_search import LocalFileKeywordSearchTool, create_local_file_keyword_search_tool
from .office_reader import OfficeReaderTool, create_office_reader_tool, get_available_formats
from .registry import ToolRegistry, build_builtin_tools
from .task_board import ProjectTaskBoard
from .task_tools import create_task_tools

__all__ = [
    "OfficeReaderTool",
    "LocalFileKeywordSearchTool",
    "ProjectTaskBoard",
    "ToolRegistry",
    "build_builtin_tools",
    "create_office_reader_tool",
    "create_local_file_keyword_search_tool",
    "create_task_tools",
    "get_available_formats",
    "get_builtin_tools",
]


def get_builtin_tools(backend=None, task_root: Optional[str] = None) -> list:
    """Compatibility wrapper returning built-in tools with optional workspace injection."""
    return build_builtin_tools(workspace_backend=backend, task_root=task_root)
