"""Centralized tool registry and workspace-aware tool injection helpers."""

from __future__ import annotations

from typing import Any, List, Optional

from .local_file_keyword_search import LocalFileKeywordSearchTool, create_local_file_keyword_search_tool
from .office_reader import OfficeReaderTool, create_office_reader_tool, get_available_formats
from .task_board import ProjectTaskBoard
from .task_tools import create_task_tools


class ToolRegistry:
    """Create and configure built-in runtime tools."""

    @staticmethod
    def build_builtin_tools(workspace_backend: Optional[Any] = None, task_root: Optional[str] = None) -> List[Any]:
        """Build runtime tools and inject the shared workspace backend when present."""
        tools: List[Any] = []

        office_tool = create_office_reader_tool()
        if workspace_backend is not None:
            office_tool._backend = workspace_backend
        tools.append(office_tool)

        local_file_search_tool = create_local_file_keyword_search_tool()
        if workspace_backend is not None:
            local_file_search_tool._backend = workspace_backend
        tools.append(local_file_search_tool)

        tools.extend(create_task_tools(task_root=task_root))
        return tools



def build_builtin_tools(workspace_backend: Optional[Any] = None, task_root: Optional[str] = None) -> List[Any]:
    """Build built-in tools using the default registry behavior."""
    return ToolRegistry.build_builtin_tools(workspace_backend=workspace_backend, task_root=task_root)


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
]
