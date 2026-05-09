<template>
  <div class="agent-chat-panel h-full flex flex-col">
    <!-- Chat content area -->
    <div ref="chatContainerRef" class="chat-content flex-1 overflow-y-auto">
      <div v-if="chatItems.length === 0 && !isExecuting" class="h-full flex flex-col items-center justify-center text-center p-8">
        <Bot class="w-16 h-16 text-muted-foreground/20 mb-4" />
        <h3 class="text-lg font-medium mb-2">Start a conversation</h3>
        <p class="text-muted-foreground text-sm max-w-md">Enter your question and the Agent will analyze and generate results</p>
      </div>

      <div class="chat-stream p-4 space-y-4">
        <template v-for="item in chatItems" :key="item.id">
          <!-- User message -->
          <div v-if="item.type === 'user'" class="flex justify-end">
            <div class="user-bubble max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
              {{ item.content }}
            </div>
          </div>

          <!-- Agent execution block — delegated to shared component -->
          <div v-else-if="item.type === 'agent-block'" class="agent-block">
            <AgentExecutionBlock
              :data="toExecutionBlockData(item)"
              @retry="$emit('retry')"
            />

            <!-- File changes (agent-chat specific, not in shared block) -->
            <div v-if="item.fileChanges && item.fileChanges.length > 0" class="file-changes-section mt-2 mb-3">
              <div class="text-xs font-medium text-muted-foreground px-3 mb-1.5">File changes</div>
              <div class="space-y-1">
                <div v-for="(file, fIdx) in item.fileChanges" :key="fIdx"
                  class="file-entry flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <component :is="fileIcon(file.operation)" class="w-3.5 h-3.5" :class="fileIconClass(file.operation)" />
                  <span class="text-sm font-mono truncate">{{ file.filepath }}</span>
                  <span class="text-xs px-1.5 py-0.5 rounded ml-auto" :class="fileBadgeClass(file.operation)">{{ fileLabel(file.operation) }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Input area -->
    <div class="chat-input border-t border-border p-3">
      <div class="flex items-end gap-3">
        <div class="flex-1 relative">
          <textarea
            ref="inputRef" v-model="inputText" @keydown="handleKeydown"
            placeholder="Type your message, press Enter to send..." :disabled="isExecuting"
            class="w-full px-4 py-3 pr-12 bg-muted rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 text-sm"
            :rows="inputRows"
          ></textarea>
          <button @click="handleSend" :disabled="!canSend"
            class="absolute right-3 bottom-3 p-1.5 rounded-lg transition-colors"
            :class="canSend ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'bg-muted-foreground/20 text-muted-foreground cursor-not-allowed'"
          ><Send class="w-4 h-4" /></button>
        </div>
      </div>
      <p class="text-xs text-muted-foreground mt-1.5">Enter to send · Shift+Enter for new line</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from "vue";
import { Bot, Send, Loader2, File, FilePlus, FileEdit, Trash2 } from "lucide-vue-next";
import AgentExecutionBlock from "@/components/common/AgentExecutionBlock.vue";
import type { ExecutionBlockData, ExecutionStep } from "@/types/execution-block";
import type { TaskItem, ThoughtPayload, ErrorPayload, ToolCallPayload } from "@/types/stream-protocol";

// ============ Internal types ============

interface ToolCallEntry {
  tool_call_id?: string;
  tool_name: string;
  tool_args?: Record<string, any>;
  tool_result?: string;
  status: "running" | "completed" | "failed";
  icon?: string;
  reason?: string;
  expected_outcome?: string;
  reflection?: string;
}

interface FileChangeEntry {
  filepath: string;
  operation: string;
  artifactId?: string;
}

type TaskUiStatus = "pending" | "running" | "completed" | "failed" | "cancelled";
type UiTaskItem = Omit<TaskItem, "status"> & { status: TaskUiStatus; content?: string };

interface ChatItem {
  id: string;
  type: "user" | "agent-block";
  content?: string;
  thoughtText?: string;
  currentPhase?: string;
  thoughtReason?: string;
  thoughtExpectedOutcome?: string;
  isThinking?: boolean;
  tasks?: UiTaskItem[];
  toolCalls?: ToolCallEntry[];
  fileChanges?: FileChangeEntry[];
  doneSummary?: string;
  doneNextSteps?: string[];
  error?: ErrorPayload | null;
  isActive?: boolean;
  statusText?: string;
  statusIcon?: string;
}

// ============ Props / Emits ============

const props = defineProps<{ isExecuting: boolean }>();
const emit = defineEmits<{
  (e: "send", input: string): void;
  (e: "retry"): void;
  (e: "open-artifact", artifactId: string): void;
}>();

// ============ State ============

const chatContainerRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const inputText = ref("");
const chatItems = ref<ChatItem[]>([]);

const canSend = computed(() => inputText.value.trim().length > 0 && !props.isExecuting);
const inputRows = computed(() => Math.min(Math.max(inputText.value.split("\n").length, 1), 5));

// ============ ChatItem → ExecutionBlockData adapter ============

/** Convert internal ChatItem to the shared ExecutionBlockData interface. */
function toExecutionBlockData(item: ChatItem): ExecutionBlockData {
  const steps: ExecutionStep[] = [];

  // Merge tasks into step flow.
  if (item.tasks) {
    for (const task of item.tasks) {
      steps.push({
        id: `task-${task.id}`,
        category: "task",
        label: task.title,
        title: task.title,
        description: task.description || task.error,
        status: task.status === "cancelled" ? "failed" : task.status,
      });
    }
  }

  // Merge tool calls into step flow.
  if (item.toolCalls) {
    for (const tc of item.toolCalls) {
      steps.push({
        id: `tc-${tc.tool_call_id || tc.tool_name}-${steps.length}`,
        category: "tool_call",
        label: "Call",
        title: tc.tool_name,
        description: tc.reason || briefArgs(tc.tool_args),
        status: tc.status,
        toolArgs: tc.tool_args,
        toolResult: tc.tool_result,
        reflection: tc.reflection,
      });
    }
  }

  // Add status text as a step if present and active.
  if (item.statusText && item.isActive && !item.doneSummary && !item.error) {
    steps.push({
      id: `status-${item.id}`,
      category: "status",
      label: "Status",
      title: item.statusText,
      status: "running",
    });
  }

  return {
    isExecuting: Boolean(item.isActive),
    steps,
    thoughtText: item.thoughtText || undefined,
    currentPhase: item.currentPhase,
    isThinking: item.isThinking,
    finalContent: undefined, // Agent chat uses thought as primary content
    doneSummary: item.doneSummary,
    doneNextSteps: item.doneNextSteps,
    errorText: item.error?.message,
    errorDetail: item.error ? {
      type: item.error.error_type,
      suggestion: item.error.suggestion,
      retryable: item.error.retryable,
    } : undefined,
  };
}

// ============ Task status helpers ============

function normalizeTaskStatus(status?: string): TaskUiStatus {
  const s = (status || "pending").toLowerCase();
  if (s === "completed" || s === "done" || s === "success" || s === "succeeded") return "completed";
  if (s === "running" || s === "in_progress" || s === "in-progress") return "running";
  if (s === "failed" || s === "error") return "failed";
  if (s === "cancelled" || s === "canceled") return "cancelled";
  return "pending";
}

function normalizeTask(task: Partial<UiTaskItem> & Record<string, any>): UiTaskItem {
  const id = String(task.id ?? task.task_id ?? "");
  const title = String(task.title || task.content || `Task ${id || "-"}`);
  return {
    ...(task as UiTaskItem),
    id,
    title,
    status: normalizeTaskStatus(String(task.status || "pending")),
  };
}

// ============ Exposed methods (API for AgentWorkspace) ============

function addUserMessage(content: string) {
  chatItems.value.push({ id: `user-${Date.now()}`, type: "user", content });
  scrollToBottom();
}

function createAgentBlock(): string {
  const blockId = `agent-${Date.now()}`;
  chatItems.value.push({
    id: blockId, type: "agent-block",
    thoughtText: "", tasks: [], toolCalls: [], fileChanges: [],
    isActive: true,
  });
  scrollToBottom();
  return blockId;
}

function appendThought(blockId: string, payload: ThoughtPayload) {
  const block = findBlock(blockId);
  if (!block) return;
  block.isThinking = true;
  if (payload.phase) block.currentPhase = payload.phase;
  if (payload.reason) block.thoughtReason = payload.reason;
  if (payload.expected_outcome) block.thoughtExpectedOutcome = payload.expected_outcome;

  const incoming = payload.content || "";
  if (payload.mode === "replace") {
    if (incoming.length <= 120) {
      block.thoughtText = incoming;
      scrollToBottom();
      return;
    }
    block.thoughtText = "";
    const chunks = incoming.match(/[\s\S]{1,40}/g) || [];
    let idx = 0;
    const pushChunk = () => {
      const current = findBlock(blockId);
      if (!current) return;
      current.thoughtText = (current.thoughtText || "") + (chunks[idx] || "");
      idx += 1;
      scrollToBottom();
      if (idx < chunks.length) {
        window.setTimeout(pushChunk, 12);
      }
    };
    pushChunk();
    return;
  }

  block.thoughtText = (block.thoughtText || "") + incoming;
  scrollToBottom();
}

function updateTasks(blockId: string, tasks: TaskItem[]) {
  const block = findBlock(blockId);
  if (!block) return;

  const prev = block.tasks || [];
  const prevMap = new Map(prev.map(task => [String(task.id), task]));
  const next: UiTaskItem[] = [];
  const incomingIds = new Set<string>();

  for (const raw of tasks as any[]) {
    const normalized = normalizeTask({ ...prevMap.get(String(raw?.id ?? raw?.task_id ?? "")), ...raw });
    if (!normalized.id) continue;
    incomingIds.add(normalized.id);
    next.push(normalized);
  }

  if (next.length > 0 && next.length < prev.length) {
    for (const oldTask of prev) {
      if (!incomingIds.has(String(oldTask.id))) {
        next.push(oldTask);
      }
    }
  }

  block.tasks = next;
  scrollToBottom();
}

function addToolCall(blockId: string, payload: ToolCallPayload) {
  const block = findBlock(blockId);
  if (!block) return;
  block.toolCalls = block.toolCalls || [];

  if (payload.status === "running") {
    block.toolCalls.push({
      tool_call_id: payload.tool_call_id,
      tool_name: payload.tool_name,
      tool_args: payload.tool_args,
      status: "running",
      icon: payload.icon,
      reason: payload.reason,
      expected_outcome: payload.expected_outcome,
    });
  } else {
    // Match by tool_call_id first, then by tool_name.
    let matched = false;
    if (payload.tool_call_id) {
      for (let i = block.toolCalls.length - 1; i >= 0; i--) {
        if (block.toolCalls[i].tool_call_id === payload.tool_call_id) {
          block.toolCalls[i].status = payload.status;
          block.toolCalls[i].tool_result = payload.tool_result;
          if (payload.reason) block.toolCalls[i].reason = payload.reason;
          if (payload.expected_outcome) block.toolCalls[i].expected_outcome = payload.expected_outcome;
          if (payload.reflection) block.toolCalls[i].reflection = payload.reflection;
          matched = true;
          break;
        }
      }
    }
    if (!matched) {
      for (let i = block.toolCalls.length - 1; i >= 0; i--) {
        if (block.toolCalls[i].tool_name === payload.tool_name && block.toolCalls[i].status === "running") {
          block.toolCalls[i].status = payload.status;
          block.toolCalls[i].tool_result = payload.tool_result;
          if (payload.reason) block.toolCalls[i].reason = payload.reason;
          if (payload.expected_outcome) block.toolCalls[i].expected_outcome = payload.expected_outcome;
          if (payload.reflection) block.toolCalls[i].reflection = payload.reflection;
          matched = true;
          break;
        }
      }
    }
    // Fallback: backend only sent completed/failed without a prior running event.
    if (!matched) {
      block.toolCalls.push({
        tool_call_id: payload.tool_call_id,
        tool_name: payload.tool_name,
        tool_args: payload.tool_args,
        tool_result: payload.tool_result,
        status: payload.status,
        icon: payload.icon,
        reason: payload.reason,
        expected_outcome: payload.expected_outcome,
        reflection: payload.reflection,
      });
    }
  }

  // Sync task status when task_update tool completes.
  if (payload.status === "completed" && payload.tool_name === "task_update" && block.tasks?.length) {
    const taskId = String(payload.tool_args?.task_id ?? payload.tool_args?.id ?? "");
    const status = String(payload.tool_args?.status || "");
    if (taskId) {
      block.tasks = block.tasks.map(task =>
        String(task.id) === taskId
          ? { ...task, status: normalizeTaskStatus(status || task.status) }
          : task
      );
    }
  }

  scrollToBottom();
}

function addFileChange(blockId: string, change: FileChangeEntry) {
  const block = findBlock(blockId);
  if (!block) return;
  block.fileChanges = block.fileChanges || [];
  const existing = block.fileChanges.find(f => f.filepath === change.filepath);
  if (existing) {
    existing.operation = change.operation;
    if ((change as any).artifactId) existing.artifactId = (change as any).artifactId;
  } else {
    block.fileChanges.push(change);
  }
  scrollToBottom();
}

function addLog(blockId: string, log: { text: string; icon?: string; isActive?: boolean }) {
  const block = findBlock(blockId);
  if (!block) return;
  block.statusText = log.text;
  block.statusIcon = log.icon;
  scrollToBottom();
}

function setDone(blockId: string, summary?: string, nextSteps?: string[]) {
  const block = findBlock(blockId);
  if (!block) return;
  block.isActive = false;
  block.isThinking = false;
  block.currentPhase = "done";
  block.statusText = "";
  block.doneSummary = summary;
  block.doneNextSteps = nextSteps;
  scrollToBottom();
}

function setError(blockId: string, error: ErrorPayload) {
  const block = findBlock(blockId);
  if (!block) return;
  block.isActive = false;
  block.isThinking = false;
  block.error = error;
  scrollToBottom();
}

function reset() {
  chatItems.value = [];
}

defineExpose({ addUserMessage, createAgentBlock, appendThought, updateTasks, addToolCall, addFileChange, addLog, setDone, setError, reset });

// ============ Internal helpers ============

function findBlock(blockId: string): ChatItem | undefined {
  return chatItems.value.find(item => item.id === blockId);
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainerRef.value) chatContainerRef.value.scrollTop = chatContainerRef.value.scrollHeight;
  });
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
}

function handleSend() {
  if (!canSend.value) return;
  const text = inputText.value.trim();
  inputText.value = "";
  emit("send", text);
}

function briefArgs(args?: Record<string, any>): string {
  if (!args) return "";
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = args[keys[0]];
  const val = typeof first === "string" ? first : JSON.stringify(first);
  return val.length > 60 ? val.slice(0, 60) + "..." : val;
}

// ============ File change helpers (agent-chat specific) ============

function fileIcon(op?: string) { return ({ create: FilePlus, update: FileEdit, delete: Trash2, view: File } as Record<string, any>)[op || "view"] || File; }
function fileIconClass(op?: string): string { return ({ create: "text-green-500", update: "text-blue-500", delete: "text-red-500", view: "text-muted-foreground" } as Record<string, string>)[op || "view"] || "text-muted-foreground"; }
function fileBadgeClass(op?: string): string {
  return ({
    create: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    update: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    view: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
  } as Record<string, string>)[op || "view"] || "";
}
function fileLabel(op?: string): string { return ({ create: "New", update: "Modified", delete: "Deleted", view: "View" } as Record<string, string>)[op || "view"] || ""; }

onMounted(() => { inputRef.value?.focus(); });
</script>

<style scoped>
.agent-chat-panel { min-height: 300px; }
textarea { min-height: 44px; max-height: 120px; }
</style>
