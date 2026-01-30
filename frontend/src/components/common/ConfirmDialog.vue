<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[400px] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center gap-3 px-6 py-4 border-b border-border">
            <div class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
              <AlertTriangle class="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <h2 class="text-lg font-semibold text-foreground">
              {{ t('confirm.deleteTitle') }}
            </h2>
          </div>
          
          <!-- 内容 -->
          <div class="p-6 space-y-4">
            <p class="text-foreground">{{ message }}</p>
            <p v-if="description" class="text-sm text-muted-foreground">{{ description }}</p>
          </div>
          
          <!-- 底部按钮 -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
            <button
              type="button"
              @click="close"
              class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="handleConfirm"
              :disabled="isLoading"
              class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
              {{ t('common.delete') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AlertTriangle, Loader2 } from 'lucide-vue-next';

const { t } = useI18n();

// Props
defineProps<{
  isOpen: boolean;
  message: string;
  description?: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm'): void;
}>();

// 加载状态
const isLoading = ref(false);

// 关闭弹窗
function close() {
  emit('close');
}

// 确认删除
function handleConfirm() {
  emit('confirm');
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
