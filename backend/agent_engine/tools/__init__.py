"""Agent tool exports and default tool factory helpers."""

from typing import Any, Optional, Sequence

from .assetbundle_link import AssetBundleLinkTool, create_assetbundle_link_tool
from .file_operater import (
    FileReadTool,
    FileWriteTool,
    create_file_read_tool,
    create_file_write_tool,
    get_available_formats,
)
from .file_search import FileSearchTool, create_file_search_tool
from .registry import ToolRegistry, build_builtin_tools
from .shell import RunCommandTool, create_run_command_tool
from .task_board import ProjectTaskBoard
from .task_tools import create_task_tools

__all__ = [
    "AssetBundleLinkTool",
    "FileReadTool",
    "FileWriteTool",
    "FileSearchTool",
    "ProjectTaskBoard",
    "RunCommandTool",
    "ToolRegistry",
    "build_builtin_tools",
    "create_assetbundle_link_tool",
    "create_file_read_tool",
    "create_file_write_tool",
    "create_file_search_tool",
    "create_run_command_tool",
    "create_task_tools",
    "get_available_formats",
    "get_builtin_tools",
]


def get_builtin_tools(
    agent_path: Optional[str] = None,
    task_root: Optional[str] = None,
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
) -> list:
    """Compatibility wrapper returning built-in tools bound to one agent directory."""
    return build_builtin_tools(
        agent_path=agent_path,
        task_root=task_root,
        business_unit_path=business_unit_path,
        asset_bundles=asset_bundles,
    )
