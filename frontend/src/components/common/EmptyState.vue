<!-- 
  EmptyState - 空状态组件
  统一空数据的展示样式
  
  使用方式：
  <EmptyState 
    :icon="FolderOpen" 
    :message="t('common.noData')"
  >
    <template #action>
      <button @click="create">创建</button>
    </template>
  </EmptyState>
-->
<template>
  <div class="flex flex-col items-center justify-center text-center" :class="containerClass">
    <!-- 图标 -->
    <div class="mb-3" :class="iconContainerClass">
      <component :is="icon" v-if="icon" class="text-muted-foreground/50" :class="iconClass" />
      <slot v-else name="icon">
        <Inbox class="text-muted-foreground/50" :class="iconClass" />
      </slot>
    </div>
    
    <!-- 主消息 -->
    <p class="text-muted-foreground mb-1" :class="messageClass">
      {{ message }}
    </p>
    
    <!-- 副标题/描述 -->
    <p v-if="description" class="text-muted-foreground/70 text-xs mb-4 max-w-xs">
      {{ description }}
    </p>
    
    <!-- 操作按钮插槽 -->
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import { Inbox } from 'lucide-vue-next';

interface Props {
  /** 图标组件 */
  icon?: Component;
  /** 主消息 */
  message: string;
  /** 描述文本 */
  description?: string;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 是否占满容器高度 */
  fullHeight?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  icon: undefined,
  description: '',
  size: 'md',
  fullHeight: false,
});

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

const iconContainerClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'p-2',
    md: 'p-3',
    lg: 'p-4',
  };
  return sizeMap[props.size] || sizeMap.md;
});

const iconClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };
  return sizeMap[props.size] || sizeMap.md;
});

const messageClass = computed(() => {
  const sizeMap: Record<string, string> = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };
  return sizeMap[props.size] || sizeMap.md;
});
</script>
