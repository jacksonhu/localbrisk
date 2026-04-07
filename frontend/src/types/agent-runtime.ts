/**
 * Agent Runtime 类型定义
 * 对应后端 agent_engine 的类型
 */

// ============ 枚举类型 ============

/** Agent 运行状态 */
export type AgentStatus =
  | "idle"
  | "initializing"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "timeout"
  | "cancelled";

/** 执行状态 */
export type ExecutionStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "timeout"
  | "cancelled";

// ============ 请求类型 ============

/** 执行请求 */
export interface ExecuteRequest {
  input: string;
  context?: Record<string, any>;
}

// ============ 响应类型 ============

/** 执行结果 */
export interface ExecutionResult {
  execution_id: string;
  agent_name: string;
  status: ExecutionStatus;
  output?: any;
  error?: string;
  execution_time_ms?: number;
}

/** 状态响应 */
export interface StatusResponse {
  execution_id?: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

/** 服务状态 */
export interface ServiceStatusResponse {
  service_id?: string;
  status: string;
  agent_name?: string;
  catalog_id?: string;
  started_at?: string;
  uptime_seconds?: number;
  request_count?: number;
  error_count?: number;
  health?: string;
}

// ============ 结构化响应类型 (Rich Text Blocks) ============

/** 文本块情感类型 */
export type TextSentiment = "neutral" | "happy" | "alert" | "warning" | "error";

/** 代码操作类型 */
export type CodeOperation = "view" | "create" | "update" | "delete" | "diff";

/** 图表类型 */
export type ChartType = "mermaid" | "json_data" | "table";

/** 思考阶段 */
export type ThinkingPhase = "planning" | "analyzing" | "reflecting";

/** 文件操作类型 */
export type FileOperation = "reference" | "created" | "modified" | "deleted";

/** 内容块类型 */
export type ContentBlockType =
  | "text"
  | "command"
  | "code"
  | "chart"
  | "table"
  | "file"
  | "thinking"
  | "error";

/** 文本块 - 普通文本/Markdown */
export interface TextBlock {
  type: "text";
  content: string;
  sentiment?: TextSentiment;
}

/** 命令块 - Shell 命令 */
export interface CommandBlock {
  type: "command";
  command: string;
  explanation?: string;
  is_dangerous?: boolean;
  cwd?: string;
}

/** 代码块 - 代码片段/文件内容 */
export interface CodeBlock {
  type: "code";
  language: string;
  code: string;
  filepath?: string;
  filename?: string;
  operation?: CodeOperation;
  start_line?: number;
  end_line?: number;
}

/** 图表块 - Mermaid/数据图表 */
export interface ChartBlock {
  type: "chart";
  chart_type?: ChartType;
  content: string;
  title?: string;
}

/** 表格块 - 数据表格 */
export interface TableBlock {
  type: "table";
  headers: string[];
  rows: string[][];
  title?: string;
  caption?: string;
}

/** 文件块 - 文件引用 */
export interface FileBlock {
  type: "file";
  filepath: string;
  filename?: string;
  file_type?: string;
  size?: number;
  operation?: FileOperation;
}

/** 思考块 - 推理过程（可折叠） */
export interface ThinkingBlock {
  type: "thinking";
  content: string;
  phase?: ThinkingPhase;
  collapsed?: boolean;
}

/** 错误块 - 错误信息 */
export interface ErrorBlock {
  type: "error";
  message: string;
  error_type?: string;
  error_code?: string;
  traceback?: string;
  suggestion?: string;
}

/** 内容块联合类型 */
export type ContentBlock =
  | TextBlock
  | CommandBlock
  | CodeBlock
  | ChartBlock
  | TableBlock
  | FileBlock
  | ThinkingBlock
  | ErrorBlock;

/** Agent 结构化响应 */
export interface AgentResponse {
  blocks: ContentBlock[];
  summary: string;
  confidence?: number;
  next_steps?: string[];
}

/** 判断是否为结构化响应 */
export function isAgentResponse(obj: any): obj is AgentResponse {
  return (
    obj &&
    typeof obj === "object" &&
    Array.isArray(obj.blocks) &&
    typeof obj.summary === "string"
  );
}

/** 获取块的显示图标名称 */
export function getBlockIconName(type: ContentBlockType): string {
  const iconMap: Record<ContentBlockType, string> = {
    text: "FileText",
    command: "Terminal",
    code: "Code",
    chart: "BarChart",
    table: "Table",
    file: "File",
    thinking: "Brain",
    error: "AlertCircle",
  };
  return iconMap[type] || "HelpCircle";
}
