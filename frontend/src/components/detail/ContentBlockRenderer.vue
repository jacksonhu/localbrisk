<template>
  <div class="content-block" :class="blockClass">
    <!-- 文本块 -->
    <template v-if="block.type === 'text'">
      <div class="text-block" :class="textSentimentClass">
        <div class="prose prose-sm dark:prose-invert max-w-none" v-html="renderMarkdown(block.content)"></div>
      </div>
    </template>

    <!-- 命令块 -->
    <template v-else-if="block.type === 'command'">
      <div class="command-block" :class="{ 'is-dangerous': block.is_dangerous }">
        <div class="command-header">
          <div class="flex items-center gap-2">
            <Terminal class="w-4 h-4 text-green-500" />
            <span class="text-xs font-medium text-muted-foreground">
              {{ block.cwd || 'Terminal' }}
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              @click="copyCommand"
              class="p-1 rounded hover:bg-muted transition-colors"
              :title="t('common.copy')"
            >
              <Copy class="w-3.5 h-3.5 text-muted-foreground" />
            </button>
            <button
              v-if="!block.is_dangerous"
              @click="runCommand"
              class="p-1 rounded hover:bg-primary/10 transition-colors"
              :title="t('chat.runCommand')"
            >
              <Play class="w-3.5 h-3.5 text-primary" />
            </button>
          </div>
        </div>
        <div class="command-content">
          <code class="text-sm font-mono">{{ block.command }}</code>
        </div>
        <div v-if="block.explanation" class="command-explanation">
          <span class="text-xs text-muted-foreground">{{ block.explanation }}</span>
        </div>
        <div v-if="block.is_dangerous" class="command-warning">
          <AlertTriangle class="w-3.5 h-3.5 text-red-500" />
          <span class="text-xs text-red-500">{{ t('chat.dangerousCommand') }}</span>
        </div>
      </div>
    </template>

    <!-- 代码块 -->
    <template v-else-if="block.type === 'code'">
      <div class="code-block">
        <div class="code-header">
          <div class="flex items-center gap-2">
            <component :is="getOperationIcon(block.operation)" class="w-4 h-4" :class="operationIconClass" />
            <span class="text-xs font-medium">
              {{ block.filepath || block.filename || block.language }}
            </span>
            <span class="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {{ block.language }}
            </span>
            <span v-if="block.operation && block.operation !== 'view'" class="text-xs px-1.5 py-0.5 rounded" :class="operationBadgeClass">
              {{ getOperationLabel(block.operation) }}
            </span>
          </div>
          <div class="flex items-center gap-1">
            <button
              @click="copyCode"
              class="p-1 rounded hover:bg-muted transition-colors"
              :title="t('common.copy')"
            >
              <Copy class="w-3.5 h-3.5 text-muted-foreground" />
            </button>
          </div>
        </div>
        <div class="code-content">
          <pre class="text-sm"><code :class="`language-${block.language}`">{{ block.code }}</code></pre>
        </div>
        <div v-if="block.start_line" class="code-lines">
          <span class="text-xs text-muted-foreground">
            Lines {{ block.start_line }}-{{ block.end_line || block.start_line }}
          </span>
        </div>
      </div>
    </template>

    <!-- 图表块 -->
    <template v-else-if="block.type === 'chart'">
      <div class="chart-block">
        <div v-if="block.title" class="chart-header">
          <BarChart class="w-4 h-4 text-primary" />
          <span class="text-sm font-medium">{{ block.title }}</span>
        </div>
        <div class="chart-content">
          <!-- Mermaid 图表 -->
          <div v-if="block.chart_type === 'mermaid' || !block.chart_type" class="mermaid-container">
            <pre class="mermaid">{{ block.content }}</pre>
          </div>
          <!-- JSON 数据 -->
          <div v-else-if="block.chart_type === 'json_data'" class="json-chart">
            <pre class="text-xs">{{ formatJson(block.content) }}</pre>
          </div>
        </div>
      </div>
    </template>

    <!-- 表格块 -->
    <template v-else-if="block.type === 'table'">
      <div class="table-block">
        <div v-if="block.title" class="table-header">
          <Table class="w-4 h-4 text-primary" />
          <span class="text-sm font-medium">{{ block.title }}</span>
        </div>
        <div class="table-content overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr>
                <th v-for="(header, idx) in block.headers" :key="idx" class="px-3 py-2 text-left font-medium text-muted-foreground bg-muted/50">
                  {{ header }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIdx) in block.rows" :key="rowIdx" class="border-t border-border">
                <td v-for="(cell, cellIdx) in row" :key="cellIdx" class="px-3 py-2">
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="block.caption" class="table-caption">
          <span class="text-xs text-muted-foreground">{{ block.caption }}</span>
        </div>
      </div>
    </template>

    <!-- 文件块 -->
    <template v-else-if="block.type === 'file'">
      <div class="file-block" :class="fileOperationClass">
        <div class="flex items-center gap-2">
          <component :is="getFileOperationIcon(block.operation)" class="w-4 h-4" :class="fileIconClass" />
          <span class="text-sm font-medium truncate">{{ block.filename || block.filepath }}</span>
          <span v-if="block.file_type" class="text-xs text-muted-foreground">.{{ block.file_type }}</span>
        </div>
        <div v-if="block.size" class="text-xs text-muted-foreground">
          {{ formatFileSize(block.size) }}
        </div>
      </div>
    </template>

    <!-- 思考块 -->
    <template v-else-if="block.type === 'thinking'">
      <div class="thinking-block">
        <div class="thinking-header" @click="toggleThinking">
          <div class="flex items-center gap-2">
            <Brain class="w-4 h-4 text-purple-500" />
            <span class="text-sm font-medium">{{ getThinkingPhaseLabel(block.phase) }}</span>
          </div>
          <ChevronDown 
            class="w-4 h-4 text-muted-foreground transition-transform" 
            :class="{ 'rotate-180': !isThinkingCollapsed }"
          />
        </div>
        <Transition name="expand">
          <div v-if="!isThinkingCollapsed" class="thinking-content">
            <div class="prose prose-sm dark:prose-invert max-w-none text-muted-foreground" v-html="renderMarkdown(block.content)"></div>
          </div>
        </Transition>
      </div>
    </template>

    <!-- 错误块 -->
    <template v-else-if="block.type === 'error'">
      <div class="error-block">
        <div class="error-header">
          <AlertCircle class="w-4 h-4 text-red-500" />
          <span class="text-sm font-medium text-red-500">
            {{ block.error_type || t('chat.error') }}
          </span>
        </div>
        <div class="error-message">
          <span class="text-sm">{{ block.message }}</span>
        </div>
        <div v-if="block.traceback" class="error-traceback">
          <pre class="text-xs font-mono overflow-x-auto">{{ block.traceback }}</pre>
        </div>
        <div v-if="block.suggestion" class="error-suggestion">
          <Lightbulb class="w-3.5 h-3.5 text-yellow-500" />
          <span class="text-xs">{{ block.suggestion }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  Terminal, Copy, Play, AlertTriangle, Code, BarChart, Table,
  File, FileText, FilePlus, FileEdit, Trash2, Brain, ChevronDown,
  AlertCircle, Lightbulb, Eye
} from "lucide-vue-next";
import type { ContentBlock, CodeOperation, FileOperation, ThinkingPhase } from "@/types/agent-runtime";

const { t } = useI18n();

const props = defineProps<{
  block: ContentBlock;
}>();

const emit = defineEmits<{
  (e: "run-command", command: string, cwd?: string): void;
  (e: "copy", content: string): void;
}>();

// 思考块折叠状态
const isThinkingCollapsed = ref(props.block.type === "thinking" ? (props.block.collapsed ?? true) : true);

// 计算属性
const blockClass = computed(() => `block-${props.block.type}`);

const textSentimentClass = computed(() => {
  if (props.block.type !== "text") return "";
  const sentimentMap: Record<string, string> = {
    neutral: "",
    happy: "border-l-2 border-green-500 pl-3",
    alert: "border-l-2 border-blue-500 pl-3",
    warning: "border-l-2 border-yellow-500 pl-3",
    error: "border-l-2 border-red-500 pl-3",
  };
  return sentimentMap[props.block.sentiment || "neutral"];
});

const operationIconClass = computed(() => {
  if (props.block.type !== "code") return "";
  const classMap: Record<CodeOperation, string> = {
    view: "text-muted-foreground",
    create: "text-green-500",
    update: "text-blue-500",
    delete: "text-red-500",
    diff: "text-purple-500",
  };
  return classMap[props.block.operation || "view"];
});

const operationBadgeClass = computed(() => {
  if (props.block.type !== "code") return "";
  const classMap: Record<CodeOperation, string> = {
    view: "bg-muted text-muted-foreground",
    create: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    update: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    delete: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    diff: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  };
  return classMap[props.block.operation || "view"];
});

const fileOperationClass = computed(() => {
  if (props.block.type !== "file") return "";
  const classMap: Record<FileOperation, string> = {
    reference: "",
    created: "border-l-2 border-green-500",
    modified: "border-l-2 border-blue-500",
    deleted: "border-l-2 border-red-500 opacity-60",
  };
  return classMap[props.block.operation || "reference"];
});

const fileIconClass = computed(() => {
  if (props.block.type !== "file") return "text-muted-foreground";
  const classMap: Record<FileOperation, string> = {
    reference: "text-muted-foreground",
    created: "text-green-500",
    modified: "text-blue-500",
    deleted: "text-red-500",
  };
  return classMap[props.block.operation || "reference"];
});

// 方法
function renderMarkdown(content: string): string {
  // 简单的 Markdown 转换
  return content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>")
    .replace(/\n/g, "<br>");
}

function getOperationIcon(operation?: CodeOperation) {
  const iconMap: Record<CodeOperation, any> = {
    view: Eye,
    create: FilePlus,
    update: FileEdit,
    delete: Trash2,
    diff: Code,
  };
  return iconMap[operation || "view"];
}

function getOperationLabel(operation?: CodeOperation): string {
  const labelMap: Record<CodeOperation, string> = {
    view: t("chat.codeOp.view"),
    create: t("chat.codeOp.create"),
    update: t("chat.codeOp.update"),
    delete: t("chat.codeOp.delete"),
    diff: t("chat.codeOp.diff"),
  };
  return labelMap[operation || "view"];
}

function getFileOperationIcon(operation?: FileOperation) {
  const iconMap: Record<FileOperation, any> = {
    reference: File,
    created: FilePlus,
    modified: FileEdit,
    deleted: Trash2,
  };
  return iconMap[operation || "reference"];
}

function getThinkingPhaseLabel(phase?: ThinkingPhase): string {
  const labelMap: Record<ThinkingPhase, string> = {
    planning: t("chat.thinkingPhase.planning"),
    analyzing: t("chat.thinkingPhase.analyzing"),
    reflecting: t("chat.thinkingPhase.reflecting"),
  };
  return labelMap[phase || "analyzing"] || t("chat.thinking");
}

function formatJson(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function toggleThinking() {
  isThinkingCollapsed.value = !isThinkingCollapsed.value;
}

async function copyCommand() {
  if (props.block.type === "command") {
    await copyToClipboard(props.block.command);
    emit("copy", props.block.command);
  }
}

async function copyCode() {
  if (props.block.type === "code") {
    await copyToClipboard(props.block.code);
    emit("copy", props.block.code);
  }
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    console.error("Copy failed:", e);
  }
}

function runCommand() {
  if (props.block.type === "command") {
    emit("run-command", props.block.command, props.block.cwd);
  }
}
</script>

<style scoped>
.content-block {
  @apply mb-3;
}

/* 命令块样式 */
.command-block {
  @apply bg-gray-900 dark:bg-gray-950 rounded-lg overflow-hidden;
}

.command-block.is-dangerous {
  @apply ring-1 ring-red-500/50;
}

.command-header {
  @apply flex items-center justify-between px-3 py-2 bg-gray-800 dark:bg-gray-900 border-b border-gray-700;
}

.command-content {
  @apply px-3 py-2 text-green-400;
}

.command-explanation {
  @apply px-3 py-1.5 bg-gray-800/50 border-t border-gray-700;
}

.command-warning {
  @apply flex items-center gap-1.5 px-3 py-1.5 bg-red-900/20 border-t border-red-500/30;
}

/* 代码块样式 */
.code-block {
  @apply bg-muted rounded-lg overflow-hidden border border-border;
}

.code-header {
  @apply flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border;
}

.code-content {
  @apply overflow-x-auto;
}

.code-content pre {
  @apply p-3 m-0;
}

.code-lines {
  @apply px-3 py-1.5 bg-muted/30 border-t border-border;
}

/* 图表块样式 */
.chart-block {
  @apply bg-muted/30 rounded-lg overflow-hidden border border-border;
}

.chart-header {
  @apply flex items-center gap-2 px-3 py-2 border-b border-border;
}

.chart-content {
  @apply p-3;
}

.mermaid-container {
  @apply flex justify-center;
}

/* 表格块样式 */
.table-block {
  @apply bg-muted/30 rounded-lg overflow-hidden border border-border;
}

.table-header {
  @apply flex items-center gap-2 px-3 py-2 border-b border-border;
}

.table-content table {
  @apply border-collapse;
}

.table-caption {
  @apply px-3 py-1.5 bg-muted/50 border-t border-border;
}

/* 文件块样式 */
.file-block {
  @apply flex items-center justify-between px-3 py-2 bg-muted/30 rounded-lg border border-border;
}

/* 思考块样式 */
.thinking-block {
  @apply bg-purple-50 dark:bg-purple-900/10 rounded-lg overflow-hidden border border-purple-200 dark:border-purple-800/30;
}

.thinking-header {
  @apply flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-purple-100 dark:hover:bg-purple-900/20 transition-colors;
}

.thinking-content {
  @apply px-3 py-2 border-t border-purple-200 dark:border-purple-800/30;
}

/* 错误块样式 */
.error-block {
  @apply bg-red-50 dark:bg-red-900/10 rounded-lg overflow-hidden border border-red-200 dark:border-red-800/30;
}

.error-header {
  @apply flex items-center gap-2 px-3 py-2 bg-red-100/50 dark:bg-red-900/20;
}

.error-message {
  @apply px-3 py-2;
}

.error-traceback {
  @apply px-3 py-2 bg-red-100/30 dark:bg-red-900/10 border-t border-red-200 dark:border-red-800/30;
}

.error-suggestion {
  @apply flex items-center gap-1.5 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/10 border-t border-red-200 dark:border-red-800/30;
}

/* 展开动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
