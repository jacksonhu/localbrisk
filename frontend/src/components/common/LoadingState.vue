<!-- 
  LoadingState - 加载状态组件
  统一加载中的展示样式
  
  使用方式：
  <LoadingState :text="t('common.loading')" />
  <LoadingState size="lg" />
-->
<template>
  <div class="flex items-center justify-center" :class="containerClass">
    <div class="flex flex-col items-center gap-3">
      <Loader2 class="animate-spin text-primary" :class="iconClass" />
      <span v-if="text" class="text-muted-foreground" :class="textClass">
        {{ text }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Loader2 } from 'lucide-vue-next';

interface Props {
  /** 加载文本 */
  text?: string;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 是否占满容器高度 */
  fullHeight?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  size: 'md',
  fullHeight: false,
});

const containerClass = computed(() => {
  const classes: string[] = [];
  if (props.fullHeight) {
    classes.push('h-full min-h-[200px]');
  } else {
    const paddingMap: Record<string, string> = {
      sm: 'py-4',
      md: 'py-8',
      lg: 'py-12',
    };
    classes.push(paddingMap[props.size] || paddingMap.md);
  }
  return classes.join(' ');
});

const iconClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };
  return sizeMap[props.size] || sizeMap.md;
});

const textClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };
  return sizeMap[props.size] || sizeMap.md;
});
</script>
