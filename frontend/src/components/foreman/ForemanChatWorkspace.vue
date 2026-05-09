<template>
  <section class="h-full flex flex-col min-h-0 bg-background">
    <!-- Header bar -->
    <div v-if="conversation" class="px-6 py-3 border-b border-border bg-card/80 backdrop-blur-sm">
      <div class="flex items-center justify-between gap-4">
        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <h2 class="text-base font-semibold text-foreground truncate">{{ conversation.title }}</h2>
            <span class="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium">
              {{ conversation.type === 'group' ? 'Group' : 'Direct' }}
            </span>
          </div>
          <p class="text-xs text-muted-foreground mt-0.5 truncate">{{ memberLine }}</p>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <span class="text-xs text-muted-foreground">{{ members.length }} members</span>
          <button
            type="button"
            class="h-9 w-9 rounded-lg border border-border bg-background text-foreground flex items-center justify-center transition-colors hover:bg-muted"
            title="Add members"
            @click="showPicker = true"
          >
            <UserRoundPlus class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Message area -->
    <div v-if="conversation" ref="messageContainerRef" class="flex-1 min-h-0 overflow-y-auto px-6 py-5 space-y-6">
      <template v-for="message in conversation.messages" :key="message.id">
        <!-- System message -->
        <div v-if="message.role === 'system'" class="flex justify-center">
          <div class="inline-flex items-center rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
            {{ message.content }}
          </div>
        </div>

        <!-- User message -->
        <div v-else-if="message.role === 'user'" class="flex justify-end gap-3">
          <div class="max-w-[75%]">
            <div class="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-6 shadow-sm">
              {{ message.content }}
            </div>
            <p class="text-[11px] text-muted-foreground mt-1 text-right px-1">
              {{ formatMessageTime(message.createdAt) }}
            </p>
          </div>
          <div class="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
            <User class="w-4 h-4 text-primary" />
          </div>
        </div>

        <!-- Agent message: avatar + unified execution block -->
        <div v-else class="flex gap-3">
          <!-- Agent avatar -->
          <div
            class="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-sm font-semibold"
            :style="getAgentAvatarStyle(message)"
          >
            {{ getAgentInitials(message.senderName) }}
          </div>

          <div class="flex-1 min-w-0 max-w-[85%]">
            <!-- Agent name -->
            <p class="text-xs font-medium text-muted-foreground mb-1.5">{{ message.senderName }}</p>

            <!-- Unified execution block via shared component -->
            <div class="bg-card border border-border rounded-2xl rounded-tl-sm shadow-sm overflow-hidden">
              <AgentExecutionBlock :data="toExecutionBlockData(message)" />
            </div>

            <!-- Action bar: time + copy -->
            <div class="flex items-center justify-between px-1 mt-1">
              <p class="text-[11px] text-muted-foreground">{{ formatMessageTime(message.createdAt) }}</p>
              <button
                v-if="message.content"
                class="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors rounded px-1.5 py-0.5"
                @click="copyContent(message)"
              >
                <Copy class="w-3 h-3" />
                <span>{{ copiedId === message.id ? 'Copied' : 'Copy' }}</span>
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- Typing indicator -->
      <div v-if="typingMembers.length > 0" class="flex gap-3">
        <div class="w-9 h-9 rounded-full bg-muted flex items-center justify-center shrink-0">
          <Loader2 class="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
        <div class="rounded-2xl rounded-tl-sm border border-dashed border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          {{ typingMembers.join(', ') }} typing...
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="flex-1 min-h-0 flex items-center justify-center px-8">
      <div class="max-w-md text-center">
        <MessagesSquare class="w-14 h-14 mx-auto text-muted-foreground/35 mb-4" />
        <h3 class="text-lg font-semibold text-foreground">Start a conversation</h3>
        <p class="text-sm text-muted-foreground mt-2 leading-6">Select an agent from the sidebar to begin chatting.</p>
      </div>
    </div>

    <!-- Input area -->
    <div class="px-6 pb-5 pt-3 border-t border-border bg-card/90 backdrop-blur-sm">
      <div class="rounded-2xl border border-border bg-card shadow-sm px-4 py-3">
        <textarea
          :value="modelValue"
          rows="2"
          placeholder="Type your message..."
          class="w-full resize-none bg-transparent text-sm leading-6 outline-none placeholder:text-muted-foreground/60 disabled:cursor-not-allowed"
          :disabled="!conversation || isSending"
          @input="handleInput"
          @keydown="handleKeydown"
        />
        <div class="mt-2 flex items-center justify-between gap-3">
          <p class="text-xs text-muted-foreground">Enter to send · Shift+Enter for new line</p>
          <button
            class="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors"
            :class="canSend
              ? 'bg-primary text-primary-foreground hover:bg-primary/90'
              : 'bg-muted text-muted-foreground cursor-not-allowed'"
            :disabled="!canSend"
            @click="$emit('send')"
          >
            <SendHorizontal class="w-4 h-4" />
            <span>{{ isSending ? 'Sending...' : 'Send' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Agent picker dialog -->
    <ForemanAgentPickerDialog
      v-model="selectedAgentIds"
      :is-open="showPicker"
      :conversation="conversation"
      :agents="allAgents"
      @close="handleClosePicker"
      @confirm="handleConfirmAddAgents"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
  Copy,
  Loader2,
  MessagesSquare,
  SendHorizontal,
  User,
  UserRoundPlus,
} from "lucide-vue-next";
import AgentExecutionBlock from "@/components/common/AgentExecutionBlock.vue";
import ForemanAgentPickerDialog from "@/components/foreman/ForemanAgentPickerDialog.vue";
import type { ExecutionBlockData, ExecutionStep } from "@/types/execution-block";
import type { ForemanAgentDirectoryItem, ForemanConversation, ForemanMessage } from "@/types/foreman";

const props = defineProps<{
  conversation: ForemanConversation | null;
  members: ForemanAgentDirectoryItem[];
  allAgents: ForemanAgentDirectoryItem[];
  typingAgentIds: string[];
  modelValue: string;
  isSending: boolean;
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
  (event: "send"): void;
  (event: "add-agents", agentIds: string[]): void;
}>();

// ---- State ----

const messageContainerRef = ref<HTMLElement | null>(null);
const showPicker = ref(false);
const selectedAgentIds = ref<string[]>([]);
const copiedId = ref<string | null>(null);

// ---- Computed ----

const memberLine = computed(() => props.members.map((m) => m.displayName).join(", "));
const typingMembers = computed(() =>
  props.typingAgentIds
    .map((id) => props.members.find((m) => m.id === id)?.displayName)
    .filter((n): n is string => Boolean(n)),
);
const canSend = computed(() =>
  Boolean(props.conversation) && Boolean(props.modelValue.trim()) && !props.isSending,
);

// ---- ForemanMessage → ExecutionBlockData adapter ----

/** Convert ForemanMessage to the shared ExecutionBlockData interface. */
function toExecutionBlockData(msg: ForemanMessage): ExecutionBlockData {
  const steps: ExecutionStep[] = [];

  // Merge tasks into step flow.
  if (msg.tasks) {
    for (const task of msg.tasks) {
      steps.push({
        id: `task-${task.id}`,
        category: "task",
        label: task.title,
        title: task.title,
        description: task.description,
        status: task.status === "cancelled" ? "failed" : (task.status as ExecutionStep["status"]),
      });
    }
  }

  // Merge tool calls into step flow.
  if (msg.toolCalls) {
    for (const tc of msg.toolCalls) {
      steps.push({
        id: `tc-${tc.toolCallId || tc.toolName}-${steps.length}`,
        category: "tool_call",
        label: "Call",
        title: tc.toolName,
        description: tc.reason || briefToolArgs(tc.toolArgs),
        status: tc.status,
        toolArgs: tc.toolArgs,
        toolResult: tc.toolResult,
        reflection: tc.reflection,
      });
    }
  }

  return {
    isExecuting: Boolean(msg.isExecuting),
    steps,
    thoughtText: msg.thoughtText || undefined,
    currentPhase: msg.currentPhase,
    isThinking: msg.isExecuting,
    finalContent: msg.content || undefined,
    doneSummary: msg.doneSummary,
    doneNextSteps: msg.doneNextSteps,
    errorText: msg.errorText,
  };
}

function briefToolArgs(args?: Record<string, any>): string {
  if (!args) return "";
  const keys = Object.keys(args);
  if (keys.length === 0) return "";
  const first = args[keys[0]];
  const val = typeof first === "string" ? first : JSON.stringify(first);
  return val.length > 60 ? val.slice(0, 60) + "..." : val;
}

// ---- Message helpers ----

function getAgentAvatarStyle(message: ForemanMessage): Record<string, string> {
  const color = message.senderColor || "#2563EB";
  return {
    backgroundColor: `${color}1A`,
    color: color,
  };
}

function getAgentInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] || "")
    .join("")
    .toUpperCase() || "A";
}

function formatMessageTime(value: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return "";
  }
}

async function copyContent(message: ForemanMessage): Promise<void> {
  try {
    await navigator.clipboard.writeText(message.content || message.doneSummary || "");
    copiedId.value = message.id;
    setTimeout(() => {
      if (copiedId.value === message.id) copiedId.value = null;
    }, 2000);
  } catch {
    // Clipboard API may not be available.
  }
}

// ---- Input handlers ----

function handleInput(event: Event): void {
  emit("update:modelValue", (event.target as HTMLTextAreaElement).value);
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (canSend.value) emit("send");
  }
}

// ---- Picker ----

function handleClosePicker(): void {
  showPicker.value = false;
  selectedAgentIds.value = [];
}

function handleConfirmAddAgents(): void {
  if (selectedAgentIds.value.length === 0) return;
  emit("add-agents", selectedAgentIds.value);
  handleClosePicker();
}

// ---- Scroll management ----

async function scrollToBottom(): Promise<void> {
  await nextTick();
  if (messageContainerRef.value) {
    messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
  }
}

watch(
  () => props.conversation?.messages.length,
  () => scrollToBottom(),
  { immediate: true },
);

watch(
  () => props.conversation?.id,
  () => {
    handleClosePicker();
    scrollToBottom();
  },
  { immediate: true },
);
</script>
