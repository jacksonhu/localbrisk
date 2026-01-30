<!-- 
  Breadcrumb - 面包屑导航组件
  统一详情页的面包屑导航样式
  
  使用方式：
  <Breadcrumb
    :items="[
      { id: 'catalog1', label: 'Catalog', onClick: () => ... },
      { id: 'schema1', label: 'Schema' },
    ]"
    show-back
    @back="goBack"
  />
-->
<template>
  <nav class="flex items-center gap-2 text-sm" aria-label="Breadcrumb">
    <!-- 返回按钮 -->
    <button
      v-if="showBack"
      type="button"
      class="p-1 -ml-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
      :aria-label="t('common.back')"
      @click="$emit('back')"
    >
      <ArrowLeft class="w-4 h-4" />
    </button>
    
    <!-- 面包屑项 -->
    <ol class="flex items-center gap-1">
      <li
        v-for="(item, index) in items"
        :key="item.id"
        class="flex items-center gap-1"
      >
        <!-- 分隔符 -->
        <ChevronRight
          v-if="index > 0"
          class="w-3 h-3 text-muted-foreground/50"
        />
        
        <!-- 面包屑项内容 -->
        <component
          :is="isClickable(item, index) ? 'button' : 'span'"
          :type="isClickable(item, index) ? 'button' : undefined"
          :class="[
            'flex items-center gap-1.5 px-1 rounded transition-colors',
            isClickable(item, index)
              ? 'text-primary hover:text-primary/80 hover:underline cursor-pointer'
              : 'text-foreground',
          ]"
          @click="isClickable(item, index) && handleClick(item)"
        >
          <!-- 图标 -->
          <component
            v-if="item.icon"
            :is="item.icon"
            class="w-3.5 h-3.5"
          />
          <!-- 文本 -->
          <span :class="{ 'max-w-[150px] truncate': truncate }">
            {{ item.label }}
          </span>
        </component>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ArrowLeft, ChevronRight } from 'lucide-vue-next';
import type { Component } from 'vue';

const { t } = useI18n();

export interface BreadcrumbItem {
  /** 唯一标识 */
  id: string;
  /** 显示文本 */
  label: string;
  /** 图标 */
  icon?: Component;
  /** 点击回调 */
  onClick?: () => void;
}

interface Props {
  /** 面包屑项列表 */
  items: BreadcrumbItem[];
  /** 是否显示返回按钮 */
  showBack?: boolean;
  /** 是否截断过长文本 */
  truncate?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showBack: true,
  truncate: true,
});

const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'navigate', item: BreadcrumbItem): void;
}>();

/**
 * 判断项是否可点击
 * 最后一项不可点击，或者没有 onClick 的项不可点击
 */
function isClickable(item: BreadcrumbItem, index: number): boolean {
  // 最后一项不可点击
  if (index === props.items.length - 1) return false;
  // 有 onClick 的可点击
  return !!item.onClick;
}

function handleClick(item: BreadcrumbItem): void {
  if (item.onClick) {
    item.onClick();
  }
  emit('navigate', item);
}
</script>
