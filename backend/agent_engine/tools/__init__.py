"""
Agent 工具模块
提供 Agent 可用的内置工具

内置工具:
1. OfficeReader - Office365 文件读取（Excel/Word/PPT/PDF）
2. LocalFileKeywordSearch - 基于关键字的本地文件查找（基于虚拟文件系统 backend）
3. TaskTools - 持久化任务管理（create/get/update/list/claim）
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
    """获取所有内置工具实例列表

    Args:
        backend: CompositeBackend 实例，用于虚拟路径解析。
        task_root: 任务存储目录（通常为 output/.task）。

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
