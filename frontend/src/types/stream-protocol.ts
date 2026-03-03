/**
 * 流式消息协议类型定义 (Stream Protocol)
 * 对应后端 agent_engine.core.stream_protocol
 */

// ============ 消息类型枚举 ============

export type MessageType =
  | "THOUGHT"
  | "TASK_LIST"
  | "TOOL_CALL"
  | "ARTIFACT"
  | "STATUS"
  | "ERROR"
  | "DONE"
  | "SNAPSHOT";

// ============ 任务状态 ============

export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

// ============ 制品类型 ============

export type ArtifactType =
  | "code"
  | "chart"
  | "html"
  | "table"
  | "text"
  | "image"
  | "file"
  | "command";

// ============ Payload 类型 ============

/** THOUGHT 消息负载 */
export interface ThoughtPayload {
  content: string;
  mode: "append" | "replace";
  phase?: string;
  step?: number;
  icon?: string;
  reasoning_type?: "thought" | "reflection";
  reason?: string;
  expected_outcome?: string;
}

/** 任务项 */
export interface TaskItem {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  icon?: string;
  error?: string;
}

/** TASK_LIST 消息负载 */
export interface TaskListPayload {
  tasks: TaskItem[];
  current_task_id?: string;
  progress?: number;
}

/** ARTIFACT 消息负载 */
export interface ArtifactPayload {
  artifact_id: string;
  version: number;
  artifact_type: ArtifactType;
  title?: string;
  content?: string;
  // 代码制品
  language?: string;
  filepath?: string;
  operation?: "view" | "create" | "update" | "delete" | "diff";
  // 图表制品
  chart_type?: string;
  chart_config?: Record<string, any>;
  // 表格制品
  headers?: string[];
  rows?: string[][];
  // 命令制品
  command?: string;
  command_explanation?: string;
  is_dangerous?: boolean;
  // 元数据
  metadata?: Record<string, any>;
}

/** STATUS 消息负载 */
export interface StatusPayload {
  text: string;
  icon?: string;
  progress?: number;
}

/** TOOL_CALL 消息负载 */
export interface ToolCallPayload {
  tool_call_id?: string;
  tool_name: string;
  tool_args?: Record<string, any>;
  tool_result?: string;
  status: "running" | "completed" | "failed";
  icon?: string;
  duration_ms?: number;
  reason?: string;
  expected_outcome?: string;
  reflection?: string;
}

/** ERROR 消息负载 */
export interface ErrorPayload {
  message: string;
  error_type?: string;
  task_id?: string;
  traceback?: string;
  suggestion?: string;
  retryable?: boolean;
}

/** DONE 消息负载 */
export interface DonePayload {
  summary?: string;
  total_steps?: number;
  total_time_ms?: number;
  next_steps?: string[];
}

/** SNAPSHOT 消息负载 */
export interface SnapshotPayload {
  thoughts: ThoughtPayload[];
  tasks: TaskItem[];
  artifacts: ArtifactPayload[];
  status?: string;
  execution_id?: string;
}

// ============ 顶层消息包 ============

/** 流式消息包 */
export interface StreamMessage {
  type: MessageType;
  payload: Record<string, any>;
  execution_id: string;
  timestamp: number;
  seq: number;
}

// ============ 类型守卫 ============

export function isThoughtMessage(msg: StreamMessage): msg is StreamMessage & { payload: ThoughtPayload } {
  return msg.type === "THOUGHT";
}

export function isTaskListMessage(msg: StreamMessage): msg is StreamMessage & { payload: TaskListPayload } {
  return msg.type === "TASK_LIST";
}

export function isArtifactMessage(msg: StreamMessage): msg is StreamMessage & { payload: ArtifactPayload } {
  return msg.type === "ARTIFACT";
}

export function isStatusMessage(msg: StreamMessage): msg is StreamMessage & { payload: StatusPayload } {
  return msg.type === "STATUS";
}

export function isToolCallMessage(msg: StreamMessage): msg is StreamMessage & { payload: ToolCallPayload } {
  return msg.type === "TOOL_CALL";
}

export function isErrorMessage(msg: StreamMessage): msg is StreamMessage & { payload: ErrorPayload } {
  return msg.type === "ERROR";
}

export function isDoneMessage(msg: StreamMessage): msg is StreamMessage & { payload: DonePayload } {
  return msg.type === "DONE";
}

export function isSnapshotMessage(msg: StreamMessage): msg is StreamMessage & { payload: SnapshotPayload } {
  return msg.type === "SNAPSHOT";
}

// ============ 图标映射 ============

/** 根据 icon 标识获取 lucide 图标名 */
export function getPhaseIcon(icon?: string): string {
  const iconMap: Record<string, string> = {
    brain: "Brain",
    search: "Search",
    code: "Code",
    plan: "ListChecks",
    check: "CheckCircle2",
    tool: "Wrench",
    file: "File",
    database: "Database",
    loading: "Loader2",
    play: "Play",
    cancel: "XCircle",
    error: "AlertCircle",
  };
  return iconMap[icon || "brain"] || "Brain";
}

/** 根据 phase 获取显示文本 */
export function getPhaseLabel(phase?: string): string {
  const labelMap: Record<string, string> = {
    planning: "规划中",
    analyzing: "分析中",
    reflecting: "反思中",
    searching: "搜索中",
    coding: "编码中",
  };
  return labelMap[phase || ""] || "思考中";
}
