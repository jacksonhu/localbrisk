<template>
  <div class="task-list-panel">
    <!-- 任务列表头部 -->
    <div 
      class="task-header flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-muted/50 transition-colors"
      @click="toggleExpanded"
    >
      <div class="flex items-center gap-2">
        <ListChecks class="w-4 h-4 text-primary" />
        <span class="text-sm font-medium">
          {{ t('chat.taskList.title', { completed: completedCount, total: tasks.length }) }}
        </span>
        <span v-if="isAllCompleted" class="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
          {{ t('chat.taskList.allCompleted') }}
        </span>
        <span v-else-if="hasRunningTask" class="text-xs px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 flex items-center gap-1">
          <Loader2 class="w-3 h-3 animate-spin" />
          {{ t('chat.taskList.inProgress') }}
        </span>
      </div>
      <ChevronDown 
        class="w-4 h-4 text-muted-foreground transition-transform duration-200"
        :class="{ 'rotate-180': !isExpanded }"
      />
    </div>

    <!-- 任务列表内容 -->
    <Transition name="expand">
      <div v-if="isExpanded" class="task-content px-3 pb-3">
        <!-- 进度条 -->
        <div class="progress-bar h-1.5 bg-muted rounded-full overflow-hidden mb-3">
          <div 
            class="h-full bg-primary transition-all duration-300"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>

        <!-- 任务项列表 -->
        <div class="task-items space-y-1.5">
          <div 
            v-for="(task, index) in tasks" 
            :key="task.id || index"
            class="task-item flex items-start gap-2 py-1.5 px-2 rounded-lg transition-colors"
            :class="{
              'bg-blue-50 dark:bg-blue-900/20': task.status === 'running',
              'opacity-60': task.status === 'completed',
            }"
          >
            <!-- 状态图标 -->
            <div class="flex-shrink-0 mt-0.5">
              <CheckCircle2 
                v-if="task.status === 'completed'" 
                class="w-4 h-4 text-green-500"
              />
              <Loader2 
                v-else-if="task.status === 'running'" 
                class="w-4 h-4 text-blue-500 animate-spin"
              />
              <Circle 
                v-else-if="task.status === 'pending'" 
                class="w-4 h-4 text-muted-foreground"
              />
              <XCircle 
                v-else-if="task.status === 'failed'" 
                class="w-4 h-4 text-red-500"
              />
              <AlertCircle 
                v-else 
                class="w-4 h-4 text-yellow-500"
              />
            </div>

            <!-- 任务内容 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span 
                  class="text-sm"
                  :class="{
                    'line-through text-muted-foreground': task.status === 'completed',
                    'font-medium': task.status === 'running',
                  }"
                >
                  {{ index + 1 }}. {{ task.content || task.title }}
                </span>
              </div>
              <p v-if="task.description" class="text-xs text-muted-foreground mt-0.5 truncate">
                {{ task.description }}
              </p>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="tasks.length === 0" class="text-center py-4">
          <p class="text-sm text-muted-foreground">{{ t('chat.taskList.empty') }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ListChecks, ChevronDown, CheckCircle2, Circle, 
  XCircle, AlertCircle, Loader2 
} from "lucide-vue-next";

const { t } = useI18n();

// Props
export interface Task {
  id: string;
  content?: string;
  title?: string;
  description?: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
}

const props = withDefaults(defineProps<{
  tasks: Task[];
  defaultExpanded?: boolean;
}>(), {
  defaultExpanded: true,
});

// State
const isExpanded = ref(props.defaultExpanded);

// Computed
const completedCount = computed(() => 
  props.tasks.filter(t => t.status === "completed").length
);

const progressPercent = computed(() => {
  if (props.tasks.length === 0) return 0;
  return Math.round((completedCount.value / props.tasks.length) * 100);
});

const isAllCompleted = computed(() => 
  props.tasks.length > 0 && completedCount.value === props.tasks.length
);

const hasRunningTask = computed(() => 
  props.tasks.some(t => t.status === "running")
);

// Methods
function toggleExpanded() {
  isExpanded.value = !isExpanded.value;
}
</script>

<style scoped>
.task-list-panel {
  @apply bg-muted/30 rounded-xl border border-border/50 overflow-hidden;
}

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
