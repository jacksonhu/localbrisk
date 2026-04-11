"""Translate OpenAI Agents SDK stream events into StreamMessage packets."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from ..core.stream_protocol import StreamMessage, StreamMessageBuilder, TaskStatus
from ..monitoring import emit_audit_event
from .message_translator import MessageTranslator
from .runtime_state import ExecutionSnapshot

logger = logging.getLogger(__name__)


class RuntimeEventAdapter:
    """Map OpenAI Agents SDK runtime events onto the stable StreamMessage protocol."""

    INTERNAL_TOOL_NAMES = MessageTranslator.INTERNAL_TASK_TOOL_NAMES

    def __init__(self, translator: Optional[MessageTranslator] = None) -> None:
        self._translator = translator or MessageTranslator()

    async def stream_runtime(
        self,
        runtime: Any,
        input_data: Any,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
        *,
        session_id: Optional[str] = None,
        run_config: Any = None,
    ) -> AsyncIterator[StreamMessage]:
        """Run one OpenAI runtime and translate its stream into StreamMessage packets."""
        run_result = await runtime.run_streamed(input_data, session_id=session_id, run_config=run_config)
        async for message in self.stream_run_result(run_result, builder, snapshot):
            yield message

    async def stream_run_result(
        self,
        run_result: Any,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> AsyncIterator[StreamMessage]:
        """Translate one SDK streaming result into stable protocol messages."""
        translator = self._translator
        accumulated_text = ""
        tool_call_names: Dict[str, str] = {}
        filtered_tool_ids: set[str] = set()
        emitted_tool_ids: set[str] = set()
        completed_tool_ids: set[str] = set()

        async for event in self._iterate_stream_events(run_result):
            event_type = self._extract_value(event, "type") or ""

            if event_type == "raw_response_event":
                content = self._extract_text(self._extract_value(event, "data"))
                if content:
                    accumulated_text += content
                    yield builder.thought(content=content, mode="append", phase="analyzing", icon="brain")
                    self._append_snapshot_thought(snapshot, content, phase="analyzing")
                continue

            if event_type == "agent_updated_stream_event":
                new_agent = self._extract_value(event, "new_agent")
                agent_name = self._extract_agent_name(new_agent)
                if agent_name:
                    yield builder.status(f"Switched to agent '{agent_name}'", icon="swap")
                continue

            if event_type != "run_item_stream_event":
                continue

            event_name = self._extract_value(event, "name") or ""
            item = self._extract_value(event, "item")

            if event_name == "tool_called":
                tool_name = self._extract_tool_name(item)
                tool_call_id = self._extract_tool_call_id(item)
                tool_args = self._extract_tool_args(item)
                if tool_name and tool_call_id:
                    tool_call_names[tool_call_id] = tool_name

                known_name = tool_call_names.get(tool_call_id or "", "") or tool_name or "unknown"
                if known_name in self.INTERNAL_TOOL_NAMES:
                    if tool_call_id:
                        filtered_tool_ids.add(tool_call_id)
                    tasks = translator.sync_tasks_from_internal_tool(
                        known_name,
                        tool_args=tool_args,
                        existing_tasks=snapshot.tasks,
                    )
                    if tasks is not None:
                        snapshot.tasks = tasks
                        yield builder.task_list(
                            tasks=tasks,
                            current_task_id=translator.current_task_id(tasks),
                            progress=translator.progress_from_tasks(tasks),
                        )
                    continue

                if tool_call_id and tool_call_id in filtered_tool_ids:
                    continue
                if tool_call_id and tool_call_id in emitted_tool_ids:
                    continue

                if tool_call_id:
                    emitted_tool_ids.add(tool_call_id)
                yield builder.tool_call(
                    tool_name=known_name,
                    tool_call_id=tool_call_id or None,
                    tool_args=tool_args,
                    status="running",
                    icon=translator.tool_icon(known_name),
                    reason=translator.extract_reason(tool_args),
                    expected_outcome=translator.extract_expected_outcome(tool_args),
                )
                continue

            if event_name == "tool_output":
                tool_call_id = self._extract_tool_call_id(item)
                tool_name = tool_call_names.get(tool_call_id or "", "") or self._extract_tool_name(item) or "unknown"
                tool_result = self._extract_text(self._extract_tool_output(item))

                if tool_name in self.INTERNAL_TOOL_NAMES:
                    if tool_call_id:
                        filtered_tool_ids.add(tool_call_id)
                        completed_tool_ids.add(tool_call_id)
                    tasks = translator.sync_tasks_from_internal_tool(
                        tool_name,
                        tool_args=self._extract_tool_args(item),
                        tool_output=tool_result,
                        existing_tasks=snapshot.tasks,
                    )
                    if tasks is not None:
                        snapshot.tasks = tasks
                        yield builder.task_list(
                            tasks=tasks,
                            current_task_id=translator.current_task_id(tasks),
                            progress=translator.progress_from_tasks(tasks),
                        )
                    continue

                if tool_call_id and (tool_call_id in filtered_tool_ids or tool_call_id in completed_tool_ids):
                    continue

                result_preview = tool_result[:500] if len(tool_result) > 500 else tool_result
                emit_audit_event(
                    "tool.completed",
                    tool_name=tool_name,
                    tool_call_id=tool_call_id or None,
                    source="openai_agents_runtime",
                    result_preview=result_preview or None,
                )
                yield builder.tool_call(
                    tool_name=tool_name,
                    tool_call_id=tool_call_id or None,
                    tool_result=result_preview or None,
                    status="completed",
                    icon="check",
                )
                if tool_call_id:
                    completed_tool_ids.add(tool_call_id)
                continue

            if event_name in {"handoff_requested", "handoff_occured", "handoff_occurred"}:
                target_name = self._extract_agent_name(item)
                if not target_name:
                    target_name = "another agent"
                action_text = "Preparing handoff to" if event_name == "handoff_requested" else "Handoff switched to"
                yield builder.status(f"{action_text} '{target_name}'", icon="swap")
                continue

            if event_name == "reasoning_item_created":
                reasoning_text = self._extract_text(item)
                if reasoning_text:
                    yield builder.thought(
                        content=reasoning_text,
                        mode="append",
                        phase="reflecting",
                        icon="brain",
                        reasoning_type="reflection",
                    )
                    self._append_snapshot_thought(snapshot, reasoning_text, phase="reflecting")
                continue

            if event_name == "message_output_created":
                message_text = self._extract_text(item)
                if message_text and not accumulated_text:
                    accumulated_text += message_text
                    yield builder.thought(content=message_text, mode="append", phase="analyzing", icon="brain")
                    self._append_snapshot_thought(snapshot, message_text, phase="analyzing")

        final_output = self.extract_final_output(run_result)
        if final_output and final_output != accumulated_text:
            yield builder.thought(content=final_output, mode="replace", phase="done", icon="check")
            self._append_snapshot_thought(snapshot, final_output, phase="done")

    async def _iterate_stream_events(self, run_result: Any) -> AsyncIterator[Any]:
        """Iterate stream events from a streaming run result object."""
        stream_events = getattr(run_result, "stream_events", None)
        if not callable(stream_events):
            raise TypeError("Streaming run result does not expose stream_events()")

        result = stream_events()
        if hasattr(result, "__aiter__"):
            async for event in result:
                yield event
            return

        for event in result:
            yield event

    @staticmethod
    def extract_final_output(run_result: Any) -> str:
        """Extract the final text output from a completed SDK run result."""
        final_output = getattr(run_result, "final_output", None)
        if isinstance(final_output, str):
            return final_output
        if final_output is None:
            return ""
        if isinstance(final_output, (dict, list)):
            return json.dumps(final_output, ensure_ascii=False)
        return str(final_output)

    @staticmethod
    def _extract_value(source: Any, key: str, default: Any = None) -> Any:
        """Read a value from a dict-like or attribute-based object."""
        if isinstance(source, dict):
            return source.get(key, default)
        return getattr(source, key, default)

    @classmethod
    def _item_candidates(cls, item: Any) -> List[Any]:
        """Return candidate objects that may carry event payload fields."""
        candidates: List[Any] = []
        if item is not None:
            candidates.append(item)
        raw_item = cls._extract_value(item, "raw_item")
        if raw_item is not None and raw_item is not item:
            candidates.append(raw_item)
        return candidates

    @classmethod
    def _extract_tool_name(cls, item: Any) -> str:
        """Extract the tool name from a run item payload."""
        for candidate in cls._item_candidates(item):
            for key in ("tool_name", "name", "tool", "tool_label"):
                value = cls._extract_value(candidate, key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @classmethod
    def _extract_tool_call_id(cls, item: Any) -> str:
        """Extract the tool call id from a run item payload."""
        for candidate in cls._item_candidates(item):
            for key in ("tool_call_id", "call_id", "id"):
                value = cls._extract_value(candidate, key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    @classmethod
    def _extract_tool_args(cls, item: Any) -> Optional[Dict[str, Any]]:
        """Extract and normalize tool call arguments from a run item payload."""
        for candidate in cls._item_candidates(item):
            for key in ("args", "arguments", "tool_args", "input"):
                value = cls._extract_value(candidate, key)
                normalized = cls._normalize_mapping(value)
                if normalized is not None:
                    return normalized
        return None

    @classmethod
    def _extract_tool_output(cls, item: Any) -> Any:
        """Extract the tool output value from a run item payload."""
        for candidate in cls._item_candidates(item):
            for key in ("output", "result", "tool_result", "content", "text"):
                value = cls._extract_value(candidate, key)
                if value is not None:
                    return value
        return None

    @classmethod
    def _extract_agent_name(cls, item: Any) -> str:
        """Extract a handoff target agent name from an event payload."""
        for candidate in cls._item_candidates(item):
            for key in ("agent_name", "name", "target_agent"):
                value = cls._extract_value(candidate, key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            agent = cls._extract_value(candidate, "agent")
            if agent is not None:
                name = cls._extract_value(agent, "name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return ""

    @classmethod
    def _normalize_mapping(cls, value: Any) -> Optional[Dict[str, Any]]:
        """Normalize JSON-like tool args into a plain dict."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            payload = value.strip()
            if not payload:
                return None
            try:
                decoded = json.loads(payload)
            except json.JSONDecodeError:
                return {"input": value}
            if isinstance(decoded, dict):
                return decoded
            return {"input": decoded}
        return None

    @classmethod
    def _extract_text(cls, value: Any) -> str:
        """Extract user-visible text from nested SDK payload objects."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [cls._extract_text(item) for item in value]
            return "".join(part for part in parts if part)
        if isinstance(value, dict):
            for key in ("delta", "text", "content", "output", "summary"):
                if key in value:
                    text = cls._extract_text(value.get(key))
                    if text:
                        return text
            return json.dumps(value, ensure_ascii=False)
        for key in ("delta", "text", "content", "output", "summary"):
            attr = getattr(value, key, None)
            if attr is None:
                continue
            text = cls._extract_text(attr)
            if text:
                return text
        return str(value)

    @staticmethod
    def _append_snapshot_thought(snapshot: ExecutionSnapshot, content: str, *, phase: str) -> None:
        """Persist one translated thought into the execution snapshot."""
        snapshot.thoughts.append(
            {
                "content": content,
                "phase": phase,
                "timestamp": time.time(),
            }
        )


__all__ = ["RuntimeEventAdapter"]
