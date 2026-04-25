/**
 * useForemanChat — Real backend-driven Foreman chat composable.
 *
 * Replaces the previous mock/localStorage implementation with:
 * - foremanApi for directory, conversation CRUD, and member management
 * - useSSEClient.executeStreamGeneric for streaming agent responses
 * - Reactive state for sidebar items, active conversation, and messages
 */

import { computed, ref, watch } from "vue";
import type {
  ForemanAgentDirectoryItem,
  ForemanConversation,
  ForemanConversationDetail,
  ForemanConversationType,
  ForemanMessage,
  ForemanSidebarItem,
} from "@/types/foreman";
import { foremanApi } from "@/services/api";
import { useSSEClient } from "@/composables/useSSEClient";
import type { StreamMessage } from "@/types/stream-protocol";

// ──────────────────── shared reactive state ────────────────────

const directoryAgents = ref<ForemanAgentDirectoryItem[]>([]);
const conversations = ref<ForemanConversation[]>([]);
const activeConversationId = ref<string | null>(null);
const conversationKeyword = ref("");
const typingAgentIds = ref<string[]>([]);
const isSending = ref(false);
const isInitialized = ref(false);
const isLoading = ref(false);

// ──────────────────── accent color pool ────────────────────

const ACCENT_COLORS = ["#2563EB", "#0F766E", "#B45309", "#7C3AED", "#DC2626", "#0284C7", "#4F46E5"];

function accentForIndex(index: number): string {
  return ACCENT_COLORS[index % ACCENT_COLORS.length];
}

// ──────────────────── helper: map backend detail → local state ────────────────────

function detailToConversation(detail: any): ForemanConversation {
  // Backend returns snake_case JSON; handle both cases for safety.
  return {
    id: detail.conversationId || detail.conversation_id || "",
    type: (detail.conversationType || detail.conversation_type || "direct") as ForemanConversationType,
    title: detail.title || "",
    summary: detail.lastMessagePreview || detail.last_message_preview || "",
    agentIds: (detail.members || []).map((m: any) =>
      `${m.businessUnitId || m.business_unit_id}/${m.agentName || m.agent_name}`,
    ),
    messages: [],
    updatedAt: detail.updatedAt || detail.updated_at || "",
  };
}

// ──────────────────── initialization ────────────────────

async function initialize(): Promise<void> {
  if (isInitialized.value || isLoading.value) return;
  isLoading.value = true;

  try {
    // Load agent directory.
    const rawAgents = await foremanApi.listAgents();
    directoryAgents.value = (rawAgents || []).map((raw: any, idx: number) => ({
      id: raw.id || `${raw.business_unit_id}/${raw.name}`,
      businessUnitId: raw.business_unit_id || raw.businessUnitId || "",
      businessUnitName: raw.business_unit_name || raw.businessUnitName || "",
      name: raw.name || "",
      displayName: raw.display_name || raw.displayName || raw.name || "",
      description: raw.description || "",
      presence: "online" as const,
      accentColor: accentForIndex(idx),
    }));

    // Load conversation list.
    const listResp = await foremanApi.listConversations();
    const summaries = listResp?.conversations || [];
    conversations.value = summaries.map((s: any) => ({
      id: s.conversationId || s.conversation_id,
      type: (s.conversationType || s.conversation_type || "direct") as ForemanConversationType,
      title: s.title || "",
      summary: s.lastMessagePreview || s.last_message_preview || "",
      agentIds: [],
      messages: [],
      updatedAt: s.updatedAt || s.updated_at || "",
    }));

    // Select first conversation if any.
    if (!activeConversationId.value && conversations.value.length > 0) {
      activeConversationId.value = conversations.value[0].id;
    }

    isInitialized.value = true;
  } catch (err) {
    console.error("[useForemanChat] Failed to initialize:", err);
  } finally {
    isLoading.value = false;
  }
}

// ──────────────────── load messages for active conversation ────────────────────

async function loadMessages(conversationId: string): Promise<void> {
  const conversation = conversations.value.find((c) => c.id === conversationId);
  if (!conversation) return;
  if (conversation.messages.length > 0) return; // Already loaded.

  try {
    const resp = await foremanApi.getMessages(conversationId, 200);
    const msgs = resp?.messages || [];
    conversation.messages = msgs.map((m: any) => {
      const mid = m.messageId || m.message_id || m.id || "";
      return {
        id: mid,
        messageId: mid,
        conversationId: m.conversationId || m.conversation_id || conversationId,
        role: m.role || "user",
        senderId: m.senderId || m.sender_id || "",
        senderName: m.senderName || m.sender_name || "",
        content: m.content || "",
        createdAt: m.createdAt || m.created_at || "",
      };
    });
  } catch (err) {
    console.error("[useForemanChat] Failed to load messages:", err);
  }
}

// ──────────────────── getAgent helper ────────────────────

function getAgent(agentId: string): ForemanAgentDirectoryItem | undefined {
  return directoryAgents.value.find((a) => a.id === agentId);
}

// ──────────────────── sidebar item helpers ────────────────────

function findDirectConversation(agentId: string): ForemanConversation | undefined {
  return conversations.value.find(
    (c) => c.type === "direct" && c.agentIds.length === 1 && c.agentIds[0] === agentId,
  );
}

// ──────────────────── select sidebar item ────────────────────

async function selectSidebarItem(item: ForemanSidebarItem): Promise<void> {
  if (item.type === "group") {
    activeConversationId.value = item.id;
    await loadMessages(item.id);
    return;
  }

  // Agent item: find existing direct conversation or create one.
  const existing = findDirectConversation(item.id);
  if (existing) {
    activeConversationId.value = existing.id;
    await loadMessages(existing.id);
    return;
  }

  await startDirectConversation(item.id);
}

// ──────────────────── start direct conversation ────────────────────

async function startDirectConversation(agentId: string): Promise<void> {
  try {
    const detail = await foremanApi.createConversation([agentId]);
    const conversation = detailToConversation(detail);
    conversations.value.unshift(conversation);
    activeConversationId.value = conversation.id;
    await loadMessages(conversation.id);
  } catch (err) {
    console.error("[useForemanChat] Failed to create direct conversation:", err);
  }
}

// ──────────────────── add agents to conversation ────────────────────

async function addAgentsToConversation(agentIds: string[]): Promise<void> {
  const conversation = activeConversation.value;
  if (!conversation) return;

  try {
    const detail: any = await foremanApi.addMembers(conversation.id, agentIds);
    // Update local state from backend response (snake_case JSON).
    conversation.agentIds = (detail.members || []).map((m: any) =>
      `${m.businessUnitId || m.business_unit_id}/${m.agentName || m.agent_name}`,
    );
    conversation.type = (detail.conversationType || detail.conversation_type || conversation.type) as ForemanConversationType;
    conversation.title = detail.title || conversation.title;

    // Reload messages to pick up system join messages.
    conversation.messages = [];
    await loadMessages(conversation.id);
  } catch (err) {
    console.error("[useForemanChat] Failed to add members:", err);
  }
}

// ──────────────────── send message ────────────────────

async function sendMessage(content: string): Promise<void> {
  const conversation = activeConversation.value;
  if (!conversation || !content.trim() || isSending.value) return;

  const normalizedContent = content.trim();
  isSending.value = true;

  // Optimistic user message.
  const userMsgId = `tmp-${Date.now()}`;
  const userMessage: ForemanMessage = {
    id: userMsgId,
    messageId: userMsgId,
    conversationId: conversation.id,
    role: "user",
    senderId: "user",
    senderName: "You",
    content: normalizedContent,
    createdAt: new Date().toISOString(),
  };
  conversation.messages.push(userMessage);
  conversation.summary = normalizedContent.slice(0, 72);

  // Track which agents are "typing".
  typingAgentIds.value = [...conversation.agentIds];

  // SSE streaming.
  const streamUrl = foremanApi.getStreamUrl(conversation.id);

  const { executeStreamGeneric, disconnect } = useSSEClient({
    onMessage: (msg: StreamMessage) => {
      const payload = msg.payload || {};
      const agentName = payload.agent_name || "";
      const eventKind = payload.event_kind || "";

      // Handle Foreman envelope events.
      if (msg.type === "STATUS" && eventKind) {
        if (eventKind === "member_done") {
          typingAgentIds.value = typingAgentIds.value.filter((id) => !id.endsWith(`/${agentName}`));
        }
        if (eventKind === "round_completed") {
          typingAgentIds.value = [];
        }
        // Show coordinator decisions as system messages.
        if (eventKind === "coordinator_decision") {
          const sysId = `sys-${Date.now()}`;
          conversation.messages.push({
            id: sysId,
            messageId: sysId,
            conversationId: conversation.id,
            role: "system",
            senderId: "system",
            senderName: "System",
            content: payload.text || eventKind,
            createdAt: new Date().toISOString(),
          });
        }
        return;
      }

      // Handle THOUGHT messages from member agents.
      if (msg.type === "THOUGHT" && agentName) {
        const agentInfo = directoryAgents.value.find((a) => a.name === agentName);
        const displayName = agentInfo?.displayName || agentName;
        const mode = payload.mode || "append";
        const content = payload.content || "";

        // Find or create a message bubble for this agent in this round.
        const existingIdx = conversation.messages.findLastIndex(
          (m) => m.role === "agent" && m.senderId === agentName && m.roundId === payload.round_id,
        );

        if (existingIdx >= 0 && mode === "append") {
          conversation.messages[existingIdx].content += content;
        } else if (existingIdx >= 0 && mode === "replace") {
          conversation.messages[existingIdx].content = content;
        } else {
          const agentMsgId = `agent-${Date.now()}-${agentName}`;
          conversation.messages.push({
            id: agentMsgId,
            messageId: agentMsgId,
            conversationId: conversation.id,
            roundId: payload.round_id,
            role: "agent",
            senderId: agentName,
            senderName: displayName,
            content: content,
            createdAt: new Date().toISOString(),
          });
        }

        conversation.summary = content.slice(0, 72);
        return;
      }

      // Handle ERROR messages.
      if (msg.type === "ERROR") {
        const errId = `err-${Date.now()}`;
        conversation.messages.push({
          id: errId,
          messageId: errId,
          conversationId: conversation.id,
          role: "system",
          senderId: "system",
          senderName: "System",
          content: `Error: ${payload.message || "Unknown error"}`,
          createdAt: new Date().toISOString(),
        });
      }
    },
    onError: (err) => {
      console.error("[useForemanChat] SSE error:", err);
    },
    onClose: () => {
      typingAgentIds.value = [];
      isSending.value = false;
    },
  });

  try {
    await executeStreamGeneric(streamUrl, {
      content: normalizedContent,
      mentions: null,
    });
  } catch (err) {
    console.error("[useForemanChat] Send message failed:", err);
  } finally {
    typingAgentIds.value = [];
    isSending.value = false;
  }
}

// ──────────────────── computed properties ────────────────────

const activeConversation = computed<ForemanConversation | null>(() => {
  return conversations.value.find((c) => c.id === activeConversationId.value) || null;
});

const activeMembers = computed<ForemanAgentDirectoryItem[]>(() => {
  const conv = activeConversation.value;
  if (!conv) return [];
  return conv.agentIds
    .map((id) => getAgent(id))
    .filter((a): a is ForemanAgentDirectoryItem => Boolean(a));
});

const activeSidebarItemId = computed<string | null>(() => {
  const conv = activeConversation.value;
  if (!conv) return null;
  if (conv.type === "group") return conv.id;
  return conv.agentIds[0] || null;
});

const sidebarItems = computed<ForemanSidebarItem[]>(() => {
  const agentItems: ForemanSidebarItem[] = [...directoryAgents.value]
    .sort((a, b) => a.displayName.localeCompare(b.displayName))
    .map((agent) => {
      const directConv = findDirectConversation(agent.id);
      return {
        id: agent.id,
        type: "agent" as const,
        title: agent.displayName,
        summary: directConv?.summary || agent.description,
        updatedAt: directConv?.updatedAt || "",
        agentIds: [agent.id],
        businessUnitName: agent.businessUnitName,
        accentColor: agent.accentColor,
        presence: agent.presence,
      };
    });

  const groupItems: ForemanSidebarItem[] = [...conversations.value]
    .filter((c) => c.type === "group")
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .map((c) => ({
      id: c.id,
      type: "group" as const,
      title: c.title,
      summary: c.summary,
      updatedAt: c.updatedAt,
      agentIds: [...c.agentIds],
    }));

  const keyword = conversationKeyword.value.trim().toLowerCase();
  const items: ForemanSidebarItem[] = [...agentItems, ...groupItems];

  if (!keyword) return items;

  return items.filter((item) => {
    const searchText = [item.title, item.summary, item.businessUnitName || ""].join(" ").toLowerCase();
    return searchText.includes(keyword);
  });
});

// ──────────────────── auto-load messages on conversation switch ────────────────────

watch(activeConversationId, (newId) => {
  if (newId) loadMessages(newId);
});

// ──────────────────── composable export ────────────────────

function useForemanChat() {
  initialize();

  return {
    activeConversation,
    activeConversationId,
    activeMembers,
    activeSidebarItemId,
    addAgentsToConversation,
    conversationKeyword,
    directoryAgents,
    conversations,
    isLoading,
    isSending,
    selectSidebarItem,
    sendMessage,
    sidebarItems,
    typingAgentIds,
  };
}

export { useForemanChat };
export default useForemanChat;
