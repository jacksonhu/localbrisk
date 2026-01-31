<template>
  <div class="card-float overflow-hidden">
    <!-- 标题栏（可选） -->
    <div v-if="title || $slots.header" class="p-4 border-b border-border flex items-center justify-between">
      <slot name="header">
        <h3 class="font-medium flex items-center gap-2">
          <component v-if="titleIcon" :is="titleIcon" class="w-4 h-4" />
          {{ title }}
        </h3>
      </slot>
      <slot name="header-right">
        <span v-if="showCount" class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
          {{ filteredItems.length }} {{ countLabel }}
        </span>
      </slot>
    </div>
    
    <!-- 搜索栏（可选） -->
    <div v-if="searchable" class="p-4 border-b border-border">
      <div class="relative">
        <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="searchPlaceholder"
          class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background"
        />
      </div>
    </div>
    
    <!-- 列表内容 -->
    <div v-if="filteredItems.length > 0" class="divide-y divide-border">
      <div
        v-for="(item, rowIndex) in filteredItems"
        :key="getItemKey(item, rowIndex)"
        @click="handleRowClick(item, rowIndex)"
        class="flex items-center gap-3 px-4 py-3 transition-colors"
        :class="getRowClass(item, rowIndex)"
      >
        <!-- 动态列渲染 -->
        <template v-for="(col, colIndex) in columns" :key="col.key || colIndex">
          <!-- 图标列 -->
          <component 
            v-if="col.type === 'icon'" 
            :is="resolveIcon(col, item)" 
            class="w-4 h-4 shrink-0"
            :class="resolveClass(col, item)"
          />
          
          <!-- 文本列 -->
          <span 
            v-else-if="col.type === 'text'" 
            class="text-sm truncate"
            :class="[col.flex ? 'flex-1' : '', resolveClass(col, item)]"
            :title="resolveValue(col, item)"
          >
            {{ resolveValue(col, item) }}
          </span>
          
          <!-- 标签/徽章列 -->
          <span 
            v-else-if="col.type === 'badge'" 
            class="text-xs px-2 py-0.5 rounded-full shrink-0"
            :class="resolveClass(col, item)"
          >
            {{ resolveValue(col, item) }}
          </span>
          
          <!-- 开关列 -->
          <label 
            v-else-if="col.type === 'toggle'" 
            class="relative inline-flex items-center cursor-pointer shrink-0" 
            @click.stop
          >
            <input
              type="checkbox"
              :checked="resolveToggleState(col, item)"
              @change="handleToggle(col, item, rowIndex)"
              class="sr-only peer"
            />
            <div class="w-9 h-5 bg-muted rounded-full peer-checked:bg-primary transition-colors"></div>
            <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow peer-checked:translate-x-4 transition-transform"></div>
          </label>
          
          <!-- 按钮列 -->
          <button
            v-else-if="col.type === 'button'"
            @click.stop="handleAction(col, item, rowIndex)"
            class="shrink-0"
            :class="resolveClass(col, item)"
          >
            <component v-if="resolveIcon(col, item)" :is="resolveIcon(col, item)" class="w-4 h-4" />
            <span v-if="resolveValue(col, item)">{{ resolveValue(col, item) }}</span>
          </button>
          
          <!-- 自定义插槽列 -->
          <div v-else-if="col.type === 'slot'" :class="resolveClass(col, item)">
            <slot :name="col.slot || col.key" :item="item" :column="col" :index="rowIndex" />
          </div>
        </template>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="flex flex-col items-center justify-center py-8 text-center">
      <slot name="empty">
        <component v-if="emptyIcon" :is="emptyIcon" class="w-8 h-8 text-muted-foreground mb-2" />
        <p class="text-muted-foreground text-sm">{{ emptyText }}</p>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Search } from 'lucide-vue-next';
import type { Component, FunctionalComponent } from 'vue';

// ============ 类型定义 ============

type IconType = Component | FunctionalComponent;
type ItemType = string | number | Record<string, unknown>;

/** 列配置 */
export interface ColumnConfig {
  /** 列唯一标识 */
  key: string;
  /** 列类型 */
  type: 'icon' | 'text' | 'badge' | 'toggle' | 'button' | 'slot';
  /** 数据字段（从 item 取值） */
  field?: string;
  /** 是否占据剩余空间（flex-1） */
  flex?: boolean;
  /** 静态图标 */
  icon?: IconType;
  /** 动态图标获取函数 */
  iconFn?: (item: ItemType) => IconType | undefined;
  /** 静态 CSS 类 */
  class?: string;
  /** 动态 CSS 类获取函数 */
  classFn?: (item: ItemType) => string;
  /** 静态值 */
  value?: string | number;
  /** 动态值获取函数 */
  valueFn?: (item: ItemType) => unknown;
  /** toggle 启用状态检查函数 */
  isEnabled?: (item: ItemType) => boolean;
  /** 插槽名称（type=slot 时） */
  slot?: string;
  /** 按钮动作标识（type=button 时） */
  action?: string;
  /** 是否参与搜索过滤 */
  searchable?: boolean;
}

// ============ Props ============

const props = withDefaults(defineProps<{
  /** 列表数据 */
  items: ItemType[];
  /** 列配置 */
  columns: ColumnConfig[];
  /** 标题（可选） */
  title?: string;
  /** 标题图标（可选） */
  titleIcon?: IconType;
  /** 是否显示数量（可选） */
  showCount?: boolean;
  /** 数量标签（可选） */
  countLabel?: string;
  /** 空状态文字 */
  emptyText?: string;
  /** 空状态图标（可选） */
  emptyIcon?: IconType;
  /** 唯一键字段名 */
  keyField?: string;
  /** 行点击是否可用 */
  rowClickable?: boolean;
  /** 行 CSS 类（静态） */
  rowClass?: string;
  /** 行 CSS 类获取函数（动态） */
  rowClassFn?: (item: ItemType, index: number) => string;
  /** 是否启用搜索 */
  searchable?: boolean;
  /** 搜索占位符 */
  searchPlaceholder?: string;
  /** 搜索字段列表（指定从哪些字段搜索） */
  searchFields?: string[];
  /** 自定义搜索过滤函数 */
  searchFilter?: (item: ItemType, query: string) => boolean;
}>(), {
  showCount: false,
  countLabel: 'items',
  emptyText: 'No items',
  keyField: 'id',
  rowClickable: false,
  rowClass: '',
  searchable: false,
  searchPlaceholder: 'Search...',
});

// ============ Emits ============

const emit = defineEmits<{
  /** 行点击事件 */
  (e: 'row-click', payload: { item: ItemType; index: number }): void;
  /** toggle 切换事件 */
  (e: 'toggle', payload: { column: ColumnConfig; item: ItemType; index: number; enabled: boolean }): void;
  /** 按钮动作事件 */
  (e: 'action', payload: { column: ColumnConfig; item: ItemType; index: number; action: string }): void;
}>();

// ============ 搜索状态 ============

const searchQuery = ref('');

/** 过滤后的列表 */
const filteredItems = computed(() => {
  if (!props.searchable || !searchQuery.value.trim()) {
    return props.items;
  }
  
  const query = searchQuery.value.toLowerCase().trim();
  
  return props.items.filter(item => {
    // 使用自定义过滤函数
    if (props.searchFilter) {
      return props.searchFilter(item, query);
    }
    
    // 基本类型直接匹配
    if (typeof item === 'string') {
      return item.toLowerCase().includes(query);
    }
    if (typeof item === 'number') {
      return String(item).includes(query);
    }
    
    // 对象类型：搜索指定字段或可搜索列
    const searchFields = props.searchFields || getSearchableFields();
    return searchFields.some(field => {
      const value = item[field];
      if (value === undefined || value === null) return false;
      return String(value).toLowerCase().includes(query);
    });
  });
});

/** 获取可搜索的字段列表 */
function getSearchableFields(): string[] {
  const fields: string[] = [];
  for (const col of props.columns) {
    if (col.searchable !== false && col.field) {
      fields.push(col.field);
    }
  }
  // 默认搜索 name 字段
  if (fields.length === 0) {
    fields.push('name');
  }
  return fields;
}

// ============ 工具函数 ============

/** 获取行的唯一键 */
function getItemKey(item: ItemType, index: number): string | number {
  if (typeof item === 'string' || typeof item === 'number') {
    return item;
  }
  return item[props.keyField] !== undefined 
    ? String(item[props.keyField]) 
    : index;
}

/** 解析列的值 */
function resolveValue(col: ColumnConfig, item: ItemType): string {
  // 优先使用动态函数
  if (col.valueFn) {
    return String(col.valueFn(item) ?? '');
  }
  // 其次使用静态值
  if (col.value !== undefined) {
    return String(col.value);
  }
  // 从 item 字段取值
  if (typeof item === 'string' || typeof item === 'number') {
    return String(item);
  }
  if (col.field && item[col.field] !== undefined) {
    return String(item[col.field]);
  }
  return '';
}

/** 解析列的图标 */
function resolveIcon(col: ColumnConfig, item: ItemType): IconType | undefined {
  if (col.iconFn) {
    return col.iconFn(item);
  }
  return col.icon;
}

/** 解析列的 CSS 类 */
function resolveClass(col: ColumnConfig, item: ItemType): string {
  const classes: string[] = [];
  if (col.class) {
    classes.push(col.class);
  }
  if (col.classFn) {
    classes.push(col.classFn(item));
  }
  return classes.join(' ');
}

/** 解析 toggle 状态 */
function resolveToggleState(col: ColumnConfig, item: ItemType): boolean {
  if (col.isEnabled) {
    return col.isEnabled(item);
  }
  if (col.field && typeof item === 'object' && item !== null) {
    return Boolean(item[col.field]);
  }
  return false;
}

/** 获取行的 CSS 类 */
function getRowClass(item: ItemType, index: number): string {
  const classes: string[] = [];
  if (props.rowClickable) {
    classes.push('cursor-pointer hover:bg-muted/30');
  }
  if (props.rowClass) {
    classes.push(props.rowClass);
  }
  if (props.rowClassFn) {
    classes.push(props.rowClassFn(item, index));
  }
  return classes.join(' ');
}

// ============ 事件处理 ============

/** 处理行点击 */
function handleRowClick(item: ItemType, index: number) {
  if (props.rowClickable) {
    emit('row-click', { item, index });
  }
}

/** 处理 toggle 切换 */
function handleToggle(col: ColumnConfig, item: ItemType, index: number) {
  const currentEnabled = resolveToggleState(col, item);
  emit('toggle', { column: col, item, index, enabled: !currentEnabled });
}

/** 处理按钮动作 */
function handleAction(col: ColumnConfig, item: ItemType, index: number) {
  emit('action', { column: col, item, index, action: col.action || col.key });
}
</script>
