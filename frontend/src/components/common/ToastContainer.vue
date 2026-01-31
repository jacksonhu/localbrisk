<!-- Toast 通知组件 -->
<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast"
      tag="div"
      class="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2"
    >
      <div
        v-for="toast in toastMessages"
        :key="toast.id"
        class="flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg border max-w-sm"
        :class="toastClasses[toast.type]"
      >
        <component :is="toastIcons[toast.type]" class="w-5 h-5 flex-shrink-0" />
        <span class="text-sm">{{ toast.message }}</span>
        <button
          @click="removeToast(toast.id)"
          class="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors ml-auto"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next';
import { useToast, type ToastType } from '@/composables/useToast';

const { toastMessages, removeToast } = useToast();

// Toast 样式配置
const toastClasses: Record<ToastType, string> = {
  success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200',
  error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200',
  warning: 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200',
  info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200',
};

// Toast 图标配置
const toastIcons: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};
</script>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease;
}

.toast-leave-active {
  transition: all 0.2s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
