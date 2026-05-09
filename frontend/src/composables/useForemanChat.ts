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
  ForemanTaskStatus,
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

/**
 * Find or create the current agent message block for the given round.
 * All SSE events from a single agent in a single round go into one message.
 */
function findOrCreateAgentBlock(
  conversation: ForemanConversation,
  agentName: string,
  roundId: string | undefined,
): ForemanMessage {
  const existing = conversation.messages.findLast(
    (m) => m.role === "agent" && m.senderId === agentName && m.roundId === (roundId || ""),
  );
  if (existing) return existing;

  const agentInfo = directoryAgents.value.find((a) => a.name === agentName);
  const displayName = agentInfo?.displayName || agentName;
  const color = agentInfo?.accentColor || "#2563EB";
  const blockId = `agent-${Date.now()}-${agentName}`;

  const block: ForemanMessage = {
    id: blockId,
    messageId: blockId,
    conversationId: conversation.id,
    roundId: roundId || "",
    role: "agent",
    senderId: agentName,
    senderName: displayName,
    senderColor: color,
    content: "",
    createdAt: new Date().toISOString(),
    isExecuting: true,
    isThinkingExpanded: true,
    tasks: [],
    toolCalls: [],
  };

  conversation.messages.push(block);
  return block;
}

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

  // Execution timer per agent block for elapsed seconds.
  const blockStartTimes = new Map<string, number>();

  // SSE streaming.
  const streamUrl = foremanApi.getStreamUrl(conversation.id);

  const { executeStreamGeneric, disconnect } = useSSEClient({
    onMessage: (msg: StreamMessage) => {
      const payload = msg.payload || {};
      const agentName: string = payload.agent_name || "";
      const eventKind: string = payload.event_kind || "";
      const roundId: string = payload.round_id || "";

      // ---- Foreman envelope events (STATUS with event_kind) ----
      if (msg.type === "STATUS" && eventKind) {
        if (eventKind === "member_started" && agentName) {
          // Create agent block eagerly when member starts.
          const block = findOrCreateAgentBlock(conversation, agentName, roundId);
          blockStartTimes.set(block.id, Date.now());
        }

        if (eventKind === "member_done" && agentName) {
          typingAgentIds.value = typingAgentIds.value.filter((id) => !id.endsWith(`/${agentName}`));
          // Mark the agent block as done executing.
          const block = conversation.messages.findLast(
            (m) => m.role === "agent" && m.senderId === agentName,
          );
          if (block) {
            block.isExecuting = false;
            // Mark all remaining pending tasks as completed.
            if (block.tasks) {
              for (const t of block.tasks) {
                if (t.status === "running" || t.status === "pending") t.status = "completed";
              }
            }
          }
        }

        if (eventKind === "round_completed") {
          typingAgentIds.value = [];
        }

        // Coordinator decisions show as system messages.
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

      // ---- THOUGHT: append to agent block ----
      if (msg.type === "THOUGHT" && agentName) {
        const block = findOrCreateAgentBlock(conversation, agentName, roundId);
        const mode = payload.mode || "append";
        const incoming = payload.content || "";

        if (mode === "replace") {
          block.content = incoming;
        } else {
          block.content += incoming;
        }

        // Also update thought text for the execution panel.
        if (payload.phase) block.currentPhase = payload.phase;
        if (mode === "replace") {
          block.thoughtText = incoming;
        } else {
          block.thoughtText = (block.thoughtText || "") + incoming;
        }

        // If there's a running task, attach the thought to it.
        const runningTask = block.tasks?.find((t) => t.status === "running");
        if (runningTask) {
          runningTask.thought = (block.thoughtText || "").slice(-500);
        }

        conversation.summary = incoming.slice(0, 72);
        return;
      }

      // ---- TASK_LIST: update step list on agent block ----
      if (msg.type === "TASK_LIST" && agentName) {
        const block = findOrCreateAgentBlock(conversation, agentName, roundId);
        const incomingTasks = payload.tasks || [];
        const startTime = blockStartTimes.get(block.id) || Date.now();

        block.tasks = incomingTasks.map((t: any) => {
          const status = normalizeTaskStatus(t.status);
          return {
            id: String(t.id || t.task_id || ""),
            title: t.title || t.content || "",
            description: t.description || "",
            status,
            elapsedSec: status !== "pending" ? Math.round((Date.now() - startTime) / 1000) : undefined,
            thought: undefined,
          };
        });
        return;
      }

      // ---- TOOL_CALL: track tool execution ----
      if (msg.type === "TOOL_CALL" && agentName) {
        const block = findOrCreateAgentBlock(conversation, agentName, roundId);
        if (!block.toolCalls) block.toolCalls = [];

        if (payload.status === "running") {
          block.toolCalls.push({
            toolCallId: payload.tool_call_id,
            toolName: payload.tool_name || "unknown",
            toolArgs: payload.tool_args,
            status: "running",
            reason: payload.reason,
            expectedOutcome: payload.expected_outcome,
          });
        } else {
          // Match and update existing entry.
          const idx = payload.tool_call_id
            ? block.toolCalls.findLastIndex((tc) => tc.toolCallId === payload.tool_call_id)
            : block.toolCalls.findLastIndex((tc) => tc.toolName === payload.tool_name && tc.status === "running");

          if (idx >= 0) {
            block.toolCalls[idx].status = payload.status;
            block.toolCalls[idx].toolResult = payload.tool_result;
            if (payload.reflection) block.toolCalls[idx].reflection = payload.reflection;
          } else {
            block.toolCalls.push({
              toolCallId: payload.tool_call_id,
              toolName: payload.tool_name || "unknown",
              toolArgs: payload.tool_args,
              toolResult: payload.tool_result,
              status: payload.status || "completed",
              reason: payload.reason,
            });
          }
        }
        return;
      }

      // ---- DONE: mark agent execution complete ----
      if (msg.type === "DONE") {
        if (agentName) {
          const block = conversation.messages.findLast(
            (m) => m.role === "agent" && m.senderId === agentName,
          );
          if (block) {
            block.isExecuting = false;
            block.doneSummary = payload.summary || "";
            block.doneNextSteps = payload.next_steps;
            if (block.tasks) {
              for (const t of block.tasks) {
                if (t.status !== "failed") t.status = "completed";
              }
            }
          }
        }
        return;
      }

      // ---- ERROR ----
      if (msg.type === "ERROR") {
        if (agentName) {
          const block = conversation.messages.findLast(
            (m) => m.role === "agent" && m.senderId === agentName,
          );
          if (block) {
            block.isExecuting = false;
            block.errorText = payload.message || "Unknown error";
          }
        } else {
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
        return;
      }
    },
    onError: (err) => {
      console.error("[useForemanChat] SSE error:", err);
    },
    onClose: () => {
      typingAgentIds.value = [];
      isSending.value = false;
      // Mark all executing blocks as done.
      for (const m of conversation.messages) {
        if (m.isExecuting) m.isExecuting = false;
      }
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

/** Normalize task status string variants to canonical values. */
function normalizeTaskStatus(status?: string): ForemanTaskStatus {
  const s = (status || "pending").toLowerCase();
  if (s === "completed" || s === "done" || s === "success") return "completed";
  if (s === "running" || s === "in_progress" || s === "in-progress") return "running";
  if (s === "failed" || s === "error") return "failed";
  if (s === "cancelled" || s === "canceled") return "cancelled";
  return "pending";
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
