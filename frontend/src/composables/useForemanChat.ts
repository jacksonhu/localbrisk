import { computed, ref, watch } from "vue";
import type {
  ForemanAgentDirectoryItem,
  ForemanConversation,
  ForemanConversationType,
  ForemanMessage,
  ForemanPersistedState,
  ForemanSidebarItem,
} from "@/types/foreman";

const FOREMAN_STORAGE_KEY = "localbrisk.foreman.state.v2";

const directoryAgents = ref<ForemanAgentDirectoryItem[]>(createMockAgents());
const conversations = ref<ForemanConversation[]>([]);
const activeConversationId = ref<string | null>(null);
const conversationKeyword = ref("");
const typingAgentIds = ref<string[]>([]);
const isSending = ref(false);
const isInitialized = ref(false);

let persistenceBound = false;

function createId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

function createTimestamp(minutesOffset = 0): string {
  return new Date(Date.now() + minutesOffset * 60 * 1000).toISOString();
}

function createMockAgents(): ForemanAgentDirectoryItem[] {
  return [
    {
      id: "market-analyst",
      businessUnitId: "market_analysis",
      businessUnitName: "Market Analysis",
      name: "market_analyst",
      displayName: "Market Analyst",
      description: "Focus on market trends, competitor signals, and pricing moves.",
      presence: "online",
      accentColor: "#2563EB",
    },
    {
      id: "ops-planner",
      businessUnitId: "market_analysis",
      businessUnitName: "Market Analysis",
      name: "ops_planner",
      displayName: "Ops Planner",
      description: "Turns strategy into milestones, owners, and follow-up actions.",
      presence: "busy",
      accentColor: "#0F766E",
    },
    {
      id: "risk-auditor",
      businessUnitId: "risk_control",
      businessUnitName: "Risk Control",
      name: "risk_auditor",
      displayName: "Risk Auditor",
      description: "Highlights assumptions, constraints, and delivery risks.",
      presence: "online",
      accentColor: "#B45309",
    },
    {
      id: "data-researcher",
      businessUnitId: "research_lab",
      businessUnitName: "Research Lab",
      name: "data_researcher",
      displayName: "Data Researcher",
      description: "Collects signals and suggests evidence-backed next steps.",
      presence: "offline",
      accentColor: "#7C3AED",
    },
  ];
}

function getAgent(agentId: string): ForemanAgentDirectoryItem | undefined {
  return directoryAgents.value.find((agent) => agent.id === agentId);
}

function buildConversationTitle(type: ForemanConversationType, agentIds: string[]): string {
  const members = agentIds
    .map((agentId) => getAgent(agentId)?.displayName)
    .filter((name): name is string => Boolean(name));

  if (members.length === 0) {
    return "Untitled Conversation";
  }

  if (type === "direct" || members.length === 1) {
    return members[0];
  }

  if (members.length <= 3) {
    return members.join(" · ");
  }

  return `${members.slice(0, 2).join(" · ")} +${members.length - 2}`;
}

function extractSummary(content: string): string {
  const normalized = content.replace(/\s+/g, " ").trim();
  return normalized.length > 72 ? `${normalized.slice(0, 72)}...` : normalized;
}

function syncConversationMeta(conversation: ForemanConversation): void {
  conversation.title = buildConversationTitle(conversation.type, conversation.agentIds);
  conversation.summary = extractSummary(conversation.messages.at(-1)?.content || "");
  conversation.updatedAt = conversation.messages.at(-1)?.createdAt || conversation.updatedAt;
}

function createMessage(
  conversationId: string,
  role: ForemanMessage["role"],
  senderId: string,
  senderName: string,
  content: string,
  createdAt = new Date().toISOString(),
): ForemanMessage {
  return {
    id: createId("message"),
    conversationId,
    role,
    senderId,
    senderName,
    content,
    createdAt,
  };
}

function createWelcomeConversation(type: ForemanConversationType, agentIds: string[]): ForemanConversation {
  const conversationId = createId("conversation");
  const title = buildConversationTitle(type, agentIds);
  const messages: ForemanMessage[] = [];

  if (type === "direct" && agentIds[0]) {
    const agent = getAgent(agentIds[0]);
    if (agent) {
      messages.push(
        createMessage(
          conversationId,
          "agent",
          agent.id,
          agent.displayName,
          `Hi, I am ${agent.displayName}. This page is currently a front-end-only framework preview, and runtime responses can be wired in later.`,
          createTimestamp(-18),
        ),
      );
    }
  }

  if (type === "group") {
    messages.push(
      createMessage(
        conversationId,
        "system",
        "system",
        "System",
        `Group created with ${agentIds.length} agents. Member details are shown in the right sidebar.`,
        createTimestamp(-14),
      ),
    );
  }

  const conversation: ForemanConversation = {
    id: conversationId,
    type,
    title,
    summary: messages[0] ? extractSummary(messages[0].content) : "",
    agentIds,
    messages,
    updatedAt: messages.at(-1)?.createdAt || new Date().toISOString(),
  };

  syncConversationMeta(conversation);
  return conversation;
}

function createInitialConversations(): ForemanConversation[] {
  const directConversation = createWelcomeConversation("direct", ["market-analyst"]);
  directConversation.messages.push(
    createMessage(
      directConversation.id,
      "user",
      "user",
      "You",
      "Please help me organize a cross-agent planning workflow for a new product launch.",
      createTimestamp(-12),
    ),
  );
  directConversation.messages.push(
    createMessage(
      directConversation.id,
      "agent",
      "market-analyst",
      "Market Analyst",
      "Front-end preview note: in the final version I can summarize inputs, propose angles, and pass execution to connected runtime services.",
      createTimestamp(-11),
    ),
  );
  syncConversationMeta(directConversation);

  const groupConversation = createWelcomeConversation("group", ["market-analyst", "ops-planner", "risk-auditor"]);
  groupConversation.messages.push(
    createMessage(
      groupConversation.id,
      "user",
      "user",
      "You",
      "We need a shared plan for launch readiness, risk review, and delivery milestones.",
      createTimestamp(-8),
    ),
  );
  groupConversation.messages.push(
    createMessage(
      groupConversation.id,
      "agent",
      "ops-planner",
      "Ops Planner",
      "I would break this into milestones, owners, dependencies, and a launch checklist in the integrated version.",
      createTimestamp(-7),
    ),
  );
  groupConversation.messages.push(
    createMessage(
      groupConversation.id,
      "agent",
      "risk-auditor",
      "Risk Auditor",
      "I would add rollout guards, risk checkpoints, and fallback paths once backend orchestration is connected.",
      createTimestamp(-6),
    ),
  );
  syncConversationMeta(groupConversation);

  return [groupConversation, directConversation].sort((left, right) =>
    right.updatedAt.localeCompare(left.updatedAt),
  );
}

function appendMessage(conversationId: string, message: ForemanMessage): void {
  const conversation = conversations.value.find((item) => item.id === conversationId);
  if (!conversation) {
    return;
  }

  conversation.messages.push(message);
  syncConversationMeta(conversation);
}

function persistState(): void {
  if (typeof window === "undefined") {
    return;
  }

  const payload: ForemanPersistedState = {
    conversations: conversations.value,
    activeConversationId: activeConversationId.value,
  };

  window.localStorage.setItem(FOREMAN_STORAGE_KEY, JSON.stringify(payload));
}

function restoreState(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  const rawState = window.localStorage.getItem(FOREMAN_STORAGE_KEY);
  if (!rawState) {
    return false;
  }

  try {
    const parsedState = JSON.parse(rawState) as Partial<ForemanPersistedState>;
    if (!Array.isArray(parsedState.conversations)) {
      return false;
    }

    conversations.value = parsedState.conversations;
    activeConversationId.value = parsedState.activeConversationId || parsedState.conversations[0]?.id || null;

    for (const conversation of conversations.value) {
      conversation.agentIds = conversation.agentIds.filter((agentId) => Boolean(getAgent(agentId)));
      conversation.type = conversation.agentIds.length <= 1 ? "direct" : conversation.type;
      if (conversation.agentIds.length === 0) {
        continue;
      }
      syncConversationMeta(conversation);
    }

    conversations.value = conversations.value.filter((conversation) => conversation.agentIds.length > 0);
    if (!conversations.value.some((conversation) => conversation.id === activeConversationId.value)) {
      activeConversationId.value = conversations.value[0]?.id || null;
    }
    return true;
  } catch (error) {
    console.error("[useForemanChat] Failed to restore local state:", error);
    return false;
  }
}

function bindPersistence(): void {
  if (persistenceBound) {
    return;
  }

  watch(
    [conversations, activeConversationId],
    () => {
      persistState();
    },
    { deep: true },
  );

  persistenceBound = true;
}

function ensureInitialized(): void {
  if (isInitialized.value) {
    return;
  }

  const restored = restoreState();
  if (!restored) {
    conversations.value = createInitialConversations();
    activeConversationId.value = conversations.value[0]?.id || null;
    persistState();
  }

  bindPersistence();
  isInitialized.value = true;
}

function findDirectConversation(agentId: string): ForemanConversation | undefined {
  return conversations.value.find(
    (conversation) =>
      conversation.type === "direct" &&
      conversation.agentIds.length === 1 &&
      conversation.agentIds[0] === agentId,
  );
}

function sortConversationsInPlace(): void {
  conversations.value.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

function setActiveConversation(conversationId: string): void {
  activeConversationId.value = conversationId;
}

function startDirectConversation(agentId: string): void {
  ensureInitialized();
  const existingConversation = findDirectConversation(agentId);
  if (existingConversation) {
    activeConversationId.value = existingConversation.id;
    return;
  }

  const newConversation = createWelcomeConversation("direct", [agentId]);
  conversations.value.unshift(newConversation);
  activeConversationId.value = newConversation.id;
}

function selectSidebarItem(item: ForemanSidebarItem): void {
  if (item.type === "group") {
    setActiveConversation(item.id);
    return;
  }

  startDirectConversation(item.id);
}

function addAgentsToConversation(agentIds: string[]): void {
  ensureInitialized();
  const conversation = activeConversation.value;
  if (!conversation) {
    return;
  }

  const uniqueAgentIds = agentIds.filter(
    (agentId, index) => Boolean(getAgent(agentId)) && agentIds.indexOf(agentId) === index,
  );
  const nextAgentIds = uniqueAgentIds.filter((agentId) => !conversation.agentIds.includes(agentId));
  if (nextAgentIds.length === 0) {
    return;
  }

  conversation.agentIds.push(...nextAgentIds);
  conversation.type = conversation.agentIds.length > 1 ? "group" : "direct";

  const addedMemberNames = nextAgentIds
    .map((agentId) => getAgent(agentId)?.displayName)
    .filter((name): name is string => Boolean(name));

  const systemMessage =
    conversation.type === "group" && addedMemberNames.length > 1
      ? `${addedMemberNames.join(", ")} joined the group conversation.`
      : `${addedMemberNames[0] || "New agent"} joined the conversation.`;

  appendMessage(
    conversation.id,
    createMessage(
      conversation.id,
      "system",
      "system",
      "System",
      systemMessage,
    ),
  );

  syncConversationMeta(conversation);
  sortConversationsInPlace();
  activeConversationId.value = conversation.id;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function buildAgentReply(agentId: string, content: string, type: ForemanConversationType): string {
  const agent = getAgent(agentId);
  const snippet = content.length > 60 ? `${content.slice(0, 60)}...` : content;

  if (!agent) {
    return "Front-end preview response is ready.";
  }

  if (type === "direct") {
    return `${agent.displayName} received “${snippet}”. This is a front-end placeholder reply, ready to be replaced by real runtime output later.`;
  }

  return `${agent.displayName} would contribute to “${snippet}” here. In the next phase, this position can stream real multi-agent outputs into the shared timeline.`;
}

async function sendMessage(content: string): Promise<void> {
  ensureInitialized();
  const conversation = activeConversation.value;
  const normalizedContent = content.trim();

  if (!conversation || !normalizedContent || isSending.value) {
    return;
  }

  appendMessage(
    conversation.id,
    createMessage(conversation.id, "user", "user", "You", normalizedContent),
  );
  sortConversationsInPlace();

  isSending.value = true;
  typingAgentIds.value = [...conversation.agentIds];

  try {
    for (const [index, agentId] of conversation.agentIds.entries()) {
      await delay(360 + index * 180);
      const agent = getAgent(agentId);
      appendMessage(
        conversation.id,
        createMessage(
          conversation.id,
          "agent",
          agentId,
          agent?.displayName || "Agent",
          buildAgentReply(agentId, normalizedContent, conversation.type),
        ),
      );
      typingAgentIds.value = typingAgentIds.value.filter((item) => item !== agentId);
      sortConversationsInPlace();
    }
  } finally {
    typingAgentIds.value = [];
    isSending.value = false;
  }
}

const activeConversation = computed<ForemanConversation | null>(() => {
  return conversations.value.find((conversation) => conversation.id === activeConversationId.value) || null;
});

const activeMembers = computed(() => {
  return activeConversation.value?.agentIds
    .map((agentId) => getAgent(agentId))
    .filter((agent): agent is ForemanAgentDirectoryItem => Boolean(agent)) || [];
});

const activeSidebarItemId = computed<string | null>(() => {
  if (!activeConversation.value) {
    return null;
  }

  if (activeConversation.value.type === "group") {
    return activeConversation.value.id;
  }

  return activeConversation.value.agentIds[0] || null;
});

const sidebarItems = computed<ForemanSidebarItem[]>(() => {
  const agentItems: ForemanSidebarItem[] = [...directoryAgents.value]
    .sort((left, right) => left.displayName.localeCompare(right.displayName))
    .map((agent) => {
      const directConversation = findDirectConversation(agent.id);

      return {
        id: agent.id,
        type: "agent",
        title: agent.displayName,
        summary: directConversation?.summary || agent.description,
        updatedAt: directConversation?.updatedAt || "",
        agentIds: [agent.id],
        businessUnitName: agent.businessUnitName,
        accentColor: agent.accentColor,
        presence: agent.presence,
      };
    });

  const groupItems: ForemanSidebarItem[] = [...conversations.value]
    .filter((conversation) => conversation.type === "group")
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    .map((conversation) => ({
      id: conversation.id,
      type: "group",
      title: conversation.title,
      summary: conversation.summary,
      updatedAt: conversation.updatedAt,
      agentIds: [...conversation.agentIds],
    }));

  const keyword = conversationKeyword.value.trim().toLowerCase();
  const items: ForemanSidebarItem[] = [...agentItems, ...groupItems];

  if (!keyword) {
    return items;
  }

  return items.filter((item) => {
    const memberNames = item.agentIds
      .map((agentId) => getAgent(agentId)?.displayName || "")
      .join(" ")
      .toLowerCase();

    return [item.title, item.summary, item.businessUnitName || "", memberNames]
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });
});

function useForemanChat() {
  ensureInitialized();

  return {
    activeConversation,
    activeConversationId,
    activeMembers,
    activeSidebarItemId,
    addAgentsToConversation,
    conversationKeyword,
    directoryAgents,
    conversations,
    isSending,
    selectSidebarItem,
    sendMessage,
    setActiveConversation,
    sidebarItems,
    startDirectConversation,
    typingAgentIds,
  };
}

export { useForemanChat };
export default useForemanChat;
