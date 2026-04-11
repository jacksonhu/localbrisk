"""Runtime state models for agent execution."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.stream_protocol import TaskItem


class AgentStatus(str, Enum):
    """Agent runtime status."""

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
    """Agent runtime state."""

    business_unit_id: str
    agent_name: str
    agent_path: str
    status: AgentStatus = AgentStatus.IDLE
    agent_instance: Any = None
    current_execution_id: Optional[str] = None
    config_fingerprint: Optional[str] = None
    loaded_at: Optional[str] = None
    last_execution_at: Optional[str] = None
    execution_count: int = 0
    error_count: int = 0
    cancel_requested: bool = False


@dataclass
class ExecutionSnapshot:
    """Execution snapshot used for reconnection recovery."""

    execution_id: str
    thoughts: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[TaskItem] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    last_seq: int = 0
