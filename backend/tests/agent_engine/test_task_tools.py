"""任务工具与任务板测试。"""

import json
from pathlib import Path

import pytest

from agent_engine.tools import create_task_tools
from agent_engine.tools.task_board import ProjectTaskBoard


def _build_tools(tmp_path: Path):
    tools = create_task_tools(task_root=str(tmp_path / ".task"))
    by_name = {tool.name: tool for tool in tools}
    return by_name


class TestProjectTaskBoard:
    def test_create_get_update_claim_list(self, tmp_path: Path):
        board = ProjectTaskBoard(root=tmp_path / ".task")

        created = json.loads(board.create("任务A", "描述A"))
        assert created["id"] == 1
        assert created["status"] == "pending"

        got = json.loads(board.get(1))
        assert got["subject"] == "任务A"

        claimed = board.claim(1, "alice")
        assert "Claimed task #1 for alice" in claimed

        updated = json.loads(board.update(1, status="completed"))
        assert updated["status"] == "completed"

        text = board.list_all()
        assert "#1: 任务A" in text

    def test_update_invalid_status(self, tmp_path: Path):
        board = ProjectTaskBoard(root=tmp_path / ".task")
        board.create("任务A")
        with pytest.raises(ValueError, match="invalid status"):
            board.update(1, status="invalid")

    def test_delete_task(self, tmp_path: Path):
        board = ProjectTaskBoard(root=tmp_path / ".task")
        board.create("任务A")

        msg = board.update(1, status="deleted")
        assert msg == "Task 1 deleted"
        assert not (tmp_path / ".task" / "task_1.json").exists()


class TestTaskTools:
    def test_task_tools_roundtrip(self, tmp_path: Path):
        tools = _build_tools(tmp_path)

        created = json.loads(tools["task_create"]._run("任务B", "描述B"))
        task_id = created["id"]

        got = json.loads(tools["task_get"]._run(task_id))
        assert got["subject"] == "任务B"

        tools["claim_task"]._run(task_id, "bob")
        updated = json.loads(tools["task_update"]._run(task_id, status="in_progress", add_blocked_by=[2, 2]))
        assert updated["owner"] == "bob"
        assert updated["blockedBy"] == [2]

        text = tools["task_list"]._run()
        assert f"#{task_id}: 任务B" in text

    @pytest.mark.asyncio
    async def test_task_create_arun(self, tmp_path: Path):
        tools = _build_tools(tmp_path)
        result = await tools["task_create"]._arun("异步任务", "异步描述")
        created = json.loads(result)
        assert created["subject"] == "异步任务"
