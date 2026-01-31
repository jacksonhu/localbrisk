<template>
  <div class="card-float overflow-hidden">
    <!-- 标题栏 -->
    <div class="p-4 border-b border-border flex items-center justify-between">
      <h3 class="font-medium flex items-center gap-2">
        <component :is="icon" class="w-4 h-4" />
        {{ title }}
      </h3>
      <span class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
        {{ items.length }} {{ itemsLabel }}
      </span>
    </div>
    
    <!-- 列表内容 -->
    <div v-if="items.length > 0" class="divide-y divide-border">
      <div
        v-for="item in items"
        :key="getItemKey(item)"
        @click="handleItemClick(item)"
        class="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors"
        :class="clickable ? 'cursor-pointer' : ''"
      >
        <!-- 图标 -->
        <component :is="itemIcon" class="w-4 h-4" :class="itemIconColor" />
        
        <!-- 名称 -->
        <span class="text-sm font-medium flex-1">{{ getItemName(item) }}</span>
        
        <!-- 启用开关 -->
        <label v-if="showToggle" class="relative inline-flex items-center cursor-pointer" @click.stop>
          <input
            type="checkbox"
            :checked="isItemEnabled(item)"
            @change="handleToggle(item)"
            class="sr-only peer"
          />
          <div class="w-9 h-5 bg-muted rounded-full peer-checked:bg-primary transition-colors"></div>
          <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
        </label>
        
        <!-- 箭头指示 -->
        <ChevronRight v-if="clickable" class="w-4 h-4 text-muted-foreground" />
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center py-8 text-center">
      <component :is="emptyIcon || icon" class="w-8 h-8 text-muted-foreground mb-2" />
      <p class="text-muted-foreground text-sm">{{ emptyText }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next';
import type { Component, FunctionalComponent } from 'vue';

// 类型定义
type IconType = Component | FunctionalComponent;

// Props
const props = withDefaults(defineProps<{
  /** 标题 */
  title: string;
  /** 标题图标 */
  icon: IconType;
  /** 列表项图标 */
  itemIcon: IconType;
  /** 列表项图标颜色 */
  itemIconColor?: string;
  /** 列表项数据 */
  items: (string | Record<string, unknown>)[];
  /** 数量标签文字 */
  itemsLabel?: string;
  /** 空状态文字 */
  emptyText: string;
  /** 空状态图标（可选，默认使用 icon） */
  emptyIcon?: IconType;
  /** 是否可点击 */
  clickable?: boolean;
  /** 是否显示启用开关 */
  showToggle?: boolean;
  /** 获取项名称的键（当 items 为对象数组时） */
  nameKey?: string;
  /** 检查项是否启用的函数 */
  isEnabled?: (item: string | Record<string, unknown>) => boolean;
}>(), {
  itemIconColor: 'text-primary',
  itemsLabel: 'items',
  clickable: true,
  showToggle: false,
  nameKey: 'name',
});

// Emits
const emit = defineEmits<{
  (e: 'item-click', item: string | Record<string, unknown>): void;
  (e: 'toggle', item: string | Record<string, unknown>, enabled: boolean): void;
}>();

// 获取项的唯一键
function getItemKey(item: string | Record<string, unknown>): string {
  if (typeof item === 'string') {
    return item;
  }
  return String(item[props.nameKey] || item.id || JSON.stringify(item));
}

// 获取项的名称
function getItemName(item: string | Record<string, unknown>): string {
  if (typeof item === 'string') {
    return item;
  }
  return String(item[props.nameKey] || '');
}

// 检查项是否启用
function isItemEnabled(item: string | Record<string, unknown>): boolean {
  if (props.isEnabled) {
    return props.isEnabled(item);
  }
  return false;
}

// 处理点击
function handleItemClick(item: string | Record<string, unknown>) {
  if (props.clickable) {
    emit('item-click', item);
  }
}

// 处理开关切换
function handleToggle(item: string | Record<string, unknown>) {
  const currentEnabled = isItemEnabled(item);
  emit('toggle', item, !currentEnabled);
}
</script>
