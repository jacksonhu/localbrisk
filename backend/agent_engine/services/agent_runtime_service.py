"""Agent runtime service orchestrating lifecycle and execution streaming."""

from __future__ import annotations

import asyncio
import logging
import time
import traceback as tb_module
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from ..core.exceptions import serialize_exception
from ..core.stream_protocol import MessageType, SnapshotPayload, StreamMessage, StreamMessageBuilder, TaskStatus
from ..monitoring import emit_runtime_event, get_logging_context, scoped_logging_context
from .execution_stream import AgentExecutionStreamer
from .history_store import ConversationHistoryStore
from .message_translator import MessageTranslator
from .runtime_state import AgentRuntimeState, AgentStatus, ExecutionSnapshot

logger = logging.getLogger(__name__)


class AgentRuntimeService:
    """Manage agent lifecycle, execution state, and stream output."""

    def __init__(self):
        logger.info("Initializing AgentRuntimeService")
        self._agents: Dict[str, AgentRuntimeState] = {}
        self._engine = None
        self._lock = asyncio.Lock()
        self._snapshots: Dict[str, ExecutionSnapshot] = {}
        self._translator = MessageTranslator()
        self._execution_streamer = AgentExecutionStreamer(self._translator)
        self._history_store = ConversationHistoryStore(self._get_agent_path)

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

    @staticmethod
    def _context_value(context: Optional[Dict[str, Any]], key: str) -> Optional[str]:
        if not isinstance(context, dict):
            return None
        raw = context.get(key)
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    def _build_observability_context(
        self,
        *,
        business_unit_id: str,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        component: str,
        ensure_request_id: bool = True,
        **extra: Any,
    ) -> Dict[str, Any]:
        current = get_logging_context()
        request_id = self._context_value(context, "request_id") or current.get("request_id")
        if ensure_request_id and not request_id:
            request_id = str(uuid.uuid4())
        session_id = self._context_value(context, "session_id") or current.get("session_id") or thread_id or execution_id or agent_name
        payload = {
            "request_id": request_id,
            "session_id": session_id,
            "business_unit_id": business_unit_id,
            "agent_id": agent_name,
            "thread_id": thread_id,
            "execution_id": execution_id,
            "component": component,
            **extra,
        }
        return {key: value for key, value in payload.items() if value is not None and value != ""}

    @staticmethod
    def _build_error_payload(exc: Exception) -> Dict[str, Any]:
        return serialize_exception(exc)

    def _build_runnable_config(self, thread_id: str, agent_name: str) -> Dict[str, Any]:
        return self._execution_streamer.build_runnable_config(thread_id, agent_name)

    def _bind_agent_config(self, agent: Any, config: Dict[str, Any]):
        return self._execution_streamer.bind_agent_config(agent, config)

    def _stream_with_config(self, agent: Any, input_data: Dict[str, Any], config: Dict[str, Any], stream_mode: str):
        return self._execution_streamer.stream_with_config(agent, input_data, config, stream_mode)

    def _get_agent_path(self, business_unit_id: str, agent_name: str) -> Path:
        key = self._get_agent_key(business_unit_id, agent_name)
        state = self._agents.get(key)
        if state and state.agent_path:
            return Path(state.agent_path)

        from app.core.config import settings

        return settings.CATALOGS_DIR / business_unit_id / "agents" / agent_name

    async def get_conversation_history(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_thread_id = self._resolve_thread_id(agent_name, {"thread_id": thread_id} if thread_id else None)
        with scoped_logging_context(
            **self._build_observability_context(
                business_unit_id=business_unit_id,
                agent_name=agent_name,
                thread_id=resolved_thread_id,
                execution_id=resolved_thread_id,
                component="agent_runtime.history",
            )
        ):
            emit_runtime_event("agent.history.requested")
            return self._history_store.get_conversation_history(business_unit_id, agent_name, resolved_thread_id)

    async def load_agent(
        self,
        business_unit_id: str,
        agent_name: str,
        agent_path: Optional[str] = None,
    ) -> AgentRuntimeState:
        """Load an agent instance into runtime."""
        key = self._get_agent_key(business_unit_id, agent_name)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            component="agent_runtime.load",
        )

        with scoped_logging_context(**operation_context):
            emit_runtime_event("agent.load.started", agent_path=agent_path)
            async with self._lock:
                if key in self._agents:
                    state = self._agents[key]
                    if state.status in (AgentStatus.READY, AgentStatus.RUNNING):
                        logger.info("Agent already loaded: %s", key)
                        emit_runtime_event("agent.load.reused", status=state.status.value)
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
                engine = self._ensure_engine()
                logger.info("Loading agent %s from %s", key, agent_path)
                agent = await engine.build_agent(
                    agent_path=agent_path,
                    business_unit_id=business_unit_id,
                    debug=False,
                )

                task_dir = Path(agent_path) / "output" / ".task"
                task_dir.mkdir(parents=True, exist_ok=True)

                async with self._lock:
                    state.agent_instance = agent
                    state.status = AgentStatus.READY
                    state.loaded_at = datetime.now().isoformat()

                logger.info("Agent loaded successfully: %s", key)
                emit_runtime_event("agent.load.completed", status=state.status.value)
                return state
            except Exception as exc:
                async with self._lock:
                    state.status = AgentStatus.FAILED
                    state.error_count += 1
                error_payload = self._build_error_payload(exc)
                logger.exception("Failed to load agent: %s", key)
                emit_runtime_event(
                    "agent.load.failed",
                    level=logging.ERROR,
                    error_code=error_payload.get("error_code"),
                    error_type=error_payload.get("error_type"),
                    suggestion=error_payload.get("suggestion"),
                    message=error_payload.get("message"),
                )
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
            state.current_execution_id = None
            if increase_execution_count:
                state.execution_count += 1

    async def _mark_agent_failed(self, key: str) -> None:
        async with self._lock:
            state = self._agents.get(key)
            if not state:
                return
            state.status = AgentStatus.READY
            state.current_execution_id = None
            state.error_count += 1

    async def execute_agent_stream(
        self,
        business_unit_id: str,
        agent_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """Execute an agent with streaming StreamMessage output."""
        key = self._get_agent_key(business_unit_id, agent_name)
        thread_id = self._resolve_thread_id(agent_name, context)
        execution_id = thread_id
        start_time = time.time()
        builder = StreamMessageBuilder(execution_id)
        snapshot = ExecutionSnapshot(execution_id=execution_id)
        self._snapshots[execution_id] = snapshot
        stream_messages: List[Dict[str, Any]] = []
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            context=context,
            execution_id=execution_id,
            thread_id=thread_id,
            component="agent_runtime.stream",
        )

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

        with scoped_logging_context(**operation_context):
            emit_runtime_event(
                "agent.execution.started",
                mode="stream",
                input_length=len(user_input),
            )
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
                async for message in self._stream_execution(
                    agent,
                    input_data,
                    config,
                    execution_id,
                    agent_name,
                    state,
                    builder,
                    snapshot,
                ):
                    yield record_stream_message(message)

                await self._mark_agent_ready(key, increase_execution_count=True)
                snapshot.status = "completed"
                total_time_ms = int((time.time() - start_time) * 1000)
                emit_runtime_event(
                    "agent.execution.completed",
                    mode="stream",
                    duration_ms=total_time_ms,
                    total_steps=len([task for task in snapshot.tasks if task.status == TaskStatus.COMPLETED]),
                    artifact_count=len(snapshot.artifacts),
                )
                yield record_stream_message(
                    builder.done(
                        summary=self._generate_summary(snapshot),
                        total_steps=len([task for task in snapshot.tasks if task.status == TaskStatus.COMPLETED]),
                        total_time_ms=total_time_ms,
                    )
                )
            except asyncio.CancelledError:
                snapshot.status = "cancelled"
                emit_runtime_event(
                    "agent.execution.cancelled",
                    mode="stream",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                yield record_stream_message(builder.status("Execution cancelled", icon="cancel"))
                yield record_stream_message(builder.done(summary="Execution cancelled"))
            except Exception as exc:
                error_payload = self._build_error_payload(exc)
                logger.error("Agent streaming execution failed: %s, error=%s", key, exc)
                await self._mark_agent_failed(key)
                snapshot.status = "failed"
                emit_runtime_event(
                    "agent.execution.failed",
                    level=logging.ERROR,
                    mode="stream",
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_code=error_payload.get("error_code"),
                    error_type=error_payload.get("error_type"),
                    suggestion=error_payload.get("suggestion"),
                    message=error_payload.get("message"),
                )
                yield record_stream_message(
                    builder.error(
                        message=error_payload.get("message", str(exc)),
                        error_type=error_payload.get("error_type", type(exc).__name__),
                        error_code=error_payload.get("error_code"),
                        suggestion=error_payload.get("suggestion"),
                        retryable=bool(error_payload.get("retryable", True)),
                        traceback=tb_module.format_exc(),
                    )
                )
                yield record_stream_message(
                    builder.done(
                        summary=f"Execution failed: {str(exc)[:50]}",
                        total_time_ms=int((time.time() - start_time) * 1000),
                    )
                )
            finally:
                try:
                    self._history_store.persist_history_turn(
                        business_unit_id=business_unit_id,
                        agent_name=agent_name,
                        thread_id=thread_id,
                        user_input=user_input,
                        stream_messages=stream_messages,
                    )
                except Exception as persist_error:
                    logger.warning(
                        "Failed to persist conversation history for %s/%s thread %s: %s",
                        business_unit_id,
                        agent_name,
                        thread_id,
                        persist_error,
                    )
                    emit_runtime_event(
                        "agent.history.persist_failed",
                        level=logging.WARNING,
                        error_type=type(persist_error).__name__,
                        message=str(persist_error),
                    )

                if len(self._snapshots) > 20:
                    oldest_keys = sorted(self._snapshots.keys())[: len(self._snapshots) - 20]
                    for snapshot_key in oldest_keys:
                        self._snapshots.pop(snapshot_key, None)

    async def _stream_execution(
        self,
        agent: Any,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        execution_id: str,
        agent_name: str,
        state: AgentRuntimeState,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> AsyncIterator[StreamMessage]:
        del execution_id, agent_name
        async for message in self._execution_streamer.stream_execution(agent, input_data, config, state.agent_name, state, builder, snapshot):
            yield message

    async def execute_agent(
        self,
        business_unit_id: str,
        agent_name: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """Execute an agent and return a non-streaming StreamMessage sequence."""
        thread_id = self._resolve_thread_id(agent_name, context)
        execution_id = thread_id
        key = self._get_agent_key(business_unit_id, agent_name)
        start_time = time.time()
        builder = StreamMessageBuilder(execution_id)
        snapshot = ExecutionSnapshot(execution_id=execution_id)
        self._snapshots[execution_id] = snapshot
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            context=context,
            execution_id=execution_id,
            thread_id=thread_id,
            component="agent_runtime.invoke",
        )

        with scoped_logging_context(**operation_context):
            emit_runtime_event(
                "agent.execution.started",
                mode="invoke",
                input_length=len(user_input),
            )
            yield builder.status("Initializing Agent...", icon="loading")
            try:
                state = self._agents.get(key)
                if not state or state.status != AgentStatus.READY:
                    yield builder.status("Loading Agent...", icon="loading")
                state = await self._ensure_ready_agent(business_unit_id, agent_name)
                await self._mark_agent_running(state, execution_id)

                input_data = {"messages": [{"role": "user", "content": user_input}]}
                config = self._build_runnable_config(thread_id, agent_name)
                yield builder.thought("Processing request...", mode="replace", phase="analyzing", icon="brain")
                output = await self._invoke_non_stream(state.agent_instance, input_data, config)
                if output:
                    yield builder.thought(output, mode="replace", phase="done", icon="check")
                await self._mark_agent_ready(key, increase_execution_count=True)

                snapshot.status = "completed"
                total_time_ms = int((time.time() - start_time) * 1000)
                emit_runtime_event(
                    "agent.execution.completed",
                    mode="invoke",
                    duration_ms=total_time_ms,
                    total_steps=len([task for task in snapshot.tasks if task.status == TaskStatus.COMPLETED]),
                    artifact_count=len(snapshot.artifacts),
                )
                yield builder.done(
                    summary=self._generate_summary(snapshot),
                    total_steps=len([task for task in snapshot.tasks if task.status == TaskStatus.COMPLETED]),
                    total_time_ms=total_time_ms,
                )
            except asyncio.CancelledError:
                snapshot.status = "cancelled"
                emit_runtime_event(
                    "agent.execution.cancelled",
                    mode="invoke",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                yield builder.status("Execution cancelled", icon="cancel")
                yield builder.done(summary="Execution cancelled")
            except Exception as exc:
                error_payload = self._build_error_payload(exc)
                logger.error("Agent execution failed: %s, error=%s", key, exc)
                await self._mark_agent_failed(key)
                snapshot.status = "failed"
                emit_runtime_event(
                    "agent.execution.failed",
                    level=logging.ERROR,
                    mode="invoke",
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_code=error_payload.get("error_code"),
                    error_type=error_payload.get("error_type"),
                    suggestion=error_payload.get("suggestion"),
                    message=error_payload.get("message"),
                )
                yield builder.error(
                    message=error_payload.get("message", str(exc)),
                    error_type=error_payload.get("error_type", type(exc).__name__),
                    error_code=error_payload.get("error_code"),
                    suggestion=error_payload.get("suggestion"),
                    retryable=bool(error_payload.get("retryable", True)),
                    traceback=tb_module.format_exc(),
                )
                yield builder.done(
                    summary=f"Execution failed: {str(exc)[:50]}",
                    total_time_ms=int((time.time() - start_time) * 1000),
                )

    async def _invoke_non_stream(self, agent: Any, input_data: Dict[str, Any], config: Dict[str, Any]) -> str:
        return await self._execution_streamer.invoke_non_stream(agent, input_data, config)

    def _emit_final_output(
        self,
        accumulated_content: str,
        builder: StreamMessageBuilder,
        snapshot: ExecutionSnapshot,
    ) -> List[StreamMessage]:
        return self._execution_streamer.emit_final_output(accumulated_content, builder, snapshot)

    def _generate_summary(self, snapshot: ExecutionSnapshot) -> str:
        return self._execution_streamer.generate_summary(snapshot)

    def _extract_output(self, result: Dict[str, Any]) -> str:
        return self._execution_streamer.extract_output(result)

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
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            component="agent_runtime.cancel",
        )
        with scoped_logging_context(**operation_context):
            async with self._lock:
                state = self._agents.get(key)
                if state and state.status == AgentStatus.RUNNING:
                    state.cancel_requested = True
                    logger.info("Requested cancellation of agent execution: %s", key)
                    emit_runtime_event("agent.execution.cancel_requested", execution_id=state.current_execution_id)
                    return True
        return False

    async def clear_agent_context(
        self,
        business_unit_id: str,
        agent_name: str,
        thread_id: Optional[str] = None,
    ) -> bool:
        """Clear agent conversation context and local history."""
        key = self._get_agent_key(business_unit_id, agent_name)
        resolved_thread_id = self._resolve_thread_id(agent_name, {"thread_id": thread_id} if thread_id else None)
        state = self._agents.get(key)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            execution_id=resolved_thread_id,
            thread_id=resolved_thread_id,
            component="agent_runtime.clear_context",
        )

        with scoped_logging_context(**operation_context):
            context_cleared = True
            if state and state.agent_instance:
                checkpointer = getattr(state.agent_instance, "checkpointer", None)
                if not checkpointer:
                    logger.warning("Agent checkpointer missing, skipping context cleanup: %s", key)
                    context_cleared = False
                else:
                    delete_thread = getattr(checkpointer, "delete_thread", None)
                    async_delete_thread = getattr(checkpointer, "adelete_thread", None)
                    if callable(delete_thread):
                        result = delete_thread(resolved_thread_id)
                        if asyncio.iscoroutine(result):
                            await result
                    elif callable(async_delete_thread):
                        result = async_delete_thread(resolved_thread_id)
                        if asyncio.iscoroutine(result):
                            await result
                    else:
                        logger.warning("Checkpointer does not support thread deletion: %s", key)
                        context_cleared = False

            self._snapshots.pop(resolved_thread_id, None)

            history_cleared = True
            try:
                history_cleared = self._history_store.clear_history(business_unit_id, agent_name, resolved_thread_id)
            except Exception as delete_error:
                history_cleared = False
                logger.warning("Failed to delete conversation history for %s thread %s: %s", key, resolved_thread_id, delete_error)

            logger.info(
                "Cleared agent context for %s thread %s: context=%s history=%s",
                key,
                resolved_thread_id,
                context_cleared,
                history_cleared,
            )
            emit_runtime_event(
                "agent.context.cleared",
                context_cleared=context_cleared,
                history_cleared=history_cleared,
            )
            return context_cleared and history_cleared

    async def unload_agent(self, business_unit_id: str, agent_name: str) -> bool:
        key = self._get_agent_key(business_unit_id, agent_name)
        operation_context = self._build_observability_context(
            business_unit_id=business_unit_id,
            agent_name=agent_name,
            component="agent_runtime.unload",
        )
        with scoped_logging_context(**operation_context):
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
                        except Exception as exc:
                            logger.warning("Failed to close agent resources for %s: %s", key, exc)
                            emit_runtime_event(
                                "agent.unload.resource_cleanup_failed",
                                level=logging.WARNING,
                                error_type=type(exc).__name__,
                                message=str(exc),
                            )

                state.agent_instance = None
                state.status = AgentStatus.UNLOADED
                del self._agents[key]
                logger.info("Agent unloaded: %s", key)
                emit_runtime_event("agent.unload.completed")
                return True

    def list_loaded_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "business_unit_id": state.business_unit_id,
                "agent_name": state.agent_name,
                "status": state.status.value,
                "loaded_at": state.loaded_at,
                "execution_count": state.execution_count,
            }
            for state in self._agents.values()
        ]


_service_instance: Optional[AgentRuntimeService] = None



def get_agent_runtime_service() -> AgentRuntimeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AgentRuntimeService()
    return _service_instance
