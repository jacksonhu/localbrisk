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

    <!-- 双栏主区域 -->
    <div class="workspace-body flex-1 flex overflow-hidden">
      <!-- 左栏：对话面板 -->
      <div
        class="left-panel flex flex-col border-r border-border"
        :style="{ width: leftPanelWidth + 'px' }"
      >
        <AgentChatPanel
          ref="chatPanelRef"
          :is-executing="isExecuting"
          @send="handleSend"
          @retry="handleRetry"
          @open-artifact="handleOpenArtifact"
        />
      </div>

      <!-- 拖拽分割线 -->
      <div
        class="splitter w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/30 transition-colors flex-shrink-0"
        @mousedown="startResize"
      />

      <!-- 右栏：制品面板 -->
      <div class="right-panel flex-1 min-w-0">
        <ArtifactPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { Bot, Trash2 } from "lucide-vue-next";
import AgentChatPanel from "./AgentChatPanel.vue";
import ArtifactPanel from "./ArtifactPanel.vue";
import { useSSEClient } from "@/composables/useSSEClient";
import { useArtifactStore } from "@/stores/artifactStore";
import { agentRuntimeApi } from "@/services/api";
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
const leftPanelWidth = ref(480);
const currentBlockId = ref<string>("");

const artifactStore = useArtifactStore();

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

function handleStreamMessage(msg: StreamMessage) {
  const panel = chatPanelRef.value;
  if (!panel || !currentBlockId.value) return;

  switch (msg.type) {
    case "THOUGHT": {
      const payload = msg.payload as unknown as ThoughtPayload;
      panel.appendThought(currentBlockId.value, payload);
      break;
    }

    case "TASK_LIST": {
      const payload = msg.payload as unknown as TaskListPayload;
      panel.updateTasks(currentBlockId.value, payload.tasks);
      break;
    }

    case "TOOL_CALL": {
      const payload = msg.payload as unknown as ToolCallPayload;
      panel.addToolCall(currentBlockId.value, payload);
      break;
    }

    case "ARTIFACT": {
      const payload = msg.payload as unknown as ArtifactPayload;
      artifactStore.handleArtifact(payload);
      // 如果是代码/文件类型，在左栏显示文件变更预览
      if (payload.filepath || payload.artifact_type === "code") {
        panel.addFileChange(currentBlockId.value, {
          filepath: payload.filepath || payload.title || payload.artifact_id,
          operation: payload.operation || "create",
          artifactId: payload.artifact_id,
        });
      }
      break;
    }

    case "STATUS": {
      const payload = msg.payload as unknown as StatusPayload;
      panel.addLog(currentBlockId.value, {
        text: payload.text,
        icon: payload.icon,
        isActive: true,
      });
      break;
    }

    case "ERROR": {
      const payload = msg.payload as unknown as ErrorPayload;
      panel.setError(currentBlockId.value, payload);
      isExecuting.value = false;
      break;
    }

    case "DONE": {
      const payload = msg.payload as unknown as DonePayload;
      panel.setDone(currentBlockId.value, payload.summary, payload.next_steps);
      isExecuting.value = false;
      break;
    }
  }
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

  // 重置制品
  artifactStore.reset();

  // 启动流式请求
  await sseClient.executeStreamV2(
    props.businessUnitId,
    props.agentName || "",
    userInput
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

function handleReset() {
  sseClient.disconnect();
  chatPanelRef.value?.reset();
  artifactStore.reset();
  isExecuting.value = false;
  lastUserInput.value = "";
  currentBlockId.value = "";
}

function handleRetry() {
  if (lastUserInput.value) {
    handleSend(lastUserInput.value);
  }
}

function handleOpenArtifact(artifactId: string) {
  artifactStore.selectArtifact(artifactId);
}

// ============ 拖拽分割线 ============

let isResizing = false;

function startResize(e: MouseEvent) {
  isResizing = true;
  const startX = e.clientX;
  const startWidth = leftPanelWidth.value;

  function onMouseMove(ev: MouseEvent) {
    if (!isResizing) return;
    const diff = ev.clientX - startX;
    const newWidth = Math.max(320, Math.min(startWidth + diff, 800));
    leftPanelWidth.value = newWidth;
  }

  function onMouseUp() {
    isResizing = false;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  }

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

// ============ 生命周期 ============

watch(
  () => [props.businessUnitId, props.agentName],
  () => {
    handleReset();
    isAgentLoaded.value = false;
  }
);

onUnmounted(() => {
  sseClient.disconnect();
});
</script>

<style scoped>
.agent-workspace {
  min-height: 400px;
}

.left-panel {
  min-width: 320px;
  max-width: 800px;
}

.splitter:hover {
  transition-delay: 100ms;
}
</style>
