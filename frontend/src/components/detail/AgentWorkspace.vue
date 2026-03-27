<template>
  <div class="agent-workspace h-full flex flex-col">
    <!-- 顶部栏 -->
    <div class="workspace-header flex items-center justify-between px-4 py-2.5 border-b border-border bg-background">
      <div class="flex items-center gap-2">
        <Bot class="w-5 h-5 text-primary" />
        <span class="font-medium text-sm">{{ displayName || agentName }}</span>
        <span
          class="text-xs px-2 py-0.5 rounded-full"
          :class="headerStatusClass"
        >
          {{ headerStatusText }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="isExecuting"
          @click="handleCancel"
          class="px-3 py-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
        >
          取消
        </button>
        <button
          @click="handleReset"
          class="p-1.5 rounded-lg hover:bg-muted transition-colors"
          title="清空"
        >
          <Trash2 class="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </div>

    <!-- 单栏主区域：仅对话 -->
    <div class="workspace-body flex-1 overflow-hidden">
      <AgentChatPanel
        ref="chatPanelRef"
        :is-executing="isExecuting"
        @send="handleSend"
        @retry="handleRetry"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { Bot, Trash2 } from "lucide-vue-next";
import AgentChatPanel from "./AgentChatPanel.vue";
import { useSSEClient } from "@/composables/useSSEClient";
import { agentRuntimeApi, type ConversationHistoryTurn } from "@/services/api";
import type {
  StreamMessage, ThoughtPayload, TaskListPayload,
  ArtifactPayload, StatusPayload, ErrorPayload, DonePayload, ToolCallPayload,
} from "@/types/stream-protocol";

const props = withDefaults(defineProps<{
  businessUnitId: string;
  agentName?: string;
  displayName?: string;
}>(), {});

// ============ 状态 ============

const chatPanelRef = ref<InstanceType<typeof AgentChatPanel> | null>(null);
const isExecuting = ref(false);
const isAgentLoaded = ref(false);
const lastUserInput = ref("");
const currentBlockId = ref<string>("");
const currentThreadId = ref<string>("");

// ============ SSE 客户端 ============

const sseClient = useSSEClient({
  onMessage: (msg: StreamMessage) => {
    handleStreamMessage(msg);
  },
  onError: (err: Error) => {
    console.error("[AgentWorkspace] SSE error:", err);
    if (currentBlockId.value && chatPanelRef.value) {
      chatPanelRef.value.setError(currentBlockId.value, {
        message: err.message || "连接错误",
        error_type: "ConnectionError",
        retryable: true,
      });
    }
    isExecuting.value = false;
  },
  onClose: () => {
    isExecuting.value = false;
  },
});

// ============ 流消息处理 ============

function applyStreamMessageToBlock(blockId: string, msg: StreamMessage) {
  const panel = chatPanelRef.value;
  if (!panel || !blockId) return;

  switch (msg.type) {
    case "THOUGHT": {
      const payload = msg.payload as unknown as ThoughtPayload;
      panel.appendThought(blockId, payload);
      break;
    }

    case "TASK_LIST": {
      const payload = msg.payload as unknown as TaskListPayload;
      panel.updateTasks(blockId, payload.tasks);
      break;
    }

    case "TOOL_CALL": {
      const payload = msg.payload as unknown as ToolCallPayload;
      panel.addToolCall(blockId, payload);
      break;
    }

    case "ARTIFACT": {
      const payload = msg.payload as unknown as ArtifactPayload;
      if (payload.filepath || payload.artifact_type === "code") {
        panel.addFileChange(blockId, {
          filepath: payload.filepath || payload.title || payload.artifact_id,
          operation: payload.operation || "create",
        });
      }
      break;
    }

    case "STATUS": {
      const payload = msg.payload as unknown as StatusPayload;
      panel.addLog(blockId, {
        text: payload.text,
        icon: payload.icon,
        isActive: true,
      });
      break;
    }

    case "ERROR": {
      const payload = msg.payload as unknown as ErrorPayload;
      panel.setError(blockId, payload);
      isExecuting.value = false;
      break;
    }

    case "DONE": {
      const payload = msg.payload as unknown as DonePayload;
      panel.setDone(blockId, payload.summary, payload.next_steps);
      isExecuting.value = false;
      break;
    }
  }
}

function handleStreamMessage(msg: StreamMessage) {
  if (!currentBlockId.value) return;
  applyStreamMessageToBlock(currentBlockId.value, msg);
}

// ============ 计算属性 ============

const headerStatusClass = computed(() => {
  if (sseClient.isConnecting.value) return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
  if (isExecuting.value) return "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400";
  return "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400";
});

const headerStatusText = computed(() => {
  if (sseClient.isConnecting.value) return "连接中...";
  if (isExecuting.value) return "执行中";
  return "就绪";
});

// ============ 方法 ============

async function handleSend(userInput: string) {
  if (isExecuting.value || !userInput.trim()) return;

  lastUserInput.value = userInput;
  const panel = chatPanelRef.value;
  if (!panel) return;

  // 添加用户消息
  panel.addUserMessage(userInput);

  // 创建 Agent 执行块
  currentBlockId.value = panel.createAgentBlock();

  isExecuting.value = true;

  // 确保 Agent 已加载
  if (!isAgentLoaded.value) {
    try {
      panel.addLog(currentBlockId.value, { text: "正在加载 Agent...", icon: "play", isActive: true });
      await agentRuntimeApi.load(props.businessUnitId, props.agentName!);
      isAgentLoaded.value = true;
    } catch (err: any) {
      console.error("[AgentWorkspace] Load error:", err);
      panel.setError(currentBlockId.value, {
        message: `加载 Agent 失败: ${err.message}`,
        error_type: "LoadError",
        retryable: true,
      });
      isExecuting.value = false;
      return;
    }
  }

  // 启动流式请求
  await sseClient.executeStreamV2(
    props.businessUnitId,
    props.agentName || "",
    userInput,
    { thread_id: ensureThreadId() }
  );
}

function handleCancel() {
  sseClient.disconnect();
  if (currentBlockId.value && chatPanelRef.value) {
    chatPanelRef.value.setError(currentBlockId.value, {
      message: "用户取消执行",
      error_type: "Cancelled",
    });
  }
  isExecuting.value = false;
}

function resetLocalSessionState(resetPanel = true) {
  sseClient.disconnect();
  if (resetPanel) {
    chatPanelRef.value?.reset();
  }
  isExecuting.value = false;
  lastUserInput.value = "";
  currentBlockId.value = "";
}

function threadStorageKey(): string {
  return `agent-chat-thread:${props.businessUnitId}:${props.agentName || ""}`;
}

function generateThreadId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function ensureThreadId(): string {
  const key = threadStorageKey();
  const cached = localStorage.getItem(key);
  if (cached && cached.trim()) {
    currentThreadId.value = cached.trim();
    return currentThreadId.value;
  }
  const threadId = generateThreadId();
  localStorage.setItem(key, threadId);
  currentThreadId.value = threadId;
  return threadId;
}

function extractTextFromAny(content: any): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const text = (item as Record<string, any>).text ?? (item as Record<string, any>).content;
          return typeof text === "string" ? text : "";
        }
        return "";
      })
      .join("");
  }
  if (content && typeof content === "object") {
    const text = (content as Record<string, any>).text ?? (content as Record<string, any>).content;
    if (typeof text === "string") return text;
  }
  return content == null ? "" : String(content);
}

function isStreamEventMessage(raw: any): raw is StreamMessage {
  const msgType = raw?.type;
  return ["THOUGHT", "TASK_LIST", "TOOL_CALL", "ARTIFACT", "STATUS", "ERROR", "DONE"].includes(msgType);
}

async function replayHistory(turns: ConversationHistoryTurn[]) {
  const panel = chatPanelRef.value;
  if (!panel) return;

  panel.reset();
  for (const turn of turns || []) {
    if (turn?.user_input) {
      panel.addUserMessage(turn.user_input);
    }

    const messages = Array.isArray(turn?.messages) ? turn.messages : [];
    if (messages.length === 0) {
      continue;
    }

    const blockId = panel.createAgentBlock();
    let hasTerminalEvent = false;

    for (const raw of messages) {
      if (isStreamEventMessage(raw)) {
        applyStreamMessageToBlock(blockId, raw as StreamMessage);
        if (raw.type === "DONE" || raw.type === "ERROR") {
          hasTerminalEvent = true;
        }
        continue;
      }

      const rawType = raw?.type;
      if (rawType === "ai") {
        const content = extractTextFromAny(raw?.content);
        if (content) {
          panel.appendThought(blockId, {
            content,
            mode: "append",
            phase: "analyzing",
          } as ThoughtPayload);
        }
      }

      if (rawType === "tool") {
        panel.addToolCall(blockId, {
          tool_name: raw?.name || "unknown",
          tool_call_id: raw?.tool_call_id,
          status: "completed",
          tool_result: extractTextFromAny(raw?.content) || undefined,
          icon: "check",
        });
      }
    }

    if (!hasTerminalEvent) {
      panel.setDone(blockId);
    }
  }
  currentBlockId.value = "";
}

async function loadConversationHistory() {
  if (!props.businessUnitId || !props.agentName) return;
  const threadId = ensureThreadId();
  try {
    const history = await agentRuntimeApi.getConversationHistory(props.businessUnitId, props.agentName, threadId);
    await replayHistory(history.turns || []);
  } catch (err) {
    console.warn("[AgentWorkspace] Load history failed:", err);
  }
}

async function handleReset(needConfirm = true) {
  if (needConfirm) {
    const confirmed = window.confirm("确认清空当前会话历史吗？该操作会删除上下文且不可恢复。");
    if (!confirmed) return;
  }

  if (props.businessUnitId && props.agentName) {
    try {
      const threadId = ensureThreadId();
      await agentRuntimeApi.clearContext(props.businessUnitId, props.agentName, threadId);
    } catch (err) {
      console.warn("[AgentWorkspace] Clear context failed:", err);
    }
  }

  const newThreadId = generateThreadId();
  localStorage.setItem(threadStorageKey(), newThreadId);
  currentThreadId.value = newThreadId;
  resetLocalSessionState(true);
}

function handleRetry() {
  if (lastUserInput.value) {
    void handleSend(lastUserInput.value);
  }
}

// ============ 生命周期 ============

watch(
  () => [props.businessUnitId, props.agentName],
  () => {
    resetLocalSessionState(true);
    isAgentLoaded.value = false;
    if (props.businessUnitId && props.agentName) {
      void loadConversationHistory();
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  sseClient.disconnect();
});
</script>

<style scoped>
.agent-workspace {
  min-height: 400px;
}

</style>
