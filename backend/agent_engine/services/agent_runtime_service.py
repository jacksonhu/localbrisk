"""
Agent Runtime Service

Manages Agent loading, execution, state, and lifecycle.
Outputs THOUGHT/TASK_LIST/ARTIFACT/STATUS/ERROR/DONE message packets via the StreamMessage protocol.
"""

import asyncio
import json
import logging
import re
import time
import traceback as tb_module
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.stream_protocol import (
    StreamMessage,
    StreamMessageBuilder,
    TaskItem,
    TaskStatus,
    SnapshotPayload,
    MessageType,
)

logger = logging.getLogger(__name__)


# ============================================================
# Status Definitions
# ============================================================

class AgentStatus(str, Enum):
    """Agent runtime status"""
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNLOADED = "unloaded"


@dataclass
class AgentRuntimeState:
    """Agent runtime state"""
    business_unit_id: str
    agent_name: str
    agent_path: str
    status: AgentStatus = AgentStatus.IDLE
    agent_instance: Any = None
    current_execution_id: Optional[str] = None
    loaded_at: Optional[str] = None
    last_execution_at: Optional[str] = None
    execution_count: int = 0
    error_count: int = 0
    cancel_requested: bool = False


@dataclass
class ExecutionSnapshot:
    """Execution snapshot — used for reconnection recovery"""
    execution_id: str
    thoughts: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[TaskItem] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    last_seq: int = 0


# ============================================================
# MessageTranslator — LangGraph Events → StreamMessage
# ============================================================

class MessageTranslator:
    """Translates raw LangGraph streaming events into StreamMessage packets"""

    @staticmethod
    def detect_phase(node_name: str, content: str) -> str:
        lower = content[:50].lower()
        if "plan" in node_name.lower() or "plan" in lower:
            return "planning"
        if "reflect" in node_name.lower():
            return "reflecting"
        if "search" in lower:
            return "searching"
        if "code" in lower:
            return "coding"
        return "analyzing"

    @staticmethod
    def detect_icon(node_name: str, content: str) -> str:
        lower = content[:100].lower()
        if "search" in lower:
            return "search"
        if "code" in lower:
            return "code"
        if "plan" in lower:
            return "plan"
        return "brain"

    @staticmethod
    def tool_icon(tool_name: str) -> str:
        for key, icon in {
            "search": "search", "web_search": "search",
            "code_executor": "code", "python_repl": "code",
            "file_reader": "file", "office_reader": "file",
            "sql_executor": "database",
        }.items():
            if key in tool_name.lower():
                return icon
        return "tool"

    @staticmethod
    def parse_todo_args(args: Dict[str, Any]) -> List[TaskItem]:
        raw_todos = args.get("todos") or args.get("task_list") or []
        if isinstance(raw_todos, str):
            try:
                raw_todos = json.loads(raw_todos)
            except (json.JSONDecodeError, TypeError):
                return []

        tasks = []
        for i, todo in enumerate(raw_todos):
            if isinstance(todo, dict):
                status_str = todo.get("status", "pending")
                try:
                    status = TaskStatus(status_str)
                except ValueError:
                    status = TaskStatus.PENDING
                tasks.append(TaskItem(
                    id=str(todo.get("id", f"task-{i}")),
                    title=todo.get("content") or todo.get("title") or todo.get("description") or f"Task {i + 1}",
                    description=todo.get("description"),
                    status=status,
                ))
        return tasks

    @staticmethod
    def extract_reason(args: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(args, dict):
            return None
        for key in ("reason", "why", "purpose", "intent"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def extract_expected_outcome(args: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(args, dict):
            return None
        for key in ("expected_outcome", "expected", "goal", "success_criteria"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


# ============================================================
# AgentRuntimeService
# ============================================================

class AgentRuntimeService:
    """Agent Runtime Service — manages the full Agent lifecycle"""

    def __init__(self):
        logger.info("Initializing AgentRuntimeService")
        self._agents: Dict[str, AgentRuntimeState] = {}
        self._engine = None
        self._lock = asyncio.Lock()
        self._snapshots: Dict[str, ExecutionSnapshot] = {}
        self._translator = MessageTranslator()

    def _get_agent_key(self, business_unit_id: str, agent_name: str) -> str:
        return f"{business_unit_id}/{agent_name}"

    def _ensure_engine(self):
        if self._engine is None:
            from ..engine.deepagents_engine import get_deepagents_engine
            self._engine = get_deepagents_engine()
        return self._engine

    def _resolve_thread_id(self, agent_name: str, context: Optional[Dict[str, Any]]) -> str:
        if isinstance(context, dict):
            raw = context.get("thread_id")
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return agent_name

    def _build_runnable_config(self, thread_id: str, agent_name: str) -> Dict[str, Any]:
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": agent_name,
            },
        }

    def _bind_agent_config(self, agent: Any, config: Dict[str, Any]):
        with_config = getattr(agent, "with_config", None)
        if not callable(with_config):
            return agent
        try:
            return with_config(config)
        except Exception as bind_error:
            logger.warning(f"Failed to bind Agent runtime config, falling back to explicit params: {bind_error}")
            return agent

    def _stream_with_config(self, agent: Any, input_data: Dict[str, Any], config: Dict[str, Any], stream_mode: str):
        bound_agent = self._bind_agent_config(agent, config)
        return bound_agent.astream(input_data, stream_mode=stream_mode)

    @staticmethod
    def _extract_text_from_content(content: Any) -> str:
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

    def _summarize_tool_content(self, content: Any, limit: int = 500) -> str:
        text = self._extract_text_from_content(content)
        if not text:
            return ""
        return text[:limit] if len(text) > limit else text

    @staticmethod
    def _sanitize_file_segment(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", value or "")
        return cleaned.strip("._") or "default"

    def _get_agent_path(self, business_unit_id: str, agent_name: str) -> Path:
        key = self._get_agent_key(business_unit_id, agent_name)
        state = self._agents.get(key)
        if state and state.agent_path:
            return Path(state.agent_path)

        from app.core.config import settings
        return settings.CATALOGS_DIR / business_unit_id / "agents" / agent_name

    def _get_history_file_path(self, business_unit_id: str, agent_name: str, thread_id: str) -> Path:
        agent_path = self._get_agent_path(business_unit_id, agent_name)
        history_dir = agent_path / "output" / ".chathistory"
        history_dir.mkdir(parents=True, exist_ok=True)
        safe_agent_name = self._sanitize_file_segment(agent_name)
        safe_thread_id = self._sanitize_file_segment(thread_id)
        return history_dir / f"{safe_agent_name}_{safe_thread_id}.md"

    @staticmethod
    def _build_default_history(agent_name: str, thread_id: str) -> Dict[str, Any]:
        return {
            "version": 1,
            "agent_name": agent_name,
            "thread_id": thread_id,
            "turns": [],
        }

    def _read_history_doc(self, history_file: Path, agent_name: str, thread_id: str) -> Dict[str, Any]:
        if not history_file.exists():
            return self._build_default_history(agent_name, thread_id)

        try:
            content = history_file.read_text(encoding="utf-8")
            start_marker = "<!-- LOCALBRISK_CHAT_HISTORY_JSON_BEGIN -->"
            end_marker = "<!-- LOCALBRISK_CHAT_HISTORY_JSON_END -->"
            start = content.find(start_marker)
            end = content.find(end_marker)
            if start == -1 or end == -1 or end <= start:
                return self._build_default_history(agent_name, thread_id)

            json_text = content[start + len(start_marker):end].strip()
            parsed = json.loads(json_text) if json_text else {}
            if not isinstance(parsed, dict):
                return self._build_default_history(agent_name, thread_id)

            turns = parsed.get("turns")
            if not isinstance(turns, list):
                parsed["turns"] = []
            parsed.setdefault("version", 1)
            parsed.setdefault("agent_name", agent_name)
            parsed.setdefault("thread_id", thread_id)
            return parsed
        except Exception as read_error:
            logger.warning(f"Failed to read history, resetting file: {history_file}, error={read_error}")
            return self._build_default_history(agent_name, thread_id)

    @staticmethod
    def _render_history_markdown(history: Dict[str, Any]) -> str:
        turns = history.get("turns") if isinstance(history, dict) else []
        turns = turns if isinstance(turns, list) else []
        header = [
            "# LocalBrisk Agent Chat History",
            "",
            f"- agent_name: {history.get('agent_name', '')}",
            f"- thread_id: {history.get('thread_id', '')}",
            f"- turns: {len(turns)}",
            "",
            "<!-- LOCALBRISK_CHAT_HISTORY_JSON_BEGIN -->",
            json.dumps(history, ensure_ascii=False, indent=2),
            "<!-- LOCALBRISK_CHAT_HISTORY_JSON_END -->",
            "",
        ]
        return "\n".join(header)

    def _write_history_doc(self, history_file: Path, history: Dict[str, Any]) -> None:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(self._render_history_markdown(history), encoding="utf-8")

    def _persist_history_turn(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: str,
        user_input: str,
        stream_messages: List[Dict[str, Any]],
    ) -> None:
        history_file = self._get_history_file_path(business_unit_id, agent_name, thread_id)
        history = self._read_history_doc(history_file, agent_name, thread_id)
        turns = history.get("turns")
        if not isinstance(turns, list):
            turns = []
            history["turns"] = turns

        turns.append(
            {
                "created_at": datetime.now().isoformat(),
                "user_input": user_input,
                "messages": stream_messages,
            }
        )
        self._write_history_doc(history_file, history)

    async def get_conversation_history(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_thread_id = self._resolve_thread_id(agent_name, {"thread_id": thread_id} if thread_id else None)
        history_file = self._get_history_file_path(business_unit_id, agent_name, resolved_thread_id)
        history = self._read_history_doc(history_file, agent_name, resolved_thread_id)
        return {
            "agent_name": agent_name,
            "thread_id": resolved_thread_id,
            "history_file": history_file.name,
            "turns": history.get("turns", []),
        }

    # ================================================================
    # Agent Loading
    # ================================================================

    async def load_agent(
        self,
        business_unit_id: str,
        agent_name: str,
        agent_path: Optional[str] = None
    ) -> AgentRuntimeState:
        """Load an Agent"""
        key = self._get_agent_key(business_unit_id, agent_name)

        async with self._lock:
            if key in self._agents:
                state = self._agents[key]
                if state.status in (AgentStatus.READY, AgentStatus.RUNNING):
                    logger.info(f"Agent already loaded: {key}")
                    return state

            if not agent_path:
                from app.core.config import settings
                agent_path = str(settings.CATALOGS_DIR / business_unit_id / "agents" / agent_name)

            state = AgentRuntimeState(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                agent_path=agent_path,
                status=AgentStatus.LOADING,
            )
            self._agents[key] = state

        try:
            logger.info(f"Loading Agent: {key}, path={agent_path}")
            engine = self._ensure_engine()
            agent = await engine.build_agent(
                agent_path=agent_path,
                business_unit_id=business_unit_id,
                debug=False
            )

            task_dir = Path(agent_path) / "output" / ".task"
            try:
                task_dir.mkdir(parents=True, exist_ok=True)
            except Exception as mkdir_error:
                logger.error(f"Failed to initialize task directory: {task_dir}, error={mkdir_error}")
                raise RuntimeError(f"Failed to initialize task directory: {task_dir}") from mkdir_error

            async with self._lock:
                state.agent_instance = agent
                state.status = AgentStatus.READY
                state.loaded_at = datetime.now().isoformat()

            logger.info(f"Agent loaded successfully: {key}")
            return state

        except Exception as e:
            logger.error(f"Failed to load Agent: {key}, error={e}")
            async with self._lock:
                state.status = AgentStatus.FAILED
                state.error_count += 1
            raise

    async def _ensure_ready_agent(self, business_unit_id: str, agent_name: str) -> AgentRuntimeState:
        key = self._get_agent_key(business_unit_id, agent_name)
        state = self._agents.get(key)
        if state and state.status == AgentStatus.READY:
            return state
        return await self.load_agent(business_unit_id, agent_name)

    async def _mark_agent_running(self, state: AgentRuntimeState, execution_id: str) -> None:
        async with self._lock:
            state.status = AgentStatus.RUNNING
            state.current_execution_id = execution_id
            state.cancel_requested = False
            state.last_execution_at = datetime.now().isoformat()

    async def _mark_agent_ready(self, key: str, increase_execution_count: bool = False) -> None:
        async with self._lock:
            state = self._agents.get(key)
            if not state:
                return
            state.status = AgentStatus.READY
            if increase_execution_count:
                state.execution_count += 1

    async def _mark_agent_failed(self, key: str) -> None:
        async with self._lock:
            state = self._agents.get(key)
            if not state:
                return
            state.status = AgentStatus.READY
            state.error_count += 1

    # ================================================================
    # Streaming Execution — outputs StreamMessage packets
    # ================================================================

    async def execute_agent_stream(
        self,
        business_unit_id: str,
        agent_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamMessage]:
        """Stream-execute an Agent — outputs StreamMessage packets"""
        key = self._get_agent_key(business_unit_id, agent_name)
        thread_id = self._resolve_thread_id(agent_name, context)
        execution_id = thread_id
        start_time = time.time()
        builder = StreamMessageBuilder(execution_id)

        snapshot = ExecutionSnapshot(execution_id=execution_id)
        self._snapshots[execution_id] = snapshot
        stream_messages: List[Dict[str, Any]] = []

        def record_stream_message(message: StreamMessage) -> StreamMessage:
            try:
                stream_messages.append(message.model_dump(exclude_none=True))
            except Exception:
                stream_messages.append(
                    {
                        "type": getattr(message, "type", ""),
                        "payload": getattr(message, "payload", {}),
                        "execution_id": getattr(message, "execution_id", execution_id),
                        "timestamp": getattr(message, "timestamp", time.time()),
                        "seq": getattr(message, "seq", 0),
                    }
                )
            return message

        yield record_stream_message(builder.status("Initializing Agent...", icon="loading"))

        try:
            state = self._agents.get(key)
            if not state or state.status != AgentStatus.READY:
                yield record_stream_message(builder.status("Loading Agent...", icon="loading"))
            state = await self._ensure_ready_agent(business_unit_id, agent_name)
            await self._mark_agent_running(state, execution_id)

            agent = state.agent_instance
            yield record_stream_message(builder.status("Agent is ready, starting execution...", icon="play"))

            input_data = {"messages": [{"role": "user", "content": user_input}]}
            config = self._build_runnable_config(thread_id, agent_name)

            async for msg in self._stream_execution(
                agent, input_data, config, execution_id, agent_name, state, builder, snapshot
            ):
                yield record_stream_message(msg)

            await self._mark_agent_ready(key, increase_execution_count=True)

            snapshot.status = "completed"

            total_time_ms = int((time.time() - start_time) * 1000)
            yield record_stream_message(builder.done(
                summary=self._generate_summary(snapshot),
                total_steps=len([t for t in snapshot.tasks if t.status == TaskStatus.COMPLETED]),
                total_time_ms=total_time_ms,
            ))

        except asyncio.CancelledError:
            snapshot.status = "cancelled"
            yield record_stream_message(builder.status("Execution cancelled", icon="cancel"))
            yield record_stream_message(builder.done(summary="Execution cancelled"))

        except Exception as e:
            logger.error(f"Agent streaming execution failed: {key}, error={e}")
            await self._mark_agent_failed(key)

            snapshot.status = "failed"
            yield record_stream_message(builder.error(
                message=str(e),
                error_type=type(e).__name__,
                suggestion="Please check Agent configuration or retry",
                retryable=True,
                traceback=tb_module.format_exc(),
            ))
            yield record_stream_message(builder.done(
                summary=f"Execution failed: {str(e)[:50]}",
                total_time_ms=int((time.time() - start_time) * 1000),
            ))

        finally:
            try:
                self._persist_history_turn(
                    business_unit_id=business_unit_id,
                    agent_name=agent_name,
                    thread_id=thread_id,
                    user_input=user_input,
                    stream_messages=stream_messages,
                )
            except Exception as persist_error:
                logger.warning(
                    f"Failed to persist conversation history: {business_unit_id}/{agent_name}, thread_id={thread_id}, error={persist_error}"
                )

            if len(self._snapshots) > 20:
                oldest_keys = sorted(self._snapshots.keys())[:len(self._snapshots) - 20]
                for k in oldest_keys:
                    self._snapshots.pop(k, None)

    _INTERNAL_TOOL_NAMES = frozenset({"write_todos", "todo_write"})

    async def _stream_execution(
        self,
        agent,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        execution_id: str,
        agent_name: str,
        state: AgentRuntimeState,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> AsyncIterator[StreamMessage]:
        """Core streaming execution — translates LangGraph events to StreamMessage.

        Key notes:
        LangGraph stream_mode="messages" outputs incremental AIMessageChunks for tool_calls.
        The same tool_call spans multiple chunks:
          - 1st chunk: name="ls", id="call_xxx", args="" (or partial)
          - Subsequent chunks: name="", id="call_xxx", args="..." (incremental append)
        Therefore, tool_call_id must be used for deduplication and tracking.
        """
        accumulated_content = ""
        t = self._translator

        # tool_call_id -> tool_name: records the name of each tool_call (captured on first occurrence)
        tool_call_names: Dict[str, str] = {}
        # tool_call index -> tool_call_id (subsequent chunks may only have index)
        index_to_id: Dict[int, str] = {}
        # tool_call_ids for which a TOOL_CALL running event has been emitted
        emitted_tool_ids: set = set()
        # tool_call_ids for which a TOOL_CALL completed event has been emitted (avoid duplicates)
        completed_tool_ids: set = set()
        # Internal tool calls to filter out
        filtered_tool_ids: set = set()

        yield builder.thought("Analyzing your request...", mode="replace", phase="planning", icon="brain")

        try:
            async for chunk in self._stream_with_config(agent, input_data, config, stream_mode="messages"):
                if state.cancel_requested:
                    break
                if not (isinstance(chunk, tuple) and len(chunk) == 2):
                    continue

                message_chunk, metadata = chunk
                node_name = metadata.get("langgraph_node", "")
                chunk_type = getattr(message_chunk, 'type', '')

                # -- 1. AI text stream -> THOUGHT --
                if chunk_type != 'tool' and hasattr(message_chunk, 'content') and message_chunk.content:
                    content = self._extract_text_from_content(message_chunk.content)
                    if content:
                        accumulated_content += content
                        yield builder.thought(
                            content=content,
                            mode="append",
                            phase=t.detect_phase(node_name, content),
                            icon=t.detect_icon(node_name, content),
                        )
                        snapshot.thoughts.append({
                            "content": content,
                            "phase": t.detect_phase(node_name, content),
                            "timestamp": time.time(),
                        })

                # -- 2. Tool calls --
                # AIMessageChunk has two relevant attributes:
                #   tool_call_chunks: raw incremental fragments (args is str fragment, id may be empty)
                #   tool_calls:       parsed complete calls (args is dict, only present when JSON is complete)
                #
                # Strategy:
                # A) Use tool_call_chunks to: discover new tool_calls + accumulate args
                # B) Use tool_calls to: get fully parsed args (for parameter display)

                # A) Process incremental tool_call_chunks
                if hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
                    for tc in message_chunk.tool_call_chunks:
                        tc_name = (tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)) or ''
                        tc_args = (tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', None)) or ''
                        tc_id = (tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)) or ''
                        tc_idx = tc.get('index', None) if isinstance(tc, dict) else getattr(tc, 'index', None)

                        # Record name -> id mapping
                        if tc_name and tc_id:
                            tool_call_names[tc_id] = tc_name
                        # index -> id mapping (subsequent chunks may lack id, only have index)
                        if tc_id and tc_idx is not None:
                            index_to_id[tc_idx] = tc_id
                        if not tc_id and tc_idx is not None:
                            tc_id = index_to_id.get(tc_idx, '')

                        known_name = tool_call_names.get(tc_id, '') if tc_id else ''

                        # write_todos / todo_write -> mark as filtered
                        if known_name in self._INTERNAL_TOOL_NAMES or tc_name in self._INTERNAL_TOOL_NAMES:
                            if tc_id:
                                filtered_tool_ids.add(tc_id)
                            continue

                        # Already filtered id
                        if tc_id and tc_id in filtered_tool_ids:
                            continue

                        # Regular tool: first occurrence -> emit running (args may be incomplete, skip for now)
                        if tc_id and tc_id not in emitted_tool_ids:
                            display_name = known_name or tc_name or 'unknown'
                            tool_call_names.setdefault(tc_id, display_name)
                            emitted_tool_ids.add(tc_id)
                            yield builder.tool_call(
                                tool_name=display_name,
                                tool_call_id=tc_id,
                                status="running",
                                icon=t.tool_icon(display_name),
                            )

                # B) Process complete tool_calls (for write_todos full args)
                if hasattr(message_chunk, 'tool_calls') and message_chunk.tool_calls:
                    for tc in message_chunk.tool_calls:
                        tc_name = (tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)) or ''
                        tc_args = (tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', None)) or {}
                        tc_id = (tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)) or ''

                        if tc_name and tc_id:
                            tool_call_names[tc_id] = tc_name
                        known_name = tool_call_names.get(tc_id, '') if tc_id else ''

                        if known_name in self._INTERNAL_TOOL_NAMES or tc_name in self._INTERNAL_TOOL_NAMES:
                            if tc_id:
                                filtered_tool_ids.add(tc_id)
                            if isinstance(tc_args, dict) and tc_args:
                                tasks = t.parse_todo_args(tc_args)
                                if tasks:
                                    snapshot.tasks = tasks
                                    completed = sum(1 for tk in tasks if tk.status == TaskStatus.COMPLETED)
                                    progress = completed / len(tasks) if tasks else 0
                                    current_id = next((tk.id for tk in tasks if tk.status == TaskStatus.RUNNING), None)
                                    yield builder.task_list(tasks=tasks, current_task_id=current_id, progress=progress)
                            continue

                        if tc_id and tc_id in filtered_tool_ids:
                            continue

                        if tc_id and tc_id not in emitted_tool_ids:
                            display_name = known_name or tc_name or 'unknown'
                            tool_call_names.setdefault(tc_id, display_name)
                            emitted_tool_ids.add(tc_id)
                            tool_args = tc_args if isinstance(tc_args, dict) and tc_args else None
                            yield builder.tool_call(
                                tool_name=display_name,
                                tool_call_id=tc_id,
                                tool_args=tool_args,
                                status="running",
                                icon=t.tool_icon(display_name),
                                reason=t.extract_reason(tool_args),
                                expected_outcome=t.extract_expected_outcome(tool_args),
                            )

                # -- 3. Tool results (ToolMessage) --
                if chunk_type == 'tool':
                    tool_call_id = getattr(message_chunk, 'tool_call_id', '')
                    if tool_call_id in filtered_tool_ids:
                        continue
                    if tool_call_id and tool_call_id in completed_tool_ids:
                        continue

                    tool_content = getattr(message_chunk, 'content', '')
                    matched_name = tool_call_names.get(tool_call_id, '') or getattr(message_chunk, 'name', '') or 'unknown'

                    result_summary = self._summarize_tool_content(tool_content)
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
            logger.warning(f"Messages mode failed, falling back to values mode: {stream_error}")
            try:
                async for chunk in self._stream_with_config(agent, input_data, config, stream_mode="values"):
                    if state.cancel_requested:
                        break
                    if isinstance(chunk, dict) and "messages" in chunk:
                        messages = chunk["messages"]
                        if not messages:
                            continue

                        for msg in messages:
                            msg_type = getattr(msg, "type", None) if not isinstance(msg, dict) else msg.get("type")

                            if msg_type == "ai":
                                tool_calls = getattr(msg, "tool_calls", None) if not isinstance(msg, dict) else msg.get("tool_calls")
                                tool_calls = tool_calls or []
                                for tc in tool_calls:
                                    tc_name = (tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)) or ''
                                    tc_args = (tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', None)) or {}
                                    tc_id = (tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)) or ''

                                    if tc_name and tc_id:
                                        tool_call_names[tc_id] = tc_name
                                    known_name = tool_call_names.get(tc_id, '') if tc_id else ''

                                    if known_name in self._INTERNAL_TOOL_NAMES or tc_name in self._INTERNAL_TOOL_NAMES:
                                        if tc_id:
                                            filtered_tool_ids.add(tc_id)
                                        if isinstance(tc_args, dict) and tc_args:
                                            tasks = t.parse_todo_args(tc_args)
                                            if tasks:
                                                snapshot.tasks = tasks
                                                completed = sum(1 for tk in tasks if tk.status == TaskStatus.COMPLETED)
                                                progress = completed / len(tasks) if tasks else 0
                                                current_id = next((tk.id for tk in tasks if tk.status == TaskStatus.RUNNING), None)
                                                yield builder.task_list(tasks=tasks, current_task_id=current_id, progress=progress)
                                        continue

                                    if tc_id and tc_id in filtered_tool_ids:
                                        continue

                                    if tc_id and tc_id not in emitted_tool_ids:
                                        display_name = known_name or tc_name or 'unknown'
                                        tool_call_names.setdefault(tc_id, display_name)
                                        emitted_tool_ids.add(tc_id)
                                        tool_args = tc_args if isinstance(tc_args, dict) and tc_args else None
                                        yield builder.tool_call(
                                            tool_name=display_name,
                                            tool_call_id=tc_id,
                                            tool_args=tool_args,
                                            status="running",
                                            icon=t.tool_icon(display_name),
                                            reason=t.extract_reason(tool_args),
                                            expected_outcome=t.extract_expected_outcome(tool_args),
                                        )

                            if msg_type == "tool":
                                tool_call_id = getattr(msg, "tool_call_id", None) if not isinstance(msg, dict) else msg.get("tool_call_id")
                                tool_call_id = tool_call_id or ""
                                if tool_call_id and (tool_call_id in filtered_tool_ids or tool_call_id in completed_tool_ids):
                                    continue

                                tool_name = tool_call_names.get(tool_call_id, '') or (
                                    getattr(msg, "name", None) if not isinstance(msg, dict) else msg.get("name")
                                ) or 'unknown'
                                tool_content = getattr(msg, "content", None) if not isinstance(msg, dict) else msg.get("content")
                                result_summary = self._summarize_tool_content(tool_content)
                                yield builder.tool_call(
                                    tool_name=tool_name,
                                    tool_call_id=tool_call_id or None,
                                    tool_result=result_summary or None,
                                    status="completed",
                                    icon="check",
                                )
                                if tool_call_id:
                                    completed_tool_ids.add(tool_call_id)

                        last_msg = messages[-1]
                        last_content = getattr(last_msg, 'content', None) if not isinstance(last_msg, dict) else last_msg.get('content')
                        if last_content:
                            content = self._extract_text_from_content(last_content)
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
                logger.warning(f"Values mode failed, falling back to non-streaming invoke: {values_error}")
                output = await self._invoke_non_stream(agent, input_data, config)
                if output and output != accumulated_content:
                    accumulated_content = output

        # -- Final output (Markdown direct output) --
        for msg in self._emit_final_output(accumulated_content, builder, snapshot):
            yield msg

    async def execute_agent(
            self,
            business_unit_id: str,
            agent_name: str,
            user_input: str,
            context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamMessage]:
        """Stream-execute an Agent — outputs StreamMessage packets"""
        key = self._get_agent_key(business_unit_id, agent_name)
        execution_id = agent_name
        start_time = time.time()
        builder = StreamMessageBuilder(execution_id)

        snapshot = ExecutionSnapshot(execution_id=execution_id)
        self._snapshots[execution_id] = snapshot

        yield builder.status("Initializing Agent...", icon="loading")

        try:
            state = self._agents.get(key)
            if not state or state.status != AgentStatus.READY:
                yield builder.status("Loading Agent...", icon="loading")
            state = await self._ensure_ready_agent(business_unit_id, agent_name)
            await self._mark_agent_running(state, execution_id)

            agent = state.agent_instance
            yield builder.status("Agent is ready, starting execution...", icon="play")

            input_data = {"messages": [{"role": "user", "content": user_input}]}
            config = self._build_runnable_config(execution_id, agent_name)
            yield builder.thought("Processing request...", mode="replace", phase="analyzing", icon="brain")
            output = await self._invoke_non_stream(agent, input_data, config)
            yield output
            await self._mark_agent_ready(key, increase_execution_count=True)

            snapshot.status = "completed"

            total_time_ms = int((time.time() - start_time) * 1000)
            yield builder.done(
                summary=self._generate_summary(snapshot),
                total_steps=len([t for t in snapshot.tasks if t.status == TaskStatus.COMPLETED]),
                total_time_ms=total_time_ms,
            )

        except asyncio.CancelledError:
            snapshot.status = "cancelled"
            yield builder.status("Execution cancelled", icon="cancel")
            yield builder.done(summary="Execution cancelled")

        except Exception as e:
            logger.error(f"Agent streaming execution failed: {key}, error={e}")
            await self._mark_agent_failed(key)

            snapshot.status = "failed"
            yield builder.error(
                message=str(e),
                error_type=type(e).__name__,
                suggestion="Please check Agent configuration or retry",
                retryable=True,
                traceback=tb_module.format_exc(),
            )
            yield builder.done(
                summary=f"Execution failed: {str(e)[:50]}",
                total_time_ms=int((time.time() - start_time) * 1000),
            )

        finally:
            if len(self._snapshots) > 20:
                oldest_keys = sorted(self._snapshots.keys())[:len(self._snapshots) - 20]
                for k in oldest_keys:
                    self._snapshots.pop(k, None)

    async def _invoke_non_stream(
        self,
        agent,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> str:
        """Invoke the non-streaming interface and extract the final text output"""
        bound_agent = self._bind_agent_config(agent, config)
        result = await bound_agent.ainvoke(input_data)

        if result is None:
            return ""

        # Handle cases where some model SDKs return AsyncStream in non-streaming call paths
        if hasattr(result, "__aiter__") and not isinstance(result, (str, dict)):
            stream_text_parts: List[str] = []
            async for chunk in result:
                chunk_content = getattr(chunk, "content", None)
                if chunk_content:
                    stream_text_parts.append(self._extract_text_from_content(chunk_content))
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
            return self._extract_output(result)

        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content

        return str(result)

    def _emit_final_output(
        self,
        accumulated_content: str,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> List[StreamMessage]:
        """Emit final Markdown text (only when streaming phase did not output completely)"""
        if not accumulated_content.strip():
            return []

        if snapshot.thoughts:
            emitted_text = "".join(str(t.get("content", "")) for t in snapshot.thoughts)
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

    def _generate_summary(self, snapshot: ExecutionSnapshot) -> str:
        task_count = len(snapshot.tasks)
        artifact_count = len(snapshot.artifacts)
        if task_count > 0:
            completed = sum(1 for t in snapshot.tasks if t.status == TaskStatus.COMPLETED)
            return f"Completed {completed}/{task_count} tasks, produced {artifact_count} artifacts"
        if artifact_count > 0:
            return f"Produced {artifact_count} artifacts"
        return "Execution completed"

    def _extract_output(self, result: Dict[str, Any]) -> str:
        if not result:
            return ""
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, 'content'):
                return msg.content
            if isinstance(msg, dict) and "content" in msg:
                return msg["content"]
        if "output" in result:
            return str(result["output"])
        return ""

    # ================================================================
    # Reconnection Snapshot
    # ================================================================

    def get_execution_snapshot(self, execution_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self._snapshots.get(execution_id)
        if not snapshot:
            return None
        return SnapshotPayload(
            thoughts=snapshot.thoughts,
            tasks=snapshot.tasks,
            artifacts=snapshot.artifacts,
            status=snapshot.status,
            execution_id=execution_id,
        ).model_dump(exclude_none=True)

    # ================================================================
    # Agent Management
    # ================================================================

    async def get_agent_status(self, business_unit_id: str, agent_name: str) -> Dict[str, Any]:
        key = self._get_agent_key(business_unit_id, agent_name)
        state = self._agents.get(key)
        if not state:
            return {"status": "not_loaded", "agent_name": agent_name, "business_unit_id": business_unit_id}
        return {
            "status": state.status.value,
            "agent_name": state.agent_name,
            "business_unit_id": state.business_unit_id,
            "execution_id": state.current_execution_id,
            "loaded_at": state.loaded_at,
            "last_execution_at": state.last_execution_at,
            "execution_count": state.execution_count,
            "error_count": state.error_count,
        }

    async def cancel_agent(self, business_unit_id: str, agent_name: str) -> bool:
        key = self._get_agent_key(business_unit_id, agent_name)
        async with self._lock:
            state = self._agents.get(key)
            if state and state.status == AgentStatus.RUNNING:
                state.cancel_requested = True
                logger.info(f"Requested cancellation of Agent execution: {key}")
                return True
        return False

    async def clear_agent_context(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: Optional[str] = None,
    ) -> bool:
        """Clear Agent conversation context (LangGraph thread) and local history."""
        key = self._get_agent_key(business_unit_id, agent_name)
        resolved_thread_id = self._resolve_thread_id(agent_name, {"thread_id": thread_id} if thread_id else None)
        state = self._agents.get(key)

        context_cleared = True
        if state and state.agent_instance:
            checkpointer = getattr(state.agent_instance, "checkpointer", None)
            if not checkpointer:
                logger.warning(f"Agent checkpointer does not exist, skipping context cleanup: {key}")
                context_cleared = False
            else:
                adelete_thread = getattr(checkpointer, "adelete_thread", None)
                if not callable(adelete_thread):
                    logger.warning(f"Checkpointer does not support adelete_thread, skipping context cleanup: {key}")
                    context_cleared = False
                else:
                    await adelete_thread(resolved_thread_id)

        self._snapshots.pop(resolved_thread_id, None)

        history_cleared = True
        history_file = self._get_history_file_path(business_unit_id, agent_name, resolved_thread_id)
        if history_file.exists():
            try:
                history_file.unlink()
            except Exception as delete_error:
                history_cleared = False
                logger.warning(
                    f"Failed to delete conversation history file: {history_file}, error={delete_error}"
                )

        logger.info(
            f"Agent conversation context cleared: {key}, thread_id={resolved_thread_id}, context={context_cleared}, history={history_cleared}"
        )
        return context_cleared and history_cleared

    async def unload_agent(self, business_unit_id: str, agent_name: str) -> bool:
        key = self._get_agent_key(business_unit_id, agent_name)
        async with self._lock:
            if key not in self._agents:
                return False
            state = self._agents[key]
            if state.status == AgentStatus.RUNNING:
                state.cancel_requested = True
                await asyncio.sleep(0.1)

            agent_instance = state.agent_instance
            if agent_instance is not None:
                engine = self._engine or self._ensure_engine()
                close_resources = getattr(engine, "close_agent_resources", None)
                if callable(close_resources):
                    try:
                        result = close_resources(agent_instance)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.warning(f"Failed to close Agent resources: {key}, error={e}")

            state.agent_instance = None
            state.status = AgentStatus.UNLOADED
            del self._agents[key]
            logger.info(f"Agent unloaded: {key}")
            return True

    def list_loaded_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "business_unit_id": s.business_unit_id,
                "agent_name": s.agent_name,
                "status": s.status.value,
                "loaded_at": s.loaded_at,
                "execution_count": s.execution_count,
            }
            for s in self._agents.values()
        ]


# Global service instance
_service_instance: Optional[AgentRuntimeService] = None


def get_agent_runtime_service() -> AgentRuntimeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentRuntimeService()
    return _service_instance
