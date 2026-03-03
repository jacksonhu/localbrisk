"""
流式消息协议定义 (Stream Protocol)

定义 Agent 执行过程中后端推送给前端的消息包格式。
Agent 主输出为 Markdown 文本，前端通过组件映射机制渲染。
每条消息都带有类型标识（MessageType），前端根据 type 字段进行分流处理。

消息类型:
    THOUGHT   - Agent 的思考过程（左侧面板 - 流式打字机效果）
    TASK_LIST - 任务列表状态更新（左侧面板 - 可折叠卡片）
    ARTIFACT  - 输出制品（右侧面板 - 代码/图表/HTML 预览）
    STATUS    - 瞬时状态（如"正在搜索..."），不持久化
    ERROR     - 错误信息（含重试/修正建议）
    DONE      - 执行完成信号
    SNAPSHOT  - 重连时的全量快照
"""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# 消息类型枚举
# ============================================================

class MessageType(str, Enum):
    """流式消息类型"""
    THOUGHT = "THOUGHT"
    TASK_LIST = "TASK_LIST"
    TOOL_CALL = "TOOL_CALL"
    ARTIFACT = "ARTIFACT"
    STATUS = "STATUS"
    ERROR = "ERROR"
    DONE = "DONE"
    SNAPSHOT = "SNAPSHOT"


# ============================================================
# 任务状态
# ============================================================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Payload 定义
# ============================================================

class ThoughtPayload(BaseModel):
    """THOUGHT 消息负载 — Agent 的思考过程"""
    content: str = Field(..., description="思考内容（Markdown），可包含组件映射语法；增量或全量取决于 mode")
    mode: Literal["append", "replace"] = Field(
        "append",
        description="append=增量追加（打字机效果），replace=替换全部"
    )
    phase: Optional[str] = Field(
        None,
        description="思考阶段标识，如 planning/analyzing/reflecting/searching/coding"
    )
    step: Optional[int] = Field(None, description="当前步骤序号")
    icon: Optional[str] = Field(None, description="状态图标标识，如 search/code/check/brain")
    reasoning_type: Optional[Literal["thought", "reflection"]] = Field(
        None,
        description="思考类型: thought=常规思考, reflection=复盘反思"
    )
    reason: Optional[str] = Field(
        None,
        description="动作前的原因说明（为什么做这一步）"
    )
    expected_outcome: Optional[str] = Field(
        None,
        description="动作预期结果"
    )


class TaskItem(BaseModel):
    """单个任务项"""
    id: str = Field(..., description="任务唯一 ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")
    icon: Optional[str] = Field(None, description="任务图标")
    error: Optional[str] = Field(None, description="失败原因（status=failed 时）")


class TaskListPayload(BaseModel):
    """TASK_LIST 消息负载 — 任务列表状态更新"""
    tasks: List[TaskItem] = Field(..., description="完整任务列表（全量替换）")
    current_task_id: Optional[str] = Field(None, description="当前正在执行的任务 ID")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="总进度 0.0~1.0"
    )


class ArtifactType(str, Enum):
    """制品类型"""
    CODE = "code"
    CHART = "chart"
    HTML = "html"
    TABLE = "table"
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    COMMAND = "command"


class ArtifactPayload(BaseModel):
    """ARTIFACT 消息负载 — 右侧输出制品"""
    artifact_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="制品唯一 ID"
    )
    version: int = Field(1, description="版本号，支持历史回看")
    artifact_type: ArtifactType = Field(..., description="制品类型")
    title: Optional[str] = Field(None, description="制品标题")
    
    # 通用内容字段
    content: Optional[str] = Field(None, description="文本/代码/HTML 内容")
    
    # 代码制品专用
    language: Optional[str] = Field(None, description="编程语言（code 类型时）")
    filepath: Optional[str] = Field(None, description="文件路径")
    operation: Optional[Literal["view", "create", "update", "delete", "diff"]] = Field(
        None, description="文件操作类型"
    )
    
    # 图表制品专用
    chart_type: Optional[str] = Field(None, description="图表类型: echarts/mermaid/json_data")
    chart_config: Optional[Dict[str, Any]] = Field(None, description="ECharts option 配置")
    
    # 表格制品专用
    headers: Optional[List[str]] = Field(None, description="表头")
    rows: Optional[List[List[str]]] = Field(None, description="行数据")
    
    # 命令制品专用
    command: Optional[str] = Field(None, description="Shell 命令")
    command_explanation: Optional[str] = Field(None, description="命令说明")
    is_dangerous: bool = Field(False, description="是否危险命令")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class StatusPayload(BaseModel):
    """STATUS 消息负载 — 瞬时状态，不持久化"""
    text: str = Field(..., description="状态文本，如 'Agent 正在搜索...'")
    icon: Optional[str] = Field(None, description="状态图标标识")
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="进度 0.0~1.0（可选）"
    )


class ToolCallPayload(BaseModel):
    """TOOL_CALL 消息负载 — 工具调用详情"""
    tool_call_id: Optional[str] = Field(None, description="工具调用 ID，用于 running/completed 状态匹配")
    tool_name: str = Field(..., description="工具名称")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="工具参数")
    tool_result: Optional[str] = Field(None, description="工具执行结果（完成后填充）")
    status: Literal["running", "completed", "failed"] = Field(
        "running", description="执行状态"
    )
    icon: Optional[str] = Field(None, description="工具图标标识")
    duration_ms: Optional[int] = Field(None, description="执行耗时（毫秒）")
    reason: Optional[str] = Field(None, description="执行该动作的原因（why）")
    expected_outcome: Optional[str] = Field(None, description="该动作的预期结果")
    reflection: Optional[str] = Field(None, description="动作完成后的简短反思")


class ErrorPayload(BaseModel):
    """ERROR 消息负载 — 错误信息"""
    message: str = Field(..., description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
    task_id: Optional[str] = Field(None, description="关联的任务 ID")
    traceback: Optional[str] = Field(None, description="错误堆栈")
    suggestion: Optional[str] = Field(None, description="修复建议")
    retryable: bool = Field(False, description="是否可重试")


class DonePayload(BaseModel):
    """DONE 消息负载 — 执行完成"""
    summary: Optional[str] = Field(None, description="一句话总结")
    total_steps: int = Field(0, description="总步骤数")
    total_time_ms: int = Field(0, description="总耗时（毫秒）")
    next_steps: Optional[List[str]] = Field(None, description="建议的后续步骤")


class SnapshotPayload(BaseModel):
    """SNAPSHOT 消息负载 — 重连时的全量快照"""
    thoughts: List[Dict[str, Any]] = Field(default_factory=list, description="已有的思考记录")
    tasks: List[TaskItem] = Field(default_factory=list, description="当前任务列表")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="已产出的制品列表")
    status: Optional[str] = Field(None, description="当前状态")
    execution_id: Optional[str] = Field(None, description="执行 ID")


# ============================================================
# 顶层消息包
# ============================================================

# Payload 联合类型
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
    """流式消息包 — SSE 传输的基本单元
    
    前端通过 type 字段进行分流处理:
    - THOUGHT  → useThoughtStore
    - TASK_LIST → useTaskStore
    - ARTIFACT → useArtifactStore
    - STATUS   → 瞬时显示，不入 store
    - ERROR    → 错误处理
    - DONE     → 结束信号
    - SNAPSHOT → 重连恢复
    """
    type: MessageType = Field(..., description="消息类型")
    payload: Dict[str, Any] = Field(..., description="消息负载（JSON 对象）")
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="执行 ID（同一次执行共享）"
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix 时间戳"
    )
    seq: int = Field(0, description="消息序号（用于断线重连排序）")
    
    def to_sse(self) -> str:
        """转换为 SSE data 行"""
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
# 工厂函数 — 便捷创建消息
# ============================================================

class StreamMessageBuilder:
    """流式消息构建器"""
    
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
        """创建 THOUGHT 消息"""
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
        """创建 TASK_LIST 消息"""
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
        """创建 ARTIFACT 消息"""
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
        """创建 STATUS 消息"""
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
        """创建 TOOL_CALL 消息"""
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
        task_id: Optional[str] = None,
        suggestion: Optional[str] = None,
        retryable: bool = False,
        traceback: Optional[str] = None,
    ) -> StreamMessage:
        """创建 ERROR 消息"""
        payload = ErrorPayload(
            message=message,
            error_type=error_type,
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
        """创建 DONE 消息"""
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
        """创建 SNAPSHOT 消息"""
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
# 导出
# ============================================================

__all__ = [
    # 枚举
    "MessageType",
    "TaskStatus",
    "ArtifactType",
    # Payload
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
    # 消息包
    "StreamMessage",
    # 构建器
    "StreamMessageBuilder",
]
