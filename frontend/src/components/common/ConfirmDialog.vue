<!-- 
  ConfirmDialog - 确认弹窗组件
  用于删除等危险操作的确认
  
  使用方式：
  <ConfirmDialog
    :is-open="showConfirm"
    :message="t('confirm.deleteMessage', { name: item.name })"
    description="删除后无法恢复"
    @close="showConfirm = false"
    @confirm="handleDelete"
  />
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="title || t('confirm.deleteTitle')"
    width="sm"
    @close="close"
  >
    <!-- 自定义标题栏 -->
    <template #header>
      <div class="flex items-center gap-3">
        <div 
          class="w-10 h-10 rounded-full flex items-center justify-center"
          :class="variant === 'danger' 
            ? 'bg-red-100 dark:bg-red-900/30' 
            : 'bg-amber-100 dark:bg-amber-900/30'"
        >
          <AlertTriangle 
            class="w-5 h-5" 
            :class="variant === 'danger' 
              ? 'text-red-600 dark:text-red-400' 
              : 'text-amber-600 dark:text-amber-400'" 
          />
        </div>
        <h2 class="text-lg font-semibold text-foreground">
          {{ title || t('confirm.deleteTitle') }}
        </h2>
      </div>
    </template>
    
    <!-- 内容 -->
    <div class="space-y-3">
      <p class="text-foreground">{{ message }}</p>
      <p v-if="description" class="text-sm text-muted-foreground">{{ description }}</p>
    </div>
    
    <!-- 底部按钮 -->
    <template #footer>
      <DialogFooter
        :submitting="isLoading"
        :submit-text="confirmText || t('common.delete')"
        :variant="variant"
        @cancel="close"
        @submit="handleConfirm"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { AlertTriangle } from 'lucide-vue-next';
import BaseDialog from './BaseDialog.vue';
import DialogFooter from './DialogFooter.vue';

const { t } = useI18n();

// Props
interface Props {
  isOpen: boolean;
  message: string;
  description?: string;
  title?: string;
  confirmText?: string;
  variant?: 'danger' | 'warning';
}

withDefaults(defineProps<Props>(), {
  description: '',
  title: '',
  confirmText: '',
  variant: 'danger',
});

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

// 确认
function handleConfirm() {
  emit('confirm');
}
</script>
