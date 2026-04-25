"""Agent task management tools."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .task_board import ProjectTaskBoard
from .write_todo import WriteTodoTool


class TaskCreateInput(BaseModel):
    subject: str = Field(description="Task title")
    description: str = Field(default="", description="Task description")


class TaskGetInput(BaseModel):
    task_id: int = Field(description="Task ID")


class TaskUpdateInput(BaseModel):
    task_id: int = Field(description="Task ID")
    status: Optional[str] = Field(default=None, description="Task status: pending/in_progress/completed/deleted")
    add_blocked_by: Optional[list[int]] = Field(default=None, description="Task IDs to append to blockedBy")
    add_blocks: Optional[list[int]] = Field(default=None, description="Task IDs to append to blocks")


class TaskClaimInput(BaseModel):
    task_id: int = Field(description="Task ID")
    owner: str = Field(default="lead", description="Task owner")


class TaskListInput(BaseModel):
    pass


class _TaskBoardTool(BaseTool):
    _board: Any = None

    def _ensure_board(self) -> ProjectTaskBoard:
        if self._board is None:
            raise RuntimeError("task board is not initialized")
        return self._board


class TaskCreateTool(_TaskBoardTool):
    name: str = "task_create"
    description: str = "Create a persisted task and return JSON."
    args_schema: Type[BaseModel] = TaskCreateInput

    def _run(self, subject: str, description: str = "") -> str:
        return self._ensure_board().create(subject, description)

    async def _arun(self, subject: str, description: str = "") -> str:
        return await asyncio.to_thread(self._run, subject, description)


class TaskGetTool(_TaskBoardTool):
    name: str = "task_get"
    description: str = "Get task details by task_id."
    args_schema: Type[BaseModel] = TaskGetInput

    def _run(self, task_id: int) -> str:
        return self._ensure_board().get(task_id)

    async def _arun(self, task_id: int) -> str:
        return await asyncio.to_thread(self._run, task_id)


class TaskUpdateTool(_TaskBoardTool):
    name: str = "task_update"
    description: str = "Update task status and dependencies."
    args_schema: Type[BaseModel] = TaskUpdateInput

    def _run(
        self,
        task_id: int,
        status: Optional[str] = None,
        add_blocked_by: Optional[list[int]] = None,
        add_blocks: Optional[list[int]] = None,
    ) -> str:
        return self._ensure_board().update(task_id, status, add_blocked_by, add_blocks)

    async def _arun(
        self,
        task_id: int,
        status: Optional[str] = None,
        add_blocked_by: Optional[list[int]] = None,
        add_blocks: Optional[list[int]] = None,
    ) -> str:
        return await asyncio.to_thread(self._run, task_id, status, add_blocked_by, add_blocks)


class TaskListTool(_TaskBoardTool):
    name: str = "task_list"
    description: str = "List all persisted tasks."
    args_schema: Type[BaseModel] = TaskListInput

    def _run(self) -> str:
        return self._ensure_board().list_all()

    async def _arun(self) -> str:
        return await asyncio.to_thread(self._run)


class TaskClaimTool(_TaskBoardTool):
    name: str = "claim_task"
    description: str = "Claim a task and set its status to in_progress."
    args_schema: Type[BaseModel] = TaskClaimInput

    def _run(self, task_id: int, owner: str = "lead") -> str:
        return self._ensure_board().claim(task_id, owner)

    async def _arun(self, task_id: int, owner: str = "lead") -> str:
        return await asyncio.to_thread(self._run, task_id, owner)


def create_task_tools(task_root: Optional[str] = None) -> list[BaseTool]:
    """Create all task management tools sharing one ProjectTaskBoard instance."""
    root = Path(task_root) if task_root else (Path.cwd() / ".task")
    board = ProjectTaskBoard(root=root)

    tools: list[_TaskBoardTool] = [
        TaskCreateTool(),
        TaskGetTool(),
        TaskUpdateTool(),
        TaskListTool(),
        TaskClaimTool(),
    ]
    for tool in tools:
        tool._board = board

    # write_todo shares the same board for consistent task state.
    write_todo = WriteTodoTool()
    write_todo._board = board

    return [*tools, write_todo]
