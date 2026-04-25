"""Centralized tool registry and simple runtime tool factories."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .assetbundle_link import AssetBundleLinkTool, create_assetbundle_link_tool
from .file_operater import (
    FileReadTool,
    FileWriteTool,
    create_file_read_tool,
    create_file_write_tool,
    get_available_formats,
)
from .file_search import FileSearchTool, create_file_search_tool
from .shell import RunCommandTool, create_run_command_tool
from .task_board import ProjectTaskBoard
from .task_tools import create_task_tools
from .write_todo import WriteTodoTool, create_write_todo_tool


class ToolRegistry:
    """Create the built-in tools used by the runtime."""

    @staticmethod
    def build_builtin_tools(
        agent_path: Optional[str] = None,
        task_root: Optional[str] = None,
        business_unit_path: Optional[str] = None,
        asset_bundles: Optional[Sequence[Any]] = None,
    ) -> List[object]:
        """Build runtime tools bound to one agent directory."""
        return [
            create_file_read_tool(base_path=agent_path, asset_bundles=asset_bundles),
            create_file_write_tool(base_path=agent_path, asset_bundles=asset_bundles),
            create_run_command_tool(agent_path=agent_path),
            create_file_search_tool(base_path=agent_path, asset_bundles=asset_bundles),
            create_assetbundle_link_tool(
                business_unit_path=business_unit_path,
                asset_bundles=asset_bundles,
            ),
            *create_task_tools(task_root=task_root),
        ]



def build_builtin_tools(
    agent_path: Optional[str] = None,
    task_root: Optional[str] = None,
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
) -> List[object]:
    """Build built-in tools using the default registry behavior."""
    return ToolRegistry.build_builtin_tools(
        agent_path=agent_path,
        task_root=task_root,
        business_unit_path=business_unit_path,
        asset_bundles=asset_bundles,
    )


__all__ = [
    "AssetBundleLinkTool",
    "FileReadTool",
    "FileWriteTool",
    "FileSearchTool",
    "ProjectTaskBoard",
    "RunCommandTool",
    "ToolRegistry",
    "WriteTodoTool",
    "build_builtin_tools",
    "create_assetbundle_link_tool",
    "create_file_read_tool",
    "create_file_write_tool",
    "create_file_search_tool",
    "create_run_command_tool",
    "create_task_tools",
    "create_write_todo_tool",
    "get_available_formats",
]
