<template>
  <div class="agent-chat-panel h-full flex flex-col">
    <!-- 对话内容区 -->
    <div ref="chatContainerRef" class="chat-content flex-1 overflow-y-auto">
      <div v-if="chatItems.length === 0 && !isExecuting" class="h-full flex flex-col items-center justify-center text-center p-8">
        <Bot class="w-16 h-16 text-muted-foreground/20 mb-4" />
        <h3 class="text-lg font-medium mb-2">开始对话</h3>
        <p class="text-muted-foreground text-sm max-w-md">输入您的问题，Agent 将为您分析并生成结果</p>
      </div>

      <div class="chat-stream p-4 space-y-4">
        <template v-for="item in chatItems" :key="item.id">
          <!-- 用户消息 -->
          <div v-if="item.type === 'user'" class="flex justify-end">
            <div class="user-bubble max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
              {{ item.content }}
            </div>
          </div>

          <!-- Agent 执行块 -->
          <div v-else-if="item.type === 'agent-block'" class="agent-block">
            <!-- 思考过程 -->
            <div v-if="item.thoughtText" class="thought-section mb-3">
              <div class="thought-toggle flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted/50 transition-colors" @click="toggle(item.id, 'thought')">
                <Brain class="w-4 h-4 text-purple-500" />
                <span class="text-xs font-medium text-purple-600 dark:text-purple-400">{{ getPhaseLabel(item.currentPhase) }}</span>
                <ChevronDown class="w-3.5 h-3.5 text-muted-foreground transition-transform duration-200 ml-auto" :class="{ 'rotate-180': !isOpen(item.id, 'thought') }" />
              </div>
              <Transition name="expand">
                <div v-if="isOpen(item.id, 'thought')" class="thought-content px-3 pb-2">
                  <div class="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed text-muted-foreground markdown-body" v-html="renderMarkdown(item.thoughtText)"></div>
                  <div v-if="item.thoughtReason || item.thoughtExpectedOutcome" class="mt-2 space-y-1">
                    <p v-if="item.thoughtReason" class="text-xs text-muted-foreground"><span class="font-medium">为什么做：</span>{{ item.thoughtReason }}</p>
                    <p v-if="item.thoughtExpectedOutcome" class="text-xs text-muted-foreground"><span class="font-medium">预期结果：</span>{{ item.thoughtExpectedOutcome }}</p>
                  </div>
                  <span v-if="item.isThinking" class="typing-cursor"></span>
                </div>
              </Transition>
            </div>

            <!-- 任务清单 -->
            <div v-if="item.tasks && item.tasks.length > 0" class="task-section mb-3">
              <div class="task-card bg-muted/30 rounded-xl border border-border/50 overflow-hidden">
                <div class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-muted/50 transition-colors" @click="toggle(item.id, 'tasks')">
                  <div class="flex items-center gap-2">
                    <ListChecks class="w-4 h-4 text-primary" />
                    <span class="text-sm font-medium">{{ completedCount(item.tasks) }}/{{ item.tasks.length }} 任务</span>
                    <span v-if="allDone(item.tasks)" class="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">全部完成</span>
                    <span v-else-if="hasRunning(item.tasks)" class="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 flex items-center gap-1">
                      <Loader2 class="w-3 h-3 animate-spin" /> 执行中
                    </span>
                  </div>
                  <ChevronDown class="w-4 h-4 text-muted-foreground transition-transform duration-200" :class="{ 'rotate-180': !isOpen(item.id, 'tasks') }" />
                </div>
                <Transition name="expand">
                  <div v-if="isOpen(item.id, 'tasks')" class="px-3 pb-3">
                    <div class="h-1.5 bg-muted rounded-full overflow-hidden mb-3">
                      <div class="h-full bg-primary transition-all duration-300" :style="{ width: `${progressPct(item.tasks)}%` }" />
                    </div>
                    <div class="space-y-1.5">
                      <div v-for="task in item.tasks" :key="task.id"
                        class="flex items-start gap-2 py-1.5 px-2 rounded-lg transition-colors"
                        :class="{ 'bg-blue-50 dark:bg-blue-900/20': taskStatus(task) === 'running', 'opacity-60': taskStatus(task) === 'completed' }"
                      >
                        <div class="flex-shrink-0 mt-0.5">
                          <CheckCircle2 v-if="taskStatus(task) === 'completed'" class="w-4 h-4 text-green-500" />
                          <Loader2 v-else-if="taskStatus(task) === 'running'" class="w-4 h-4 text-blue-500 animate-spin" />
                          <Circle v-else-if="taskStatus(task) === 'pending'" class="w-4 h-4 text-muted-foreground" />
                          <XCircle v-else-if="taskStatus(task) === 'failed'" class="w-4 h-4 text-red-500" />
                          <AlertCircle v-else class="w-4 h-4 text-yellow-500" />
                        </div>
                        <div class="flex-1 min-w-0">
                          <span class="text-sm" :class="{ 'line-through text-muted-foreground': taskStatus(task) === 'completed', 'font-medium': taskStatus(task) === 'running' }">{{ taskTitle(task) }}</span>
                          <p v-if="task.error" class="text-xs text-red-500 mt-0.5">{{ task.error }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- 工具调用列表（默认收起） -->
            <div v-if="item.toolCalls && item.toolCalls.length > 0" class="tool-calls-section mb-3">
              <div class="tool-call-entry rounded-lg border border-border/50 overflow-hidden">
                <div class="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-muted/30 transition-colors" @click="toggle(item.id, 'toolCalls')">
                  <Wrench class="w-3.5 h-3.5 text-muted-foreground" />
                  <span class="text-xs font-medium text-muted-foreground">工具调用 {{ item.toolCalls.length }} 条</span>
                  <ChevronDown class="w-3 h-3 text-muted-foreground transition-transform duration-200 ml-auto" :class="{ 'rotate-180': isOpen(item.id, 'toolCalls') }" />
                </div>
                <Transition name="expand">
                  <div v-if="isOpen(item.id, 'toolCalls')" class="space-y-1.5 p-2 border-t border-border/30 bg-muted/20">
                    <div v-for="(tc, tcIdx) in item.toolCalls" :key="tcIdx" class="tool-call-entry rounded-lg border border-border/50 overflow-hidden">
                      <div class="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-muted/30 transition-colors" @click="toggleTc(item.id, tcIdx)">
                        <component :is="toolIcon(tc.icon)" class="w-3.5 h-3.5 flex-shrink-0" :class="toolIconClass(tc.status)" />
                        <span class="text-xs font-mono text-foreground/80 font-medium">{{ tc.tool_name }}</span>
                        <span v-if="tc.tool_args" class="text-xs text-muted-foreground truncate max-w-[200px]">{{ briefArgs(tc.tool_args) }}</span>
                        <Loader2 v-if="tc.status === 'running'" class="w-3 h-3 animate-spin text-blue-500 ml-auto flex-shrink-0" />
                        <CheckCircle2 v-else-if="tc.status === 'completed'" class="w-3 h-3 text-green-500 ml-auto flex-shrink-0" />
                        <XCircle v-else-if="tc.status === 'failed'" class="w-3 h-3 text-red-500 ml-auto flex-shrink-0" />
                        <ChevronDown class="w-3 h-3 text-muted-foreground transition-transform duration-200 flex-shrink-0" :class="{ 'rotate-180': !isTcOpen(item.id, tcIdx) }" />
                      </div>
                      <Transition name="expand">
                        <div v-if="isTcOpen(item.id, tcIdx)" class="tool-call-detail border-t border-border/30 bg-muted/20">
                          <div v-if="tc.tool_args && Object.keys(tc.tool_args).length > 0" class="px-3 py-2">
                            <div class="text-xs text-muted-foreground mb-1 font-medium">参数</div>
                            <pre class="text-xs font-mono bg-gray-900 dark:bg-gray-950 text-green-400 rounded p-2 overflow-x-auto max-h-40 overflow-y-auto">{{ fmtJson(tc.tool_args) }}</pre>
                          </div>
                          <div v-if="tc.reason || tc.expected_outcome" class="px-3 py-2 border-t border-border/20 space-y-1">
                            <p v-if="tc.reason" class="text-xs text-muted-foreground"><span class="font-medium">为什么做：</span>{{ tc.reason }}</p>
                            <p v-if="tc.expected_outcome" class="text-xs text-muted-foreground"><span class="font-medium">预期结果：</span>{{ tc.expected_outcome }}</p>
                          </div>
                          <div v-if="tc.tool_result || tc.reflection" class="px-3 py-2 border-t border-border/20">
                            <div v-if="tc.tool_result" class="mb-2">
                              <div class="text-xs text-muted-foreground mb-1 font-medium">结果</div>
                              <pre class="text-xs font-mono bg-gray-900 dark:bg-gray-950 text-gray-300 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap break-all">{{ tc.tool_result }}</pre>
                            </div>
                            <p v-if="tc.reflection" class="text-xs text-muted-foreground"><span class="font-medium">反思：</span>{{ tc.reflection }}</p>
                          </div>
                        </div>
                      </Transition>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- 文件变更 -->
            <div v-if="item.fileChanges && item.fileChanges.length > 0" class="file-changes-section mb-3">
              <div class="text-xs font-medium text-muted-foreground px-3 mb-1.5">文件变更</div>
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

            <!-- 完成总结 -->
            <div v-if="item.doneSummary" class="done-section p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-200 dark:border-green-800/30">
              <div class="flex items-center gap-2 mb-1">
                <CheckCircle2 class="w-4 h-4 text-green-500" />
                <span class="text-sm font-medium text-green-700 dark:text-green-400">执行完成</span>
              </div>
              <p class="text-sm text-green-600 dark:text-green-300">{{ item.doneSummary }}</p>
              <div v-if="item.doneNextSteps?.length" class="mt-2 space-y-1">
                <p class="text-xs font-medium text-muted-foreground">建议后续步骤：</p>
                <div v-for="(step, sIdx) in item.doneNextSteps" :key="sIdx" class="text-xs flex items-start gap-1.5">
                  <span class="text-primary mt-0.5">→</span><span>{{ step }}</span>
                </div>
              </div>
            </div>

            <!-- 错误信息 -->
            <div v-if="item.error" class="error-section p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-800/30">
              <div class="flex items-center gap-2 mb-1">
                <AlertCircle class="w-4 h-4 text-red-500" />
                <span class="text-sm font-medium text-red-600 dark:text-red-400">{{ item.error.error_type || '错误' }}</span>
              </div>
              <p class="text-sm text-red-600 dark:text-red-300">{{ item.error.message }}</p>
              <p v-if="item.error.suggestion" class="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <Lightbulb class="w-3 h-3 text-yellow-500" /> {{ item.error.suggestion }}
              </p>
              <button v-if="item.error.retryable" @click="$emit('retry')" class="mt-2 text-xs px-3 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors">重试</button>
            </div>

            <!-- 状态提示 -->
            <div v-if="item.statusText && item.isActive && !item.doneSummary && !item.error" class="status-section flex items-center gap-2 px-3 py-1.5 mb-1">
              <Loader2 class="w-3.5 h-3.5 animate-spin text-muted-foreground" />
              <span class="text-xs text-muted-foreground">{{ item.statusText }}</span>
            </div>

            <!-- 加载占位 -->
            <div v-if="item.isActive && !item.thoughtText && !item.tasks?.length && !item.toolCalls?.length" class="flex items-center gap-2 px-3 py-2">
              <Loader2 class="w-4 h-4 animate-spin text-primary" />
              <span class="text-sm text-muted-foreground">思考中...</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input border-t border-border p-3">
      <div class="flex items-end gap-3">
        <div class="flex-1 relative">
          <textarea
            ref="inputRef" v-model="inputText" @keydown="handleKeydown"
            placeholder="输入指令，按 Enter 发送..." :disabled="isExecuting"
            class="w-full px-4 py-3 pr-12 bg-muted rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 text-sm"
            :rows="inputRows"
          ></textarea>
          <button @click="handleSend" :disabled="!canSend"
            class="absolute right-3 bottom-3 p-1.5 rounded-lg transition-colors"
            :class="canSend ? 'bg-primary text-primary-foreground hover:bg-primary/90' : 'bg-muted-foreground/20 text-muted-foreground cursor-not-allowed'"
          ><Send class="w-4 h-4" /></button>
        </div>
      </div>
      <p class="text-xs text-muted-foreground mt-1.5">Enter 发送 · Shift+Enter 换行</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from "vue";
import {
  Bot, Brain, Send, Loader2, ListChecks, ChevronDown,
  CheckCircle2, Circle, XCircle, AlertCircle, Lightbulb,
  Search, Code, Wrench, File, Database, Play, FilePlus, FileEdit, Trash2, Terminal,
} from "lucide-vue-next";
import MarkdownIt from "markdown-it";
import type { TaskItem, ThoughtPayload, ErrorPayload, ToolCallPayload } from "@/types/stream-protocol";

// ============ 类型 ============

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

// ============ 状态 ============

const chatContainerRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const inputText = ref("");
const chatItems = ref<ChatItem[]>([]);
const expandedSections = ref<Set<string>>(new Set());
const expandedToolCalls = ref<Set<string>>(new Set());

const canSend = computed(() => inputText.value.trim().length > 0 && !props.isExecuting);
const inputRows = computed(() => Math.min(Math.max(inputText.value.split("\n").length, 1), 5));

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
  const title = String(task.title || task.content || `任务 ${id || "-"}`);
  return {
    ...(task as UiTaskItem),
    id,
    title,
    status: normalizeTaskStatus(String(task.status || "pending")),
  };
}

function taskStatus(task: Partial<UiTaskItem>): TaskUiStatus {
  return normalizeTaskStatus(task.status);
}

function taskTitle(task: Partial<UiTaskItem>): string {
  return task.title || (task as any).content || `任务 ${task.id || "-"}`;
}

// ============ 公开方法 ============

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
  expandedSections.value.add(`${blockId}:thought`);
  expandedSections.value.add(`${blockId}:tasks`);
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
    // 优先用 tool_call_id 精确匹配，其次用 tool_name 匹配最后一个 running 项
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

    // 兼容后端仅发 completed/failed（未先发 running）的场景
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
  if (existing) { existing.operation = change.operation; existing.artifactId = change.artifactId; }
  else { block.fileChanges.push(change); }
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
  expandedSections.value.clear();
  expandedToolCalls.value.clear();
}

defineExpose({ addUserMessage, createAgentBlock, appendThought, updateTasks, addToolCall, addFileChange, addLog, setDone, setError, reset });

// ============ 内部方法 ============

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

// ============ 折叠控制 ============

function toggle(id: string, section: string) {
  const key = `${id}:${section}`;
  expandedSections.value.has(key) ? expandedSections.value.delete(key) : expandedSections.value.add(key);
}
function isOpen(id: string, section: string): boolean {
  return expandedSections.value.has(`${id}:${section}`);
}
function toggleTc(blockId: string, idx: number) {
  const key = `${blockId}:tc:${idx}`;
  expandedToolCalls.value.has(key) ? expandedToolCalls.value.delete(key) : expandedToolCalls.value.add(key);
}
function isTcOpen(blockId: string, idx: number): boolean {
  return expandedToolCalls.value.has(`${blockId}:tc:${idx}`);
}

// ============ 辅助函数 ============

function completedCount(tasks: UiTaskItem[]): number {
  return tasks.filter(t => taskStatus(t) === "completed").length;
}

function allDone(tasks: UiTaskItem[]): boolean {
  return tasks.length > 0 && tasks.every(t => {
    const status = taskStatus(t);
    return status === "completed" || status === "cancelled";
  });
}

function hasRunning(tasks: UiTaskItem[]): boolean {
  return tasks.some(t => taskStatus(t) === "running");
}

function progressPct(tasks: UiTaskItem[]): number {
  return tasks.length === 0 ? 0 : Math.round((completedCount(tasks) / tasks.length) * 100);
}

function getPhaseLabel(phase?: string): string {
  return ({ planning: "规划中", analyzing: "分析中", reflecting: "反思中", searching: "搜索中", coding: "编码中", done: "已完成" } as Record<string, string>)[phase || ""] || "思考中";
}

function toolIcon(icon?: string) {
  return ({ search: Search, code: Code, tool: Wrench, file: File, database: Database, play: Play, brain: Brain, check: CheckCircle2, terminal: Terminal } as Record<string, any>)[icon || ""] || Wrench;
}
function toolIconClass(status?: string): string {
  return ({ running: "text-blue-500", completed: "text-green-500", failed: "text-red-500" } as Record<string, string>)[status || "running"] || "text-muted-foreground";
}
function briefArgs(args: Record<string, any>): string {
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = args[keys[0]];
  const val = typeof first === "string" ? first : JSON.stringify(first);
  return val.length > 60 ? val.slice(0, 60) + "..." : val;
}
function fmtJson(obj: any): string {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

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
function fileLabel(op?: string): string { return ({ create: "新建", update: "修改", delete: "删除", view: "查看" } as Record<string, string>)[op || "view"] || ""; }

const md = new MarkdownIt({ html: true, linkify: true, breaks: true });

md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  token.attrSet("target", "_blank");
  token.attrSet("rel", "noopener noreferrer nofollow");
  token.attrJoin("class", "cb-link");
  return self.renderToken(tokens, idx, options);
};

md.renderer.rules.fence = (tokens, idx) => {
  const token = tokens[idx];
  const lang = (token.info || "").trim().split(/\s+/)[0] || "text";
  const code = md.utils.escapeHtml(token.content || "");
  return `<div class="cb-code-card"><div class="cb-code-head">${lang}</div><pre class="code-block"><code class="language-${lang}">${code}</code></pre></div>`;
};

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function parseAttrMap(attrText: string): Record<string, string> {
  const map: Record<string, string> = {};
  const regex = /(\w+)="([^"]*)"/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(attrText)) !== null) {
    map[m[1]] = m[2];
  }
  return map;
}

function mapCustomComponents(input: string): string {
  let out = input;

  out = out.replace(/<cb-callout([^>]*)>([\s\S]*?)<\/cb-callout>/g, (_, attrs, body) => {
    const a = parseAttrMap(attrs || "");
    const type = (a.type || "info").toLowerCase();
    const title = a.title ? `<div class="cb-callout-title">${escapeHtml(a.title)}</div>` : "";
    return `<div class="cb-callout cb-callout-${escapeHtml(type)}">${title}<div class="cb-callout-body">${md.renderInline(body || "")}</div></div>`;
  });

  out = out.replace(/<cb-file([^>]*)\/>/g, (_, attrs) => {
    const a = parseAttrMap(attrs || "");
    const path = escapeHtml(a.path || "");
    const op = escapeHtml(a.op || "view");
    return `<div class="cb-file-card"><span class="cb-chip">文件</span><span class="cb-file-path">${path}</span><span class="cb-chip cb-chip-op">${op}</span></div>`;
  });

  out = out.replace(/<cb-tool([^>]*)\/>/g, (_, attrs) => {
    const a = parseAttrMap(attrs || "");
    const name = escapeHtml(a.name || "tool");
    const status = escapeHtml(a.status || "running");
    return `<div class="cb-tool-card"><span class="cb-chip">工具</span><span class="cb-tool-name">${name}</span><span class="cb-chip cb-chip-status">${status}</span></div>`;
  });

  return out;
}

function sanitizeUnsafeMarkup(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

function renderMarkdown(content: string): string {
  if (!content) return "";
  const mapped = mapCustomComponents(content);
  return md.render(sanitizeUnsafeMarkup(mapped));
}

onMounted(() => { inputRef.value?.focus(); });
</script>

<style scoped>
.agent-chat-panel { min-height: 300px; }
textarea { min-height: 44px; max-height: 120px; }

.typing-cursor {
  display: inline-block; width: 2px; height: 1em;
  background-color: currentColor; margin-left: 2px;
  animation: blink 1s step-end infinite; vertical-align: text-bottom;
}
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }

.expand-enter-active, .expand-leave-active { transition: all 0.2s ease; overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 2000px; }

.tool-call-entry { background: hsl(var(--muted) / 0.15); }

.markdown-body :deep(h1) { @apply text-xl font-bold mb-3 mt-4 first:mt-0; }
.markdown-body :deep(h2) { @apply text-lg font-bold mb-2 mt-3 first:mt-0; }
.markdown-body :deep(h3) { @apply text-base font-semibold mb-2 mt-2 first:mt-0; }
.markdown-body :deep(p) { @apply mb-2 last:mb-0; }
.markdown-body :deep(ul) { @apply my-2 pl-5 list-disc; }
.markdown-body :deep(li) { @apply mb-1; }
.markdown-body :deep(.inline-code) { @apply px-1.5 py-0.5 bg-muted-foreground/10 rounded text-primary font-mono text-xs; }
.markdown-body :deep(.cb-link) { @apply text-primary underline underline-offset-2; }
.markdown-body :deep(.cb-code-card) { @apply my-3 rounded-lg overflow-hidden border border-border/50; }
.markdown-body :deep(.cb-code-head) { @apply px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide bg-muted/60 text-muted-foreground; }
.markdown-body :deep(.code-block) { @apply m-0 p-3 bg-gray-900 dark:bg-gray-950 rounded-none overflow-x-auto; }
.markdown-body :deep(.code-block code) { @apply text-green-400 font-mono text-xs whitespace-pre; }
.markdown-body :deep(.cb-callout) { @apply my-2 p-3 rounded-lg border text-sm; }
.markdown-body :deep(.cb-callout-title) { @apply font-medium mb-1; }
.markdown-body :deep(.cb-callout-info) { @apply bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-200; }
.markdown-body :deep(.cb-callout-warning) { @apply bg-yellow-50 border-yellow-200 text-yellow-800 dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-200; }
.markdown-body :deep(.cb-callout-success) { @apply bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-200; }
.markdown-body :deep(.cb-callout-error) { @apply bg-red-50 border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800 dark:text-red-200; }
.markdown-body :deep(.cb-file-card),
.markdown-body :deep(.cb-tool-card) { @apply my-2 flex items-center gap-2 text-xs rounded-lg border border-border/50 px-2.5 py-2 bg-muted/20; }
.markdown-body :deep(.cb-file-path),
.markdown-body :deep(.cb-tool-name) { @apply font-mono text-foreground/80; }
.markdown-body :deep(.cb-chip) { @apply px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-[10px] uppercase tracking-wide; }
.markdown-body :deep(.cb-chip-op),
.markdown-body :deep(.cb-chip-status) { @apply bg-primary/10 text-primary; }
.markdown-body :deep(strong) { @apply font-semibold; }
.markdown-body :deep(em) { @apply italic; }
</style>
