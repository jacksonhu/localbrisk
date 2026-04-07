"""Streaming execution helpers for agent runtime."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from ..core.stream_protocol import StreamMessage, StreamMessageBuilder, TaskStatus
from ..monitoring import emit_audit_event
from .message_translator import MessageTranslator
from .runtime_state import AgentRuntimeState, ExecutionSnapshot

logger = logging.getLogger(__name__)


class AgentExecutionStreamer:
    """Handle runtime execution streaming and final output extraction."""

    INTERNAL_TOOL_NAMES = frozenset({"write_todos", "todo_write"})

    def __init__(self, translator: Optional[MessageTranslator] = None):
        self._translator = translator or MessageTranslator()

    @staticmethod
    def build_runnable_config(thread_id: str, agent_name: str) -> Dict[str, Any]:
        """Build a runnable config for the runtime backend."""
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": agent_name,
            },
        }

    @staticmethod
    def bind_agent_config(agent: Any, config: Dict[str, Any]):
        """Bind runtime config to an agent when the backend supports it."""
        with_config = getattr(agent, "with_config", None)
        if not callable(with_config):
            return agent
        try:
            return with_config(config)
        except Exception as exc:
            logger.warning("Failed to bind agent runtime config, falling back to explicit params: %s", exc)
            return agent

    async def _iterate_stream_result(self, stream_result: Any) -> AsyncIterator[Any]:
        if hasattr(stream_result, "__aiter__"):
            async for item in stream_result:
                yield item
            return
        for item in stream_result:
            yield item

    def stream_with_config(self, agent: Any, input_data: Dict[str, Any], config: Dict[str, Any], stream_mode: str):
        """Start a stream from an agent using async or sync runtime hooks."""
        bound_agent = self.bind_agent_config(agent, config)
        if callable(getattr(bound_agent, "astream", None)):
            return bound_agent.astream(input_data, stream_mode=stream_mode)
        if callable(getattr(bound_agent, "stream", None)):
            return bound_agent.stream(input_data, config=config, stream_mode=stream_mode)
        raise AttributeError("Agent does not support streaming execution")

    @staticmethod
    def extract_text_from_content(content: Any) -> str:
        """Extract text from structured model content."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return str(content) if content is not None else ""

    def summarize_tool_content(self, content: Any, limit: int = 500) -> str:
        """Build a compact tool result summary."""
        text = self.extract_text_from_content(content)
        if not text:
            return ""
        return text[:limit] if len(text) > limit else text

    async def invoke_non_stream(self, agent: Any, input_data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Invoke an agent without streaming and extract the final text output."""
        bound_agent = self.bind_agent_config(agent, config)
        if callable(getattr(bound_agent, "ainvoke", None)):
            result = await bound_agent.ainvoke(input_data)
        elif callable(getattr(bound_agent, "invoke", None)):
            try:
                result = bound_agent.invoke(input_data, config=config)
            except TypeError:
                result = bound_agent.invoke(input_data)
            if asyncio.iscoroutine(result):
                result = await result
        else:
            raise AttributeError("Agent does not support non-streaming invocation")

        if result is None:
            return ""

        if hasattr(result, "__aiter__") and not isinstance(result, (str, dict)):
            stream_text_parts: List[str] = []
            async for chunk in result:
                chunk_content = getattr(chunk, "content", None)
                if chunk_content:
                    stream_text_parts.append(self.extract_text_from_content(chunk_content))
                    continue
                choices = getattr(chunk, "choices", None)
                if choices and isinstance(choices, list):
                    for choice in choices:
                        delta = getattr(choice, "delta", None) or (choice.get("delta") if isinstance(choice, dict) else None)
                        if isinstance(delta, dict):
                            text = delta.get("content")
                            if isinstance(text, str) and text:
                                stream_text_parts.append(text)
            return "".join(stream_text_parts)

        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return self.extract_output(result)

        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        return str(result)

    async def stream_execution(
        self,
        agent: Any,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        agent_name: str,
        state: AgentRuntimeState,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> AsyncIterator[StreamMessage]:
        """Translate runtime events into StreamMessage packets."""
        accumulated_content = ""
        translator = self._translator
        tool_call_names: Dict[str, str] = {}
        index_to_id: Dict[int, str] = {}
        emitted_tool_ids: set[str] = set()
        completed_tool_ids: set[str] = set()
        filtered_tool_ids: set[str] = set()

        yield builder.thought("Analyzing your request...", mode="replace", phase="planning", icon="brain")

        try:
            async for chunk in self._iterate_stream_result(self.stream_with_config(agent, input_data, config, stream_mode="messages")):
                if state.cancel_requested:
                    break
                if not (isinstance(chunk, tuple) and len(chunk) == 2):
                    continue

                message_chunk, metadata = chunk
                node_name = metadata.get("langgraph_node", "")
                chunk_type = getattr(message_chunk, "type", "")

                if chunk_type != "tool" and hasattr(message_chunk, "content") and message_chunk.content:
                    content = self.extract_text_from_content(message_chunk.content)
                    if content:
                        accumulated_content += content
                        phase = translator.detect_phase(node_name, content)
                        yield builder.thought(
                            content=content,
                            mode="append",
                            phase=phase,
                            icon=translator.detect_icon(node_name, content),
                        )
                        snapshot.thoughts.append(
                            {
                                "content": content,
                                "phase": phase,
                                "timestamp": time.time(),
                            }
                        )

                if hasattr(message_chunk, "tool_call_chunks") and message_chunk.tool_call_chunks:
                    for tool_call in message_chunk.tool_call_chunks:
                        call_name = (tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)) or ""
                        call_id = (tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", None)) or ""
                        call_index = tool_call.get("index", None) if isinstance(tool_call, dict) else getattr(tool_call, "index", None)

                        if call_name and call_id:
                            tool_call_names[call_id] = call_name
                        if call_id and call_index is not None:
                            index_to_id[call_index] = call_id
                        if not call_id and call_index is not None:
                            call_id = index_to_id.get(call_index, "")

                        known_name = tool_call_names.get(call_id, "") if call_id else ""
                        if known_name in self.INTERNAL_TOOL_NAMES or call_name in self.INTERNAL_TOOL_NAMES:
                            if call_id:
                                filtered_tool_ids.add(call_id)
                            continue
                        if call_id and call_id in filtered_tool_ids:
                            continue
                        if call_id and call_id not in emitted_tool_ids:
                            display_name = known_name or call_name or "unknown"
                            tool_call_names.setdefault(call_id, display_name)
                            emitted_tool_ids.add(call_id)
                            yield builder.tool_call(
                                tool_name=display_name,
                                tool_call_id=call_id,
                                status="running",
                                icon=translator.tool_icon(display_name),
                            )

                if hasattr(message_chunk, "tool_calls") and message_chunk.tool_calls:
                    for tool_call in message_chunk.tool_calls:
                        call_name = (tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)) or ""
                        call_args = (tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)) or {}
                        call_id = (tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", None)) or ""

                        if call_name and call_id:
                            tool_call_names[call_id] = call_name
                        known_name = tool_call_names.get(call_id, "") if call_id else ""

                        if known_name in self.INTERNAL_TOOL_NAMES or call_name in self.INTERNAL_TOOL_NAMES:
                            if call_id:
                                filtered_tool_ids.add(call_id)
                            if isinstance(call_args, dict) and call_args:
                                tasks = translator.parse_todo_args(call_args)
                                if tasks:
                                    snapshot.tasks = tasks
                                    completed = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
                                    progress = completed / len(tasks) if tasks else 0
                                    current_id = next((task.id for task in tasks if task.status == TaskStatus.RUNNING), None)
                                    yield builder.task_list(tasks=tasks, current_task_id=current_id, progress=progress)
                            continue

                        if call_id and call_id in filtered_tool_ids:
                            continue
                        if call_id and call_id not in emitted_tool_ids:
                            display_name = known_name or call_name or "unknown"
                            tool_call_names.setdefault(call_id, display_name)
                            emitted_tool_ids.add(call_id)
                            tool_args = call_args if isinstance(call_args, dict) and call_args else None
                            yield builder.tool_call(
                                tool_name=display_name,
                                tool_call_id=call_id,
                                tool_args=tool_args,
                                status="running",
                                icon=translator.tool_icon(display_name),
                                reason=translator.extract_reason(tool_args),
                                expected_outcome=translator.extract_expected_outcome(tool_args),
                            )

                if chunk_type == "tool":
                    tool_call_id = getattr(message_chunk, "tool_call_id", "")
                    if tool_call_id in filtered_tool_ids or (tool_call_id and tool_call_id in completed_tool_ids):
                        continue
                    tool_content = getattr(message_chunk, "content", "")
                    matched_name = tool_call_names.get(tool_call_id, "") or getattr(message_chunk, "name", "") or "unknown"
                    result_summary = self.summarize_tool_content(tool_content)
                    yield builder.tool_call(
                        tool_name=matched_name,
                        tool_call_id=tool_call_id or None,
                        tool_result=result_summary or None,
                        status="completed",
                        icon="check",
                    )
                    if tool_call_id:
                        completed_tool_ids.add(tool_call_id)

        except Exception as stream_error:
            logger.warning("Messages mode failed, falling back to values mode: %s", stream_error)
            try:
                async for chunk in self._iterate_stream_result(self.stream_with_config(agent, input_data, config, stream_mode="values")):
                    if state.cancel_requested:
                        break
                    if not isinstance(chunk, dict) or "messages" not in chunk:
                        continue

                    messages = chunk["messages"]
                    if not messages:
                        continue

                    for message in messages:
                        msg_type = getattr(message, "type", None) if not isinstance(message, dict) else message.get("type")
                        if msg_type == "ai":
                            tool_calls = getattr(message, "tool_calls", None) if not isinstance(message, dict) else message.get("tool_calls")
                            for tool_call in tool_calls or []:
                                call_name = (tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)) or ""
                                call_args = (tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)) or {}
                                call_id = (tool_call.get("id") if isinstance(tool_call, dict) else getattr(tool_call, "id", None)) or ""

                                if call_name and call_id:
                                    tool_call_names[call_id] = call_name
                                known_name = tool_call_names.get(call_id, "") if call_id else ""

                                if known_name in self.INTERNAL_TOOL_NAMES or call_name in self.INTERNAL_TOOL_NAMES:
                                    if call_id:
                                        filtered_tool_ids.add(call_id)
                                    if isinstance(call_args, dict) and call_args:
                                        tasks = translator.parse_todo_args(call_args)
                                        if tasks:
                                            snapshot.tasks = tasks
                                            completed = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED)
                                            progress = completed / len(tasks) if tasks else 0
                                            current_id = next((task.id for task in tasks if task.status == TaskStatus.RUNNING), None)
                                            yield builder.task_list(tasks=tasks, current_task_id=current_id, progress=progress)
                                    continue

                                if call_id and call_id in filtered_tool_ids:
                                    continue
                                if call_id and call_id not in emitted_tool_ids:
                                    display_name = known_name or call_name or "unknown"
                                    tool_call_names.setdefault(call_id, display_name)
                                    emitted_tool_ids.add(call_id)
                                    tool_args = call_args if isinstance(call_args, dict) and call_args else None
                                    yield builder.tool_call(
                                        tool_name=display_name,
                                        tool_call_id=call_id,
                                        tool_args=tool_args,
                                        status="running",
                                        icon=translator.tool_icon(display_name),
                                        reason=translator.extract_reason(tool_args),
                                        expected_outcome=translator.extract_expected_outcome(tool_args),
                                    )

                        if msg_type == "tool":
                            tool_call_id = getattr(message, "tool_call_id", None) if not isinstance(message, dict) else message.get("tool_call_id")
                            tool_call_id = tool_call_id or ""
                            if tool_call_id and (tool_call_id in filtered_tool_ids or tool_call_id in completed_tool_ids):
                                continue
                            tool_name = tool_call_names.get(tool_call_id, "") or (
                                getattr(message, "name", None) if not isinstance(message, dict) else message.get("name")
                            ) or "unknown"
                            tool_content = getattr(message, "content", None) if not isinstance(message, dict) else message.get("content")
                            result_summary = self.summarize_tool_content(tool_content)
                            emit_audit_event(
                                "tool.completed",
                                tool_name=tool_name,
                                tool_call_id=tool_call_id or None,
                                source="agent_runtime.values",
                                result_preview=result_summary or None,
                            )
                            yield builder.tool_call(
                                tool_name=tool_name,
                                tool_call_id=tool_call_id or None,
                                tool_result=result_summary or None,
                                status="completed",
                                icon="check",
                            )
                            if tool_call_id:
                                completed_tool_ids.add(tool_call_id)

                    last_message = messages[-1]
                    last_content = getattr(last_message, "content", None) if not isinstance(last_message, dict) else last_message.get("content")
                    if last_content:
                        content = self.extract_text_from_content(last_content)
                        if content and content != accumulated_content:
                            new_part = content[len(accumulated_content):] if content.startswith(accumulated_content) else content
                            accumulated_content = content
                            yield builder.thought(
                                content=new_part if new_part else content,
                                mode="append" if new_part else "replace",
                                phase="analyzing",
                                icon="brain",
                            )
            except Exception as values_error:
                logger.warning("Values mode failed, falling back to non-streaming invoke: %s", values_error)
                output = await self.invoke_non_stream(agent, input_data, config)
                if output and output != accumulated_content:
                    accumulated_content = output

        for message in self.emit_final_output(accumulated_content, builder, snapshot):
            yield message

    def emit_final_output(
        self,
        accumulated_content: str,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> List[StreamMessage]:
        """Emit final markdown text when the stream did not fully cover it."""
        if not accumulated_content.strip():
            return []
        if snapshot.thoughts:
            emitted_text = "".join(str(thought.get("content", "")) for thought in snapshot.thoughts)
            if emitted_text == accumulated_content:
                return []
        return [
            builder.thought(
                content=accumulated_content,
                mode="replace",
                phase="done",
                icon="check",
            )
        ]

    @staticmethod
    def generate_summary(snapshot: ExecutionSnapshot) -> str:
        """Generate a compact execution summary."""
        task_count = len(snapshot.tasks)
        artifact_count = len(snapshot.artifacts)
        if task_count > 0:
            completed = sum(1 for task in snapshot.tasks if task.status == TaskStatus.COMPLETED)
            return f"Completed {completed}/{task_count} tasks, produced {artifact_count} artifacts"
        if artifact_count > 0:
            return f"Produced {artifact_count} artifacts"
        return "Execution completed"

    def extract_output(self, result: Dict[str, Any]) -> str:
        """Extract the final text output from a non-streaming runtime result."""
        if not result:
            return ""
        messages = result.get("messages", [])
        for message in reversed(messages):
            if hasattr(message, "content"):
                return self.extract_text_from_content(message.content)
            if isinstance(message, dict) and "content" in message:
                return self.extract_text_from_content(message["content"])
        if "output" in result:
            return str(result["output"])
        return ""
