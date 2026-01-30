<!-- 
  DialogFooter - 弹窗底部按钮组件
  统一弹窗的确认/取消按钮样式和行为
  
  使用方式：
  <DialogFooter
    :submitting="isSubmitting"
    :disabled="!isValid"
    submit-text="创建"
    @cancel="close"
    @submit="handleSubmit"
  />
-->
<template>
  <div class="flex items-center gap-3" :class="{ 'justify-end': !$slots.left, 'justify-between': $slots.left }">
    <!-- 左侧自定义内容 -->
    <div v-if="$slots.left">
      <slot name="left" />
    </div>
    
    <!-- 右侧按钮组 -->
    <div class="flex items-center gap-3">
      <!-- 取消按钮 -->
      <button
        v-if="showCancel"
        type="button"
        class="px-4 py-2 text-sm font-medium border border-input rounded-lg text-foreground hover:bg-muted transition-colors"
        :disabled="submitting"
        @click="$emit('cancel')"
      >
        {{ cancelText || t('common.cancel') }}
      </button>
      
      <!-- 提交按钮 -->
      <button
        v-if="showSubmit"
        type="button"
        class="px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
        :class="submitButtonClass"
        :disabled="submitting || disabled"
        @click="$emit('submit')"
      >
        <Loader2 v-if="submitting" class="w-4 h-4 animate-spin" />
        <component :is="submitIcon" v-else-if="submitIcon" class="w-4 h-4" />
        {{ submitText || t('common.confirm') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import { useI18n } from 'vue-i18n';
import { Loader2 } from 'lucide-vue-next';

const { t } = useI18n();

interface Props {
  /** 是否正在提交 */
  submitting?: boolean;
  /** 是否禁用提交按钮 */
  disabled?: boolean;
  /** 取消按钮文本 */
  cancelText?: string;
  /** 提交按钮文本 */
  submitText?: string;
  /** 提交按钮图标 */
  submitIcon?: Component;
  /** 是否显示取消按钮 */
  showCancel?: boolean;
  /** 是否显示提交按钮 */
  showSubmit?: boolean;
  /** 提交按钮变体：primary | danger */
  variant?: 'primary' | 'danger';
}

const props = withDefaults(defineProps<Props>(), {
  submitting: false,
  disabled: false,
  cancelText: '',
  submitText: '',
  submitIcon: undefined,
  showCancel: true,
  showSubmit: true,
  variant: 'primary',
});

defineEmits<{
  (e: 'cancel'): void;
  (e: 'submit'): void;
}>();

// 提交按钮样式
const submitButtonClass = computed(() => {
  const base = 'disabled:opacity-50 disabled:cursor-not-allowed';
  
  if (props.variant === 'danger') {
    return `${base} bg-red-500 text-white hover:bg-red-600`;
  }
  
  return `${base} bg-primary text-primary-foreground hover:bg-primary/90`;
});
</script>
