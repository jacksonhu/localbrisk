<template>
  <div class="model-chat-panel h-full flex flex-col">
    <!-- 顶部状态栏 -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background">
      <div class="flex items-center gap-2">
        <Cpu class="w-5 h-5 text-orange-500" />
        <span class="font-medium text-sm">{{ modelName }}</span>
        <span
          class="text-xs px-2 py-0.5 rounded-full"
          :class="isStreaming
            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'"
        >
          {{ isStreaming ? '生成中' : '就绪' }}
        </span>
      </div>
      <button @click="handleClear" class="p-1.5 rounded-lg hover:bg-muted transition-colors" title="清空">
        <Trash2 class="w-4 h-4 text-muted-foreground" />
      </button>
    </div>

    <!-- 对话内容 -->
    <div ref="chatRef" class="flex-1 overflow-y-auto p-4 space-y-4">
      <div v-if="messages.length === 0" class="h-full flex flex-col items-center justify-center text-center">
        <Cpu class="w-16 h-16 text-muted-foreground/20 mb-4" />
        <h3 class="text-lg font-medium mb-2">模型调试</h3>
        <p class="text-muted-foreground text-sm max-w-md">直接与模型对话，验证模型是否可用</p>
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
            {{ msg.content }}
          </div>
        </div>
        <!-- 模型回复 -->
        <div v-else class="flex justify-start">
          <div class="max-w-[85%] bg-muted rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm">
            <div class="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap break-words">{{ msg.content }}</div>
            <span v-if="msg.isStreaming" class="typing-cursor"></span>
            <div v-if="msg.error" class="mt-2 text-xs text-red-500 flex items-center gap-1">
              <AlertCircle class="w-3 h-3" /> {{ msg.error }}
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 输入区域 -->
    <div class="border-t border-border p-3">
      <div class="flex items-end gap-3">
        <div class="flex-1 relative">
          <textarea
            ref="inputRef" v-model="inputText" @keydown="handleKeydown"
            placeholder="输入内容，按 Enter 发送..." :disabled="isStreaming"
            class="w-full px-4 py-3 pr-12 bg-muted rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 text-sm"
            :rows="Math.min(Math.max(inputText.split('\n').length, 1), 5)"
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
import { Cpu, Trash2, Send, AlertCircle } from "lucide-vue-next";
import { modelRuntimeApi } from "@/services/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  error?: string;
}

const props = defineProps<{
  businessUnitId: string;
  agentName: string;
  modelName: string;
}>();

const chatRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const inputText = ref("");
const messages = ref<ChatMessage[]>([]);
const isStreaming = ref(false);
const isModelLoaded = ref(false);

const canSend = computed(() => inputText.value.trim().length > 0 && !isStreaming.value);

function scrollToBottom() {
  nextTick(() => {
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight;
  });
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
}

async function handleSend() {
  if (!canSend.value) return;
  const text = inputText.value.trim();
  inputText.value = "";

  // 添加用户消息
  messages.value.push({ id: `u-${Date.now()}`, role: "user", content: text });
  scrollToBottom();

  // 创建助手消息占位
  const assistantId = `a-${Date.now()}`;
  messages.value.push({ id: assistantId, role: "assistant", content: "", isStreaming: true });
  scrollToBottom();

  isStreaming.value = true;

  try {
    // 确保模型已加载
    if (!isModelLoaded.value) {
      updateAssistant(assistantId, "正在加载模型...\n");
      await modelRuntimeApi.load(props.businessUnitId, props.agentName, props.modelName);
      isModelLoaded.value = true;
      updateAssistant(assistantId, "");
    }

    // 流式调用
    for await (const event of modelRuntimeApi.executeStream(
      props.businessUnitId, props.agentName, props.modelName,
      { input: text }
    )) {
      if (event.event_type === "done") break;
      if (event.event_type === "error") {
        setAssistantError(assistantId, event.error || "执行失败");
        break;
      }
      // 处理流式文本（兼容多种字段名）
      const chunk = event.message || event.content || event.text || event.delta || "";
      if (chunk) {
        // message_received 是完整消息，直接替换；其他是增量追加
        if (event.event_type === "message_received") {
          updateAssistant(assistantId, chunk);
        } else {
          appendToAssistant(assistantId, chunk);
        }
      }
    }
  } catch (err: any) {
    setAssistantError(assistantId, err.message || "请求失败");
  } finally {
    finishAssistant(assistantId);
    isStreaming.value = false;
  }
}

function updateAssistant(id: string, content: string) {
  const msg = messages.value.find(m => m.id === id);
  if (msg) { msg.content = content; scrollToBottom(); }
}

function appendToAssistant(id: string, chunk: string) {
  const msg = messages.value.find(m => m.id === id);
  if (msg) { msg.content += chunk; scrollToBottom(); }
}

function setAssistantError(id: string, error: string) {
  const msg = messages.value.find(m => m.id === id);
  if (msg) { msg.error = error; msg.isStreaming = false; scrollToBottom(); }
}

function finishAssistant(id: string) {
  const msg = messages.value.find(m => m.id === id);
  if (msg) msg.isStreaming = false;
}

function handleClear() {
  messages.value = [];
}

onMounted(() => { inputRef.value?.focus(); });
</script>

<style scoped>
.model-chat-panel { min-height: 300px; }
textarea { min-height: 44px; max-height: 120px; }

.typing-cursor {
  display: inline-block; width: 2px; height: 1em;
  background-color: currentColor; margin-left: 2px;
  animation: blink 1s step-end infinite; vertical-align: text-bottom;
}
@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }
</style>
