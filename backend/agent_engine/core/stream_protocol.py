"""
Stream Protocol Definition

Defines the message packet format pushed from backend to frontend during Agent execution.
Agent main output is Markdown text; the frontend renders it through component mapping.
Each message carries a type identifier (MessageType); the frontend dispatches based on the type field.

Message Types:
    THOUGHT   - Agent's thought process (left panel — streaming typewriter effect)
    TASK_LIST - Task list state updates (left panel — collapsible cards)
    ARTIFACT  - Output artifacts (right panel — code/chart/HTML preview)
    STATUS    - Transient status (e.g., "Searching..."), not persisted
    ERROR     - Error information (with retry/fix suggestions)
    DONE      - Execution completion signal
    SNAPSHOT  - Full snapshot for reconnection
"""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# Message Type Enum
# ============================================================

class MessageType(str, Enum):
    """Streaming message type"""
    THOUGHT = "THOUGHT"
    TASK_LIST = "TASK_LIST"
    TOOL_CALL = "TOOL_CALL"
    ARTIFACT = "ARTIFACT"
    STATUS = "STATUS"
    ERROR = "ERROR"
    DONE = "DONE"
    SNAPSHOT = "SNAPSHOT"


# ============================================================
# Task Status
# ============================================================

class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Payload Definitions
# ============================================================

class ThoughtPayload(BaseModel):
    """THOUGHT message payload — Agent's thought process"""
    content: str = Field(..., description="Thought content (Markdown), may include component mapping syntax; incremental or full depends on mode")
    mode: Literal["append", "replace"] = Field(
        "append",
        description="append=incremental append (typewriter effect), replace=replace all"
    )
    phase: Optional[str] = Field(
        None,
        description="Thought phase identifier, e.g., planning/analyzing/reflecting/searching/coding"
    )
    step: Optional[int] = Field(None, description="Current step number")
    icon: Optional[str] = Field(None, description="Status icon identifier, e.g., search/code/check/brain")
    reasoning_type: Optional[Literal["thought", "reflection"]] = Field(
        None,
        description="Thought type: thought=regular thinking, reflection=retrospective reflection"
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for the action (why this step is taken)"
    )
    expected_outcome: Optional[str] = Field(
        None,
        description="Expected outcome of the action"
    )


class TaskItem(BaseModel):
    """Single task item"""
    id: str = Field(..., description="Task unique ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    icon: Optional[str] = Field(None, description="Task icon")
    error: Optional[str] = Field(None, description="Failure reason (when status=failed)")


class TaskListPayload(BaseModel):
    """TASK_LIST message payload — task list state update"""
    tasks: List[TaskItem] = Field(..., description="Complete task list (full replacement)")
    current_task_id: Optional[str] = Field(None, description="Currently executing task ID")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Overall progress 0.0~1.0"
    )


class ArtifactType(str, Enum):
    """Artifact type"""
    CODE = "code"
    CHART = "chart"
    HTML = "html"
    TABLE = "table"
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    COMMAND = "command"


class ArtifactPayload(BaseModel):
    """ARTIFACT message payload — right panel output artifact"""
    artifact_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Artifact unique ID"
    )
    version: int = Field(1, description="Version number, supports history review")
    artifact_type: ArtifactType = Field(..., description="Artifact type")
    title: Optional[str] = Field(None, description="Artifact title")

    # Generic content field
    content: Optional[str] = Field(None, description="Text/code/HTML content")

    # Code artifact specific
    language: Optional[str] = Field(None, description="Programming language (for code type)")
    filepath: Optional[str] = Field(None, description="File path")
    operation: Optional[Literal["view", "create", "update", "delete", "diff"]] = Field(
        None, description="File operation type"
    )

    # Chart artifact specific
    chart_type: Optional[str] = Field(None, description="Chart type: echarts/mermaid/json_data")
    chart_config: Optional[Dict[str, Any]] = Field(None, description="ECharts option config")

    # Table artifact specific
    headers: Optional[List[str]] = Field(None, description="Table headers")
    rows: Optional[List[List[str]]] = Field(None, description="Row data")

    # Command artifact specific
    command: Optional[str] = Field(None, description="Shell command")
    command_explanation: Optional[str] = Field(None, description="Command explanation")
    is_dangerous: bool = Field(False, description="Whether the command is dangerous")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Extension metadata")


class StatusPayload(BaseModel):
    """STATUS message payload — transient status, not persisted"""
    text: str = Field(..., description="Status text, e.g., 'Agent is searching...'")
    icon: Optional[str] = Field(None, description="Status icon identifier")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Progress 0.0~1.0 (optional)"
    )


class ToolCallPayload(BaseModel):
    """TOOL_CALL message payload — tool call details"""
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for running/completed status matching")
    tool_name: str = Field(..., description="Tool name")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="Tool arguments")
    tool_result: Optional[str] = Field(None, description="Tool execution result (populated on completion)")
    status: Literal["running", "completed", "failed"] = Field(
        "running", description="Execution status"
    )
    icon: Optional[str] = Field(None, description="Tool icon identifier")
    duration_ms: Optional[int] = Field(None, description="Execution duration (milliseconds)")
    reason: Optional[str] = Field(None, description="Reason for executing this action (why)")
    expected_outcome: Optional[str] = Field(None, description="Expected outcome of this action")
    reflection: Optional[str] = Field(None, description="Brief reflection after action completion")


class ErrorPayload(BaseModel):
    """ERROR message payload — error information"""
    message: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Error type")
    error_code: Optional[str] = Field(None, description="Stable application error code")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    traceback: Optional[str] = Field(None, description="Error traceback")
    suggestion: Optional[str] = Field(None, description="Fix suggestion")
    retryable: bool = Field(False, description="Whether retryable")


class DonePayload(BaseModel):
    """DONE message payload — execution completed"""
    summary: Optional[str] = Field(None, description="One-line summary")
    total_steps: int = Field(0, description="Total step count")
    total_time_ms: int = Field(0, description="Total time (milliseconds)")
    next_steps: Optional[List[str]] = Field(None, description="Suggested next steps")


class SnapshotPayload(BaseModel):
    """SNAPSHOT message payload — full snapshot for reconnection"""
    thoughts: List[Dict[str, Any]] = Field(default_factory=list, description="Existing thought records")
    tasks: List[TaskItem] = Field(default_factory=list, description="Current task list")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Produced artifacts list")
    status: Optional[str] = Field(None, description="Current status")
    execution_id: Optional[str] = Field(None, description="Execution ID")


# ============================================================
# Top-Level Message Packet
# ============================================================

# Payload union type
StreamPayload = Union[
    ThoughtPayload,
    TaskListPayload,
    ToolCallPayload,
    ArtifactPayload,
    StatusPayload,
    ErrorPayload,
    DonePayload,
    SnapshotPayload,
]


class StreamMessage(BaseModel):
    """Stream message packet — basic unit for SSE transport

    The frontend dispatches based on the type field:
    - THOUGHT  → useThoughtStore
    - TASK_LIST → useTaskStore
    - ARTIFACT → useArtifactStore
    - STATUS   → transient display, not stored
    - ERROR    → error handling
    - DONE     → end signal
    - SNAPSHOT → reconnection recovery
    """
    type: MessageType = Field(..., description="Message type")
    payload: Dict[str, Any] = Field(..., description="Message payload (JSON object)")
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Execution ID (shared within the same execution)"
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix timestamp"
    )
    seq: int = Field(0, description="Message sequence number (for reconnection ordering)")

    def to_sse(self) -> str:
        """Convert to SSE data line"""
        import json
        data = {
            "type": self.type.value,
            "payload": self.payload,
            "execution_id": self.execution_id,
            "timestamp": self.timestamp,
            "seq": self.seq,
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============================================================
# Factory Functions — convenience message creation
# ============================================================

class StreamMessageBuilder:
    """Stream message builder"""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def thought(
        self,
        content: str,
        mode: str = "append",
        phase: Optional[str] = None,
        step: Optional[int] = None,
        icon: Optional[str] = None,
        reasoning_type: Optional[str] = None,
        reason: Optional[str] = None,
        expected_outcome: Optional[str] = None,
    ) -> StreamMessage:
        """Create a THOUGHT message"""
        payload = ThoughtPayload(
            content=content,
            mode=mode,
            phase=phase,
            step=step,
            icon=icon,
            reasoning_type=reasoning_type,
            reason=reason,
            expected_outcome=expected_outcome,
        )
        return StreamMessage(
            type=MessageType.THOUGHT,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def task_list(
        self,
        tasks: List[TaskItem],
        current_task_id: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> StreamMessage:
        """Create a TASK_LIST message"""
        payload = TaskListPayload(
            tasks=tasks, current_task_id=current_task_id, progress=progress
        )
        return StreamMessage(
            type=MessageType.TASK_LIST,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def artifact(
        self,
        artifact_type: ArtifactType,
        **kwargs,
    ) -> StreamMessage:
        """Create an ARTIFACT message"""
        payload = ArtifactPayload(artifact_type=artifact_type, **kwargs)
        return StreamMessage(
            type=MessageType.ARTIFACT,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def status(
        self,
        text: str,
        icon: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> StreamMessage:
        """Create a STATUS message"""
        payload = StatusPayload(text=text, icon=icon, progress=progress)
        return StreamMessage(
            type=MessageType.STATUS,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def tool_call(
        self,
        tool_name: str,
        tool_call_id: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[str] = None,
        status: str = "running",
        icon: Optional[str] = None,
        duration_ms: Optional[int] = None,
        reason: Optional[str] = None,
        expected_outcome: Optional[str] = None,
        reflection: Optional[str] = None,
    ) -> StreamMessage:
        """Create a TOOL_CALL message"""
        payload = ToolCallPayload(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            status=status,
            icon=icon,
            duration_ms=duration_ms,
            reason=reason,
            expected_outcome=expected_outcome,
            reflection=reflection,
        )
        return StreamMessage(
            type=MessageType.TOOL_CALL,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def error(
        self,
        message: str,
        error_type: Optional[str] = None,
        error_code: Optional[str] = None,
        task_id: Optional[str] = None,
        suggestion: Optional[str] = None,
        retryable: bool = False,
        traceback: Optional[str] = None,
    ) -> StreamMessage:
        """Create an ERROR message"""
        payload = ErrorPayload(
            message=message,
            error_type=error_type,
            error_code=error_code,
            task_id=task_id,
            suggestion=suggestion,
            retryable=retryable,
            traceback=traceback,
        )
        return StreamMessage(
            type=MessageType.ERROR,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def done(
        self,
        summary: Optional[str] = None,
        total_steps: int = 0,
        total_time_ms: int = 0,
        next_steps: Optional[List[str]] = None,
    ) -> StreamMessage:
        """Create a DONE message"""
        payload = DonePayload(
            summary=summary,
            total_steps=total_steps,
            total_time_ms=total_time_ms,
            next_steps=next_steps,
        )
        return StreamMessage(
            type=MessageType.DONE,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )

    def snapshot(
        self,
        thoughts: Optional[List[Dict[str, Any]]] = None,
        tasks: Optional[List[TaskItem]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        status: Optional[str] = None,
    ) -> StreamMessage:
        """Create a SNAPSHOT message"""
        payload = SnapshotPayload(
            thoughts=thoughts or [],
            tasks=tasks or [],
            artifacts=artifacts or [],
            status=status,
            execution_id=self.execution_id,
        )
        return StreamMessage(
            type=MessageType.SNAPSHOT,
            payload=payload.model_dump(exclude_none=True),
            execution_id=self.execution_id,
            seq=self._next_seq(),
        )


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Enums
    "MessageType",
    "TaskStatus",
    "ArtifactType",
    # Payloads
    "ThoughtPayload",
    "TaskItem",
    "TaskListPayload",
    "ToolCallPayload",
    "ArtifactPayload",
    "StatusPayload",
    "ErrorPayload",
    "DonePayload",
    "SnapshotPayload",
    "StreamPayload",
    # Message packet
    "StreamMessage",
    # Builder
    "StreamMessageBuilder",
]
