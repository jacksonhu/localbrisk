<!-- 
  ErrorState - 错误状态组件
  统一错误信息的展示样式
  
  使用方式：
  <ErrorState 
    :error="error"
    @retry="fetchData"
  />
-->
<template>
  <div class="flex flex-col items-center justify-center text-center" :class="containerClass">
    <!-- 图标 -->
    <div class="mb-3 p-3 rounded-full bg-red-500/10">
      <AlertCircle class="text-red-500" :class="iconClass" />
    </div>
    
    <!-- 标题 -->
    <p class="text-foreground font-medium mb-1" :class="titleClass">
      {{ title || t('common.error') }}
    </p>
    
    <!-- 错误详情 -->
    <p class="text-muted-foreground text-sm mb-4 max-w-md">
      {{ error }}
    </p>
    
    <!-- 重试按钮 -->
    <button
      v-if="showRetry"
      type="button"
      class="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2"
      @click="$emit('retry')"
    >
      <RefreshCw class="w-4 h-4" />
      {{ retryText || t('common.retry') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AlertCircle, RefreshCw } from 'lucide-vue-next';

const { t } = useI18n();

interface Props {
  /** 错误信息 */
  error: string;
  /** 标题 */
  title?: string;
  /** 重试按钮文本 */
  retryText?: string;
  /** 是否显示重试按钮 */
  showRetry?: boolean;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 是否占满容器高度 */
  fullHeight?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  retryText: '',
  showRetry: true,
  size: 'md',
  fullHeight: false,
});

defineEmits<{
  (e: 'retry'): void;
}>();

const containerClass = computed(() => {
  const classes: string[] = [];
  if (props.fullHeight) {
    classes.push('h-full min-h-[200px]');
  } else {
    const paddingMap: Record<string, string> = {
      sm: 'py-6',
      md: 'py-10',
      lg: 'py-16',
    };
    classes.push(paddingMap[props.size] || paddingMap.md);
  }
  return classes.join(' ');
});

const iconClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };
  return sizeMap[props.size] || sizeMap.md;
});

const titleClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
  };
  return sizeMap[props.size] || sizeMap.md;
});
</script>
