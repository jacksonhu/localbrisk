// Foreman type definitions — aligned with backend models.

// ============ Agent directory ============

export type ForemanAgentPresence = "online" | "busy" | "offline";

export interface ForemanAgentDirectoryItem {
  /** Format: "business_unit_id/agent_name" */
  id: string;
  businessUnitId: string;
  businessUnitName: string;
  name: string;
  displayName: string;
  description: string;
  /** Derived on frontend side; backend doesn't track presence yet. */
  presence: ForemanAgentPresence;
  accentColor: string;
}

// ============ Conversation member ============

export interface ForemanConversationMember {
  memberId: string;
  businessUnitId: string;
  agentName: string;
  displayName: string;
  joinedAt: string;
}

// ============ Conversation types ============

export type ForemanConversationType = "direct" | "group";

export interface ForemanConversationSummary {
  conversationId: string;
  conversationType: ForemanConversationType;
  title: string;
  lastMessagePreview: string;
  memberCount: number;
  updatedAt: string;
  createdAt: string;
}

export interface ForemanConversationDetail {
  conversationId: string;
  conversationType: ForemanConversationType;
  title: string;
  lastMessagePreview: string;
  coordinatorEnabled: boolean;
  members: ForemanConversationMember[];
  updatedAt: string;
  createdAt: string;
}

// ============ Timeline message ============

export type ForemanMessageRole = "user" | "agent" | "system";

/** Execution step status for task list display. */
export type ForemanTaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

/** One step in the agent execution plan. */
export interface ForemanTaskStep {
  id: string;
  title: string;
  description?: string;
  status: ForemanTaskStatus;
  /** Elapsed time in seconds for display (e.g. "00:02"). */
  elapsedSec?: number;
  /** Thought/reasoning content for this step (expandable). */
  thought?: string;
}

/** Tool call entry tracked during agent execution. */
export interface ForemanToolCallEntry {
  toolCallId?: string;
  toolName: string;
  toolArgs?: Record<string, any>;
  toolResult?: string;
  status: "running" | "completed" | "failed";
  reason?: string;
  expectedOutcome?: string;
  reflection?: string;
}

export interface ForemanMessage {
  /** Primary identifier for the message. */
  id: string;
  /** Same as id; used by backend contracts. */
  messageId: string;
  conversationId: string;
  roundId?: string;
  role: ForemanMessageRole;
  senderId: string;
  senderName: string;
  /** Accent color for the agent avatar. */
  senderColor?: string;
  content: string;
  mentionedAgents?: string[];
  createdAt: string;

  // ---- Execution process fields (agent messages only) ----

  /** Whether the agent is currently executing (show loading indicators). */
  isExecuting?: boolean;
  /** Whether the thinking process panel is expanded. */
  isThinkingExpanded?: boolean;
  /** Current thought/reasoning text being streamed. */
  thoughtText?: string;
  /** Current execution phase label. */
  currentPhase?: string;
  /** Execution step list. */
  tasks?: ForemanTaskStep[];
  /** Tool call entries. */
  toolCalls?: ForemanToolCallEntry[];
  /** Done summary text. */
  doneSummary?: string;
  /** Suggested next steps after completion. */
  doneNextSteps?: string[];
  /** Error info. */
  errorText?: string;
}

// ============ Sidebar item (unified for left panel) ============

export type ForemanSidebarItemType = "agent" | "group";

export interface ForemanSidebarItem {
  id: string;
  type: ForemanSidebarItemType;
  title: string;
  summary: string;
  updatedAt: string;
  agentIds: string[];
  businessUnitName?: string;
  accentColor?: string;
  presence?: ForemanAgentPresence;
}

// ============ SSE event types ============

export type ForemanSSEEventKind =
  | "round_started"
  | "member_started"
  | "member_done"
  | "round_completed"
  | "coordinator_decision";

// ============ Local state (for useForemanChat) ============

/**
 * Runtime conversation state held in memory by useForemanChat.
 * Combines backend detail with locally-accumulated messages.
 */
export interface ForemanConversation {
  id: string;
  type: ForemanConversationType;
  title: string;
  summary: string;
  agentIds: string[];
  messages: ForemanMessage[];
  updatedAt: string;
}

export interface ForemanPersistedState {
  conversations: ForemanConversation[];
  activeConversationId: string | null;
}
