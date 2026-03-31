"""
Agent Tools Module
Provides built-in tools available to Agents

Built-in tools:
1. OfficeReader - Office365 file reading (Excel/Word/PPT/PDF)
2. LocalFileKeywordSearch - Keyword-based local file search (via virtual filesystem backend)
3. TaskTools - Persistent task management (create/get/update/list/claim)
"""

from typing import Optional

from .office_reader import (
    OfficeReaderTool,
    create_office_reader_tool,
    get_available_formats,
)
from .task_tools import create_task_tools
from .task_board import ProjectTaskBoard
from .local_file_keyword_search import (
    LocalFileKeywordSearchTool,
    create_local_file_keyword_search_tool,
)

__all__ = [
    "OfficeReaderTool",
    "create_office_reader_tool",
    "get_available_formats",
    "ProjectTaskBoard",
    "create_task_tools",
    "LocalFileKeywordSearchTool",
    "create_local_file_keyword_search_tool",
    "get_builtin_tools",
]


def get_builtin_tools(backend=None, task_root: Optional[str] = None) -> list:
    """Get all built-in tool instances

    Args:
        backend: CompositeBackend instance for virtual path resolution.
        task_root: 任务存储directory (通常为 output/.task).

    Returns:
        List[BaseTool]: 可用的内置工具实例
    """
    tools = []

    office_tool = create_office_reader_tool()
    if backend is not None:
        office_tool._backend = backend
    tools.append(office_tool)

    local_file_search_tool = create_local_file_keyword_search_tool()
    if backend is not None:
        local_file_search_tool._backend = backend
    tools.append(local_file_search_tool)

    tools.extend(create_task_tools(task_root=task_root))

    return tools
