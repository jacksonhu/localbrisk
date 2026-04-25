"""Tests for the write_todo tool."""

from __future__ import annotations

from pathlib import Path

from agent_engine.tools import build_builtin_tools
from agent_engine.tools.task_board import ProjectTaskBoard
from agent_engine.tools.write_todo import WriteTodoTool, create_write_todo_tool


class TestWriteTodoTool:
    """Core write_todo functionality tests."""

    def _make_tool(self, tmp_path: Path) -> WriteTodoTool:
        board = ProjectTaskBoard(root=tmp_path / ".task")
        return create_write_todo_tool(board)

    def test_create_todos_from_scratch(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)
        result = tool._run(
            todos=[
                {"content": "Analyze requirements", "status": "in_progress"},
                {"content": "Implement feature A"},
                {"content": "Write tests"},
            ],
            merge=False,
        )

        assert "3 item(s)" in result
        assert "Analyze requirements" in result
        assert "(created)" in result
        assert "[>]" in result  # in_progress marker
        assert "[ ]" in result  # pending marker

    def test_update_existing_task_status(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)

        # Create initial items.
        tool._run(
            todos=[
                {"content": "Step 1", "status": "in_progress"},
                {"content": "Step 2"},
            ],
            merge=False,
        )

        # Update step 1 to completed, step 2 to in_progress.
        result = tool._run(
            todos=[
                {"id": 1, "content": "Step 1", "status": "completed"},
                {"id": 2, "content": "Step 2", "status": "in_progress"},
            ],
            merge=True,
        )

        assert "(updated)" in result
        assert "[x]" in result  # completed
        assert "[>]" in result  # in_progress

    def test_merge_false_clears_existing_tasks(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)
        board = tool._board

        # Create initial tasks.
        tool._run(todos=[{"content": "Old task 1"}, {"content": "Old task 2"}], merge=False)
        assert "Old task 1" in board.list_all()

        # Replace with new plan (merge=false).
        tool._run(todos=[{"content": "New task A"}, {"content": "New task B"}], merge=False)
        listing = board.list_all()

        # Old tasks should be deleted; new tasks should exist.
        assert "Old task 1" not in listing
        assert "New task A" in listing
        assert "New task B" in listing

    def test_merge_true_preserves_existing_tasks(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)
        board = tool._board

        # Create existing task.
        tool._run(todos=[{"content": "Existing task"}], merge=False)

        # Merge a new task.
        tool._run(todos=[{"content": "Additional task"}], merge=True)
        listing = board.list_all()

        assert "Existing task" in listing
        assert "Additional task" in listing

    def test_empty_todos_returns_error(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)
        result = tool._run(todos=[], merge=False)
        assert "❌" in result

    def test_tool_shares_board_with_task_tools(self, tmp_path: Path):
        """write_todo and task_list share the same board in build_builtin_tools."""
        tools = build_builtin_tools(
            agent_path=str(tmp_path / "agent"),
            task_root=str(tmp_path / ".task"),
        )
        write_todo = next(t for t in tools if getattr(t, "name", "") == "write_todo")
        task_list = next(t for t in tools if getattr(t, "name", "") == "task_list")

        # Create via write_todo.
        write_todo._run(todos=[{"content": "Shared board test"}], merge=False)

        # Should be visible via task_list.
        listing = task_list._run()
        assert "Shared board test" in listing

    def test_build_builtin_tools_includes_write_todo(self, tmp_path: Path):
        tools = build_builtin_tools(
            agent_path=str(tmp_path / "agent"),
            task_root=str(tmp_path / ".task"),
        )
        tool_names = [getattr(t, "name", "") for t in tools]
        assert "write_todo" in tool_names

    def test_description_encourages_early_planning(self, tmp_path: Path):
        tool = self._make_tool(tmp_path)
        assert "complex" in tool.description.lower()
        assert "first" in tool.description.lower()
