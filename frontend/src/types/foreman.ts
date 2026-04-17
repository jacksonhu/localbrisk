export type ForemanConversationType = "direct" | "group";
export type ForemanMessageRole = "user" | "agent" | "system";
export type ForemanAgentPresence = "online" | "busy" | "offline";
export type ForemanSidebarItemType = "agent" | "group";

export interface ForemanAgentDirectoryItem {
  id: string;
  businessUnitId: string;
  businessUnitName: string;
  name: string;
  displayName: string;
  description: string;
  presence: ForemanAgentPresence;
  accentColor: string;
}

export interface ForemanMessage {
  id: string;
  conversationId: string;
  role: ForemanMessageRole;
  senderId: string;
  senderName: string;
  content: string;
  createdAt: string;
}

export interface ForemanConversation {
  id: string;
  type: ForemanConversationType;
  title: string;
  summary: string;
  agentIds: string[];
  messages: ForemanMessage[];
  updatedAt: string;
}

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

export interface ForemanPersistedState {
  conversations: ForemanConversation[];
  activeConversationId: string | null;
}
