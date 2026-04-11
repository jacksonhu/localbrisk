"""Unit tests for ``runtime_event_adapter.py``."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_engine.core.stream_protocol import MessageType, StreamMessageBuilder
from agent_engine.services.runtime_event_adapter import RuntimeEventAdapter
from agent_engine.services.runtime_state import ExecutionSnapshot


class FakeRunResult:
    """Simple async stream result used by adapter tests."""

    def __init__(self, events, final_output=""):
        self._events = list(events)
        self.final_output = final_output

    async def stream_events(self):
        for event in self._events:
            yield event


class TestRuntimeEventAdapter:
    """Runtime event translation tests."""

    @pytest.mark.asyncio
    async def test_stream_run_result_maps_text_and_tool_events(self):
        adapter = RuntimeEventAdapter()
        builder = StreamMessageBuilder("exec-1")
        snapshot = ExecutionSnapshot(execution_id="exec-1")
        run_result = FakeRunResult(
            events=[
                SimpleNamespace(type="raw_response_event", data={"delta": "Hello "}),
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_called",
                    item={
                        "tool_name": "search_file",
                        "tool_call_id": "call-1",
                        "args": {"pattern": "*.py"},
                    },
                ),
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_output",
                    item={
                        "tool_name": "search_file",
                        "tool_call_id": "call-1",
                        "output": "Found 3 files",
                    },
                ),
            ],
            final_output="Hello world",
        )

        messages = [message async for message in adapter.stream_run_result(run_result, builder, snapshot)]

        assert messages[0].type == MessageType.THOUGHT
        assert messages[0].payload["content"] == "Hello "
        assert messages[1].type == MessageType.TOOL_CALL
        assert messages[1].payload["tool_name"] == "search_file"
        assert messages[1].payload["status"] == "running"
        assert messages[2].type == MessageType.TOOL_CALL
        assert messages[2].payload["status"] == "completed"
        assert messages[-1].type == MessageType.THOUGHT
        assert messages[-1].payload["content"] == "Hello world"
        assert snapshot.thoughts[-1]["phase"] == "done"

    @pytest.mark.asyncio
    async def test_stream_run_result_translates_internal_todo_tool(self):
        adapter = RuntimeEventAdapter()
        builder = StreamMessageBuilder("exec-2")
        snapshot = ExecutionSnapshot(execution_id="exec-2")
        run_result = FakeRunResult(
            events=[
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_called",
                    item={
                        "tool_name": "todo_write",
                        "tool_call_id": "call-2",
                        "args": {
                            "todos": [
                                {"id": "task-1", "content": "Inspect config", "status": "running"},
                                {"id": "task-2", "content": "Implement engine", "status": "pending"},
                            ]
                        },
                    },
                )
            ]
        )

        messages = [message async for message in adapter.stream_run_result(run_result, builder, snapshot)]

        assert len(messages) == 1
        assert messages[0].type == MessageType.TASK_LIST
        assert messages[0].payload["current_task_id"] == "task-1"
        assert len(snapshot.tasks) == 2
        assert snapshot.tasks[0].title == "Inspect config"

    @pytest.mark.asyncio
    async def test_stream_run_result_translates_task_board_tools(self):
        adapter = RuntimeEventAdapter()
        builder = StreamMessageBuilder("exec-3")
        snapshot = ExecutionSnapshot(execution_id="exec-3")
        snapshot.tasks = []
        run_result = FakeRunResult(
            events=[
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_output",
                    item={
                        "tool_name": "task_create",
                        "tool_call_id": "call-3",
                        "output": '{"id": 1, "subject": "Inspect runtime", "status": "pending"}',
                    },
                ),
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_called",
                    item={
                        "tool_name": "claim_task",
                        "tool_call_id": "call-4",
                        "args": {"task_id": 1, "owner": "lead"},
                    },
                ),
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="tool_called",
                    item={
                        "tool_name": "task_update",
                        "tool_call_id": "call-5",
                        "args": {"task_id": 1, "status": "completed"},
                    },
                ),
            ]
        )

        messages = [message async for message in adapter.stream_run_result(run_result, builder, snapshot)]

        assert [message.type for message in messages] == [MessageType.TASK_LIST, MessageType.TASK_LIST, MessageType.TASK_LIST]
        assert messages[0].payload["tasks"][0]["title"] == "Inspect runtime"
        assert messages[1].payload["current_task_id"] == "1"
        assert messages[2].payload["progress"] == 1.0
        assert snapshot.tasks[0].status.value == "completed"

    @pytest.mark.asyncio
    async def test_stream_run_result_emits_status_for_agent_switch_and_handoff(self):
        adapter = RuntimeEventAdapter()
        builder = StreamMessageBuilder("exec-4")
        snapshot = ExecutionSnapshot(execution_id="exec-4")
        run_result = FakeRunResult(
            events=[
                SimpleNamespace(type="agent_updated_stream_event", new_agent={"name": "planner"}),
                SimpleNamespace(
                    type="run_item_stream_event",
                    name="handoff_occurred",
                    item={"agent_name": "data_analysis_agent"},
                ),
            ]
        )

        messages = [message async for message in adapter.stream_run_result(run_result, builder, snapshot)]

        assert [message.type for message in messages] == [MessageType.STATUS, MessageType.STATUS]
        assert "planner" in messages[0].payload["text"]
        assert "data_analysis_agent" in messages[1].payload["text"]
