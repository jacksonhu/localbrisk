<template>
  <div class="agent-execution-block">
    <!-- Thinking process panel (collapsible) -->
    <div v-if="hasThinkingContent" class="thinking-panel">
      <!-- Collapse/Expand header -->
      <div
        class="flex items-center gap-2 px-3 py-2 cursor-pointer select-none rounded-lg hover:bg-muted/40 transition-colors"
        @click="toggleThinking"
      >
        <ChevronRight
          class="w-4 h-4 text-muted-foreground transition-transform duration-200"
          :class="{ 'rotate-90': isExpanded }"
        />
        <span class="text-sm font-medium text-foreground/80">Thinking process</span>
        <Loader2 v-if="data.isExecuting" class="w-3.5 h-3.5 animate-spin text-primary ml-1" />
        <CheckCircle2 v-else-if="!data.errorText" class="w-3.5 h-3.5 text-green-500 ml-1" />
        <AlertCircle v-else class="w-3.5 h-3.5 text-red-500 ml-1" />
      </div>

      <!-- Collapsible content -->
      <Transition name="expand">
        <div v-if="isExpanded" class="thinking-content pl-4 pr-2 pb-3">
          <!-- Thought text (streaming reasoning) -->
          <div
            v-if="data.thoughtText"
            class="thought-text text-sm leading-relaxed text-muted-foreground mb-3 markdown-body"
            v-html="renderedThought"
          ></div>

          <!-- Unified step flow -->
          <div v-if="data.steps.length > 0" class="step-flow space-y-1">
            <div
              v-for="step in data.steps"
              :key="step.id"
              class="step-entry flex items-start gap-2.5 py-1.5 px-2 rounded-lg transition-colors"
              :class="stepRowClass(step)"
            >
              <!-- Status icon -->
              <div class="shrink-0 mt-0.5">
                <CheckCircle2 v-if="step.status === 'completed'" class="w-4 h-4 text-green-500" />
                <Loader2 v-else-if="step.status === 'running'" class="w-4 h-4 text-primary animate-spin" />
                <Circle v-else-if="step.status === 'pending'" class="w-4 h-4 text-muted-foreground/40" />
                <XCircle v-else class="w-4 h-4 text-red-500" />
              </div>

              <!-- Step content -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span
                    class="text-xs font-semibold px-1.5 py-0.5 rounded"
                    :class="stepLabelClass(step)"
                  >{{ step.label }}</span>
                  <span
                    class="text-sm font-medium truncate"
                    :class="{ 'text-foreground': step.status === 'running', 'text-foreground/80': step.status !== 'running' }"
                  >{{ step.title }}</span>
                </div>
                <p v-if="step.description" class="text-xs text-muted-foreground mt-0.5 leading-5 break-all">
                  {{ step.description }}
                </p>
                <!-- Tool result (truncated, expandable) -->
                <div v-if="step.toolResult" class="mt-1">
                  <pre class="text-xs font-mono text-muted-foreground bg-muted/40 rounded px-2 py-1.5 overflow-x-auto max-h-24 overflow-y-auto whitespace-pre-wrap break-all">{{ truncateResult(step.toolResult) }}</pre>
                </div>
                <p v-if="step.reflection" class="text-xs text-muted-foreground mt-1 italic">{{ step.reflection }}</p>
              </div>
            </div>
          </div>

          <!-- Typing cursor for active streaming -->
          <span v-if="data.isThinking" class="typing-cursor"></span>

          <!-- Error detail inside thinking panel -->
          <div v-if="data.errorText" class="mt-3 rounded-lg bg-red-50/80 dark:bg-red-900/10 px-3 py-2 border border-red-200/60 dark:border-red-800/30">
            <div class="flex items-center gap-1.5 mb-0.5">
              <AlertCircle class="w-3.5 h-3.5 text-red-500" />
              <span class="text-xs font-medium text-red-600 dark:text-red-400">{{ data.errorDetail?.type || 'Error' }}</span>
            </div>
            <p class="text-xs text-red-600 dark:text-red-300 leading-5">{{ data.errorText }}</p>
            <p v-if="data.errorDetail?.suggestion" class="text-xs text-muted-foreground mt-1">
              {{ data.errorDetail.suggestion }}
            </p>
            <button
              v-if="data.errorDetail?.retryable"
              class="mt-1.5 text-xs px-2.5 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
              @click="$emit('retry')"
            >Retry</button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Final result output (always visible when present) -->
    <div v-if="data.finalContent" class="final-result px-3 py-3">
      <div class="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed markdown-body" v-html="renderedFinal"></div>
    </div>

    <!-- Done summary -->
    <div v-if="data.doneSummary" class="done-section mx-3 mb-3 p-3 bg-green-50/80 dark:bg-green-900/10 rounded-lg border border-green-200/60 dark:border-green-800/30">
      <div class="flex items-center gap-2 mb-1">
        <CheckCircle2 class="w-4 h-4 text-green-500" />
        <span class="text-sm font-medium text-green-700 dark:text-green-400">Completed</span>
      </div>
      <p class="text-sm text-green-600 dark:text-green-300">{{ data.doneSummary }}</p>
      <div v-if="data.doneNextSteps?.length" class="mt-2 space-y-1">
        <p class="text-xs font-medium text-muted-foreground">Suggested next steps:</p>
        <div v-for="(step, idx) in data.doneNextSteps" :key="idx" class="text-xs flex items-start gap-1.5">
          <span class="text-primary mt-0.5">→</span><span>{{ step }}</span>
        </div>
      </div>
    </div>

    <!-- Loading placeholder (no content yet) -->
    <div v-if="data.isExecuting && !data.thoughtText && data.steps.length === 0 && !data.finalContent" class="flex items-center gap-2 px-3 py-3">
      <Loader2 class="w-4 h-4 animate-spin text-primary" />
      <span class="text-sm text-muted-foreground">Thinking...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Circle,
  Loader2,
  XCircle,
} from "lucide-vue-next";
import { useMarkdownRenderer } from "@/composables/useMarkdownRenderer";
import type { ExecutionBlockData, ExecutionStep } from "@/types/execution-block";

const props = defineProps<{
  data: ExecutionBlockData;
  /** Whether the thinking panel starts expanded (default: true). */
  defaultExpanded?: boolean;
}>();

defineEmits<{
  (e: "retry"): void;
}>();

// ---- Expand/collapse state ----

const isExpanded = ref(props.defaultExpanded !== false);

function toggleThinking(): void {
  isExpanded.value = !isExpanded.value;
}

// ---- Markdown rendering ----

const { renderMarkdown } = useMarkdownRenderer();

const renderedThought = computed(() => renderMarkdown(props.data.thoughtText || ""));
const renderedFinal = computed(() => renderMarkdown(props.data.finalContent || ""));

// ---- Computed: has any thinking content to show ----

const hasThinkingContent = computed(() => {
  return Boolean(
    props.data.isExecuting ||
    props.data.thoughtText ||
    props.data.steps.length > 0 ||
    props.data.errorText,
  );
});

// ---- Step rendering helpers ----

function stepRowClass(step: ExecutionStep): string {
  if (step.status === "running") return "bg-blue-50/50 dark:bg-blue-900/10";
  if (step.status === "failed") return "bg-red-50/30 dark:bg-red-900/5";
  return "";
}

function stepLabelClass(step: ExecutionStep): Record<string, boolean> {
  return {
    "bg-primary/10 text-primary": step.category === "tool_call",
    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400": step.category === "skill",
    "bg-muted text-muted-foreground": step.category === "status",
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400": step.category === "task",
  };
}

function truncateResult(result: string): string {
  return result.length > 300 ? result.slice(0, 300) + "..." : result;
}
</script>

<style scoped>
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
  max-height: 5000px;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: currentColor;
  margin-left: 2px;
  animation: blink 1s step-end infinite;
  vertical-align: text-bottom;
}
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Markdown body styles */
.markdown-body :deep(h1) { @apply text-xl font-bold mb-3 mt-4 first:mt-0; }
.markdown-body :deep(h2) { @apply text-lg font-bold mb-2 mt-3 first:mt-0; }
.markdown-body :deep(h3) { @apply text-base font-semibold mb-2 mt-2 first:mt-0; }
.markdown-body :deep(p) { @apply mb-2 last:mb-0; }
.markdown-body :deep(ul) { @apply my-2 pl-5 list-disc; }
.markdown-body :deep(ol) { @apply my-2 pl-5 list-decimal; }
.markdown-body :deep(li) { @apply mb-1; }
.markdown-body :deep(table) { @apply w-full border-collapse my-3 text-sm; }
.markdown-body :deep(th) { @apply px-3 py-2 bg-muted/60 text-left font-semibold border border-border/50; }
.markdown-body :deep(td) { @apply px-3 py-2 border border-border/50; }
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
.markdown-body :deep(code) { @apply px-1 py-0.5 bg-muted rounded text-xs font-mono; }
.markdown-body :deep(pre code) { @apply bg-transparent p-0; }
.markdown-body :deep(blockquote) { @apply border-l-2 border-border pl-3 italic text-muted-foreground; }
</style>
