/**
 * Shared type definitions for the unified AgentExecutionBlock component.
 *
 * Both AgentChatPanel (single agent) and ForemanChatWorkspace (multi-agent)
 * feed data into AgentExecutionBlock through the ExecutionBlockData interface.
 */

// ============ Execution step (one entry in the thinking-process flow) ============

/** Step category determines icon and label rendering. */
export type ExecutionStepCategory = "tool_call" | "skill" | "status" | "task";

export type ExecutionStepStatus = "pending" | "running" | "completed" | "failed";

/** One step in the unified execution flow (tool call / task / status). */
export interface ExecutionStep {
  id: string;
  /** Step category for icon and label selection. */
  category: ExecutionStepCategory;
  /** Display label, e.g. "Call", "Skill", "List". */
  label: string;
  /** Primary text, e.g. tool name or task title. */
  title: string;
  /** Secondary description text. */
  description?: string;
  status: ExecutionStepStatus;
  /** Tool call args (expandable detail). */
  toolArgs?: Record<string, any>;
  /** Tool execution result text. */
  toolResult?: string;
  /** Reflection text after step completion. */
  reflection?: string;
}

// ============ Error detail ============

export interface ExecutionErrorDetail {
  type?: string;
  suggestion?: string;
  retryable?: boolean;
}

// ============ ExecutionBlockData — props interface for AgentExecutionBlock ============

export interface ExecutionBlockData {
  /** Whether the agent is currently executing (show spinners). */
  isExecuting: boolean;
  /** Merged execution steps (tool calls + tasks + status messages). */
  steps: ExecutionStep[];
  /** Raw thought/reasoning text (shown when no structured steps exist). */
  thoughtText?: string;
  /** Current thinking phase label (e.g. "analyzing", "planning"). */
  currentPhase?: string;
  /** Whether the thinking cursor should blink (streaming in progress). */
  isThinking?: boolean;
  /** Final output content (markdown string, rendered below the thinking panel). */
  finalContent?: string;
  /** Done summary text. */
  doneSummary?: string;
  /** Suggested next steps after completion. */
  doneNextSteps?: string[];
  /** Error message text. */
  errorText?: string;
  /** Structured error detail. */
  errorDetail?: ExecutionErrorDetail;
}
