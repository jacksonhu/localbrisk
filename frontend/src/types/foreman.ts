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
  content: string;
  mentionedAgents?: string[];
  createdAt: string;
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
