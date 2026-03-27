"""
Agent 运行时服务

负责管理 Agent 的加载、执行、状态和生命周期。
使用 StreamMessage 协议输出 THOUGHT/TASK_LIST/ARTIFACT/STATUS/ERROR/DONE 消息包。
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
# 状态定义
# ============================================================

class AgentStatus(str, Enum):
    """Agent 运行状态"""
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
    """Agent 运行时状态"""
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
    """执行快照 — 用于断线重连恢复"""
    execution_id: str
    thoughts: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[TaskItem] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    last_seq: int = 0


# ============================================================
# MessageTranslator — LangGraph 事件 → StreamMessage
# ============================================================

class MessageTranslator:
    """将 LangGraph 的原始流式事件翻译为 StreamMessage 消息包"""

    @staticmethod
    def detect_phase(node_name: str, content: str) -> str:
        lower = content[:50].lower()
        if "plan" in node_name.lower() or "plan" in lower:
            return "planning"
        if "reflect" in node_name.lower():
            return "reflecting"
        if "search" in lower or "搜索" in lower:
            return "searching"
        if "code" in lower or "代码" in lower:
            return "coding"
        return "analyzing"

    @staticmethod
    def detect_icon(node_name: str, content: str) -> str:
        lower = content[:100].lower()
        if "search" in lower or "查找" in lower or "搜索" in lower:
            return "search"
        if "code" in lower or "代码" in lower:
            return "code"
        if "plan" in lower or "计划" in lower:
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
                    title=todo.get("content") or todo.get("title") or todo.get("description") or f"任务 {i + 1}",
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
    """Agent 运行时服务 — 管理 Agent 完整生命周期"""

    def __init__(self):
        logger.info("初始化 AgentRuntimeService")
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
            logger.warning(f"绑定 Agent 运行配置失败，回退到显式传参: {bind_error}")
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
            logger.warning(f"读取历史记录失败，将重置文件: {history_file}, error={read_error}")
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
    # Agent 加载
    # ================================================================

    async def load_agent(
        self,
        business_unit_id: str,
        agent_name: str,
        agent_path: Optional[str] = None
    ) -> AgentRuntimeState:
        """加载 Agent"""
        key = self._get_agent_key(business_unit_id, agent_name)

        async with self._lock:
            if key in self._agents:
                state = self._agents[key]
                if state.status in (AgentStatus.READY, AgentStatus.RUNNING):
                    logger.info(f"Agent 已加载: {key}")
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
            logger.info(f"开始加载 Agent: {key}, path={agent_path}")
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
                logger.error(f"初始化任务目录失败: {task_dir}, error={mkdir_error}")
                raise RuntimeError(f"初始化任务目录失败: {task_dir}") from mkdir_error

            async with self._lock:
                state.agent_instance = agent
                state.status = AgentStatus.READY
                state.loaded_at = datetime.now().isoformat()

            logger.info(f"Agent 加载成功: {key}")
            return state

        except Exception as e:
            logger.error(f"Agent 加载失败: {key}, error={e}")
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
    # 流式执行 — 输出 StreamMessage 消息包
    # ================================================================

    async def execute_agent_stream(
        self,
        business_unit_id: str,
        agent_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamMessage]:
        """流式执行 Agent — 输出 StreamMessage 消息包"""
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

        yield record_stream_message(builder.status("正在初始化 Agent...", icon="loading"))

        try:
            state = self._agents.get(key)
            if not state or state.status != AgentStatus.READY:
                yield record_stream_message(builder.status("正在加载 Agent...", icon="loading"))
            state = await self._ensure_ready_agent(business_unit_id, agent_name)
            await self._mark_agent_running(state, execution_id)

            agent = state.agent_instance
            yield record_stream_message(builder.status("Agent 已就绪，开始执行...", icon="play"))

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
            yield record_stream_message(builder.status("执行已取消", icon="cancel"))
            yield record_stream_message(builder.done(summary="执行已取消"))

        except Exception as e:
            logger.error(f"Agent 流式执行失败: {key}, error={e}")
            await self._mark_agent_failed(key)

            snapshot.status = "failed"
            yield record_stream_message(builder.error(
                message=str(e),
                error_type=type(e).__name__,
                suggestion="请检查 Agent 配置或重试",
                retryable=True,
                traceback=tb_module.format_exc(),
            ))
            yield record_stream_message(builder.done(
                summary=f"执行失败: {str(e)[:50]}",
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
                    f"保存对话历史失败: {business_unit_id}/{agent_name}, thread_id={thread_id}, error={persist_error}"
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
        """核心流式执行 — 翻译 LangGraph 事件为 StreamMessage

        关键说明：
        LangGraph stream_mode="messages" 以增量 AIMessageChunk 方式输出 tool_calls。
        同一个 tool_call 会跨多个 chunk：
          - 第1个 chunk: name="ls", id="call_xxx", args="" (或部分)
          - 后续 chunk: name="", id="call_xxx", args="..." (增量追加)
        因此必须用 tool_call_id 做去重和跟踪。
        """
        accumulated_content = ""
        t = self._translator

        # tool_call_id → tool_name：记录每个 tool_call 的名称（首次出现时记录）
        tool_call_names: Dict[str, str] = {}
        # tool_call index → tool_call_id（tool_call_chunks 中后续 chunk 可能只有 index）
        index_to_id: Dict[int, str] = {}
        # 已发送 TOOL_CALL running 事件的 tool_call_id
        emitted_tool_ids: set = set()
        # 已发送 TOOL_CALL completed 事件的 tool_call_id（避免重复）
        completed_tool_ids: set = set()
        # 需要过滤的内部工具调用
        filtered_tool_ids: set = set()

        yield builder.thought("正在分析您的请求...", mode="replace", phase="planning", icon="brain")

        try:
            async for chunk in self._stream_with_config(agent, input_data, config, stream_mode="messages"):
                if state.cancel_requested:
                    break
                if not (isinstance(chunk, tuple) and len(chunk) == 2):
                    continue

                message_chunk, metadata = chunk
                node_name = metadata.get("langgraph_node", "")
                chunk_type = getattr(message_chunk, 'type', '')

                # ── 1. AI 文本流 → THOUGHT ──
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

                # ── 2. 工具调用 ──
                # AIMessageChunk 有两个相关属性：
                #   tool_call_chunks: 原始增量片段（args 是 str 片段，id 可能为空）
                #   tool_calls:       解析后的完整调用（args 是 dict，仅当 JSON 完整时存在）
                #
                # 策略：
                # A) 用 tool_call_chunks 来：发现新 tool_call + 累积 AgentResponse args
                # B) 用 tool_calls 来：获取完整解析的 args（用于普通工具的参数展示）

                # A) 处理增量 tool_call_chunks
                if hasattr(message_chunk, 'tool_call_chunks') and message_chunk.tool_call_chunks:
                    for tc in message_chunk.tool_call_chunks:
                        # 注意：后续 chunk 中 name/id 可能是 None（不是空字符串）
                        tc_name = (tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)) or ''
                        tc_args = (tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', None)) or ''
                        tc_id = (tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)) or ''
                        tc_idx = tc.get('index', None) if isinstance(tc, dict) else getattr(tc, 'index', None)

                        # 记录 name→id 映射
                        if tc_name and tc_id:
                            tool_call_names[tc_id] = tc_name
                        # index→id 映射（后续 chunk 可能没有 id 只有 index）
                        if tc_id and tc_idx is not None:
                            index_to_id[tc_idx] = tc_id
                        if not tc_id and tc_idx is not None:
                            tc_id = index_to_id.get(tc_idx, '')

                        known_name = tool_call_names.get(tc_id, '') if tc_id else ''

                        # write_todos / todo_write → 标记过滤
                        if known_name in self._INTERNAL_TOOL_NAMES or tc_name in self._INTERNAL_TOOL_NAMES:
                            if tc_id:
                                filtered_tool_ids.add(tc_id)
                            continue

                        # 已过滤 id
                        if tc_id and tc_id in filtered_tool_ids:
                            continue

                        # 普通工具：首次出现 → 发 running（args 此时可能不完整，先不传）
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

                # B) 处理完整 tool_calls（用于 write_todos 的完整 args）
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

                # ── 3. 工具结果（ToolMessage） ──
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
            logger.warning(f"messages 模式失败，回退到 values 模式: {stream_error}")
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
                logger.warning(f"values 模式失败，回退到非流式 invoke: {values_error}")
                output = await self._invoke_non_stream(agent, input_data, config)
                if output and output != accumulated_content:
                    accumulated_content = output

        # ── 最终输出（Markdown 直出） ──
        for msg in self._emit_final_output(accumulated_content, builder, snapshot):
            yield msg
    async def execute_agent(
            self,
            business_unit_id: str,
            agent_name: str,
            user_input: str,
            context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamMessage]:
        """流式执行 Agent — 输出 StreamMessage 消息包"""
        key = self._get_agent_key(business_unit_id, agent_name)
        execution_id = agent_name
        start_time = time.time()
        builder = StreamMessageBuilder(execution_id)

        snapshot = ExecutionSnapshot(execution_id=execution_id)
        self._snapshots[execution_id] = snapshot

        yield builder.status("正在初始化 Agent...", icon="loading")

        try:
            state = self._agents.get(key)
            if not state or state.status != AgentStatus.READY:
                yield builder.status("正在加载 Agent...", icon="loading")
            state = await self._ensure_ready_agent(business_unit_id, agent_name)
            await self._mark_agent_running(state, execution_id)

            agent = state.agent_instance
            yield builder.status("Agent 已就绪，开始执行...", icon="play")

            input_data = {"messages": [{"role": "user", "content": user_input}]}
            config = self._build_runnable_config(execution_id, agent_name)
            yield builder.thought("正在处理请求...", mode="replace", phase="analyzing", icon="brain")
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
            yield builder.status("执行已取消", icon="cancel")
            yield builder.done(summary="执行已取消")

        except Exception as e:
            logger.error(f"Agent 流式执行失败: {key}, error={e}")
            await self._mark_agent_failed(key)

            snapshot.status = "failed"
            yield builder.error(
                message=str(e),
                error_type=type(e).__name__,
                suggestion="请检查 Agent 配置或重试",
                retryable=True,
                traceback=tb_module.format_exc(),
            )
            yield builder.done(
                summary=f"执行失败: {str(e)[:50]}",
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
        """调用非流式接口并提取最终文本输出"""
        bound_agent = self._bind_agent_config(agent, config)
        result = await bound_agent.ainvoke(input_data)

        if result is None:
            return ""

        # 兼容部分模型 SDK 在非流式调用路径返回 AsyncStream 的情况
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
        """补发最终 Markdown 文本（仅在流式阶段未完整输出时）"""
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
            return f"完成 {completed}/{task_count} 个任务，产出 {artifact_count} 个制品"
        if artifact_count > 0:
            return f"已产出 {artifact_count} 个制品"
        return "执行完成"

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
    # 重连快照
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
    # Agent 管理
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
                logger.info(f"请求取消 Agent 执行: {key}")
                return True
        return False

    async def clear_agent_context(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: Optional[str] = None,
    ) -> bool:
        """清理 Agent 对话上下文（LangGraph thread）与本地历史。"""
        key = self._get_agent_key(business_unit_id, agent_name)
        resolved_thread_id = self._resolve_thread_id(agent_name, {"thread_id": thread_id} if thread_id else None)
        state = self._agents.get(key)

        context_cleared = True
        if state and state.agent_instance:
            checkpointer = getattr(state.agent_instance, "checkpointer", None)
            if not checkpointer:
                logger.warning(f"Agent checkpointer 不存在，跳过上下文清理: {key}")
                context_cleared = False
            else:
                adelete_thread = getattr(checkpointer, "adelete_thread", None)
                if not callable(adelete_thread):
                    logger.warning(f"checkpointer 不支持 adelete_thread，跳过上下文清理: {key}")
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
                    f"删除对话历史文件失败: {history_file}, error={delete_error}"
                )

        logger.info(
            f"Agent 对话上下文清理完成: {key}, thread_id={resolved_thread_id}, context={context_cleared}, history={history_cleared}"
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
                        logger.warning(f"关闭 Agent 资源失败: {key}, error={e}")

            state.agent_instance = None
            state.status = AgentStatus.UNLOADED
            del self._agents[key]
            logger.info(f"Agent 已卸载: {key}")
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


# 全局服务实例
_service_instance: Optional[AgentRuntimeService] = None


def get_agent_runtime_service() -> AgentRuntimeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentRuntimeService()
    return _service_instance
