<!-- 
  StateContainer - 状态容器组件
  根据 loading/error/empty 状态自动渲染对应的 UI
  
  使用方式：
  <StateContainer
    :loading="loading"
    :error="error"
    :empty="items.length === 0"
    :empty-message="t('common.noData')"
    @retry="fetchData"
  >
    <ItemList :items="items" />
  </StateContainer>
-->
<template>
  <div class="state-container" :class="{ 'h-full': fullHeight }">
    <!-- 加载状态 -->
    <LoadingState
      v-if="loading"
      :text="loadingText"
      :size="size"
      :full-height="fullHeight"
    />
    
    <!-- 错误状态 -->
    <ErrorState
      v-else-if="error"
      :error="error"
      :title="errorTitle"
      :retry-text="retryText"
      :show-retry="showRetry"
      :size="size"
      :full-height="fullHeight"
      @retry="$emit('retry')"
    />
    
    <!-- 空状态 -->
    <EmptyState
      v-else-if="empty"
      :icon="emptyIcon"
      :message="emptyMessage"
      :description="emptyDescription"
      :size="size"
      :full-height="fullHeight"
    >
      <template v-if="$slots.empty" #action>
        <slot name="empty" />
      </template>
    </EmptyState>
    
    <!-- 正常内容 -->
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue';
import LoadingState from './LoadingState.vue';
import EmptyState from './EmptyState.vue';
import ErrorState from './ErrorState.vue';

interface Props {
  /** 是否加载中 */
  loading?: boolean;
  /** 加载文本 */
  loadingText?: string;
  /** 错误信息 */
  error?: string | null;
  /** 错误标题 */
  errorTitle?: string;
  /** 重试按钮文本 */
  retryText?: string;
  /** 是否显示重试按钮 */
  showRetry?: boolean;
  /** 是否为空 */
  empty?: boolean;
  /** 空状态图标 */
  emptyIcon?: Component;
  /** 空状态消息 */
  emptyMessage?: string;
  /** 空状态描述 */
  emptyDescription?: string;
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 是否占满容器高度 */
  fullHeight?: boolean;
}

withDefaults(defineProps<Props>(), {
  loading: false,
  loadingText: '',
  error: null,
  errorTitle: '',
  retryText: '',
  showRetry: true,
  empty: false,
  emptyIcon: undefined,
  emptyMessage: '',
  emptyDescription: '',
  size: 'md',
  fullHeight: false,
});

defineEmits<{
  (e: 'retry'): void;
}>();
</script>
