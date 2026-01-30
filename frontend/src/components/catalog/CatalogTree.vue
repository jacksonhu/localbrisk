<template>
  <div class="catalog-tree">
    <div v-for="item in items" :key="item.id" class="tree-node">
      <div
        class="tree-item flex items-center gap-2 text-sm px-2 py-1.5 rounded cursor-pointer text-foreground"
        :class="[
          item.type === 'placeholder' ? 'text-muted-foreground cursor-default' : 'hover:bg-muted',
          item.readonly ? 'opacity-75' : '',
          isSelected(item) ? 'bg-primary/10 text-primary font-medium' : ''
        ]"
        @click="handleClick(item)"
        @contextmenu="(e) => handleContextMenu(e, item)"
      >
        <!-- 展开/折叠图标 -->
        <button
          v-if="canExpand(item)"
          class="w-4 h-4 flex items-center justify-center flex-shrink-0"
          @click.stop="handleToggleExpand(item)"
        >
          <ChevronRight
            class="w-3 h-3 transition-transform duration-150"
            :class="{ 'rotate-90': item.expanded }"
          />
        </button>
        <span v-else class="w-4 flex-shrink-0"></span>

        <!-- 图标 -->
        <component :is="getIcon(item.type)" class="w-4 h-4 flex-shrink-0" :class="getIconColor(item.type)" />

        <!-- 名称 -->
        <span class="truncate flex-1" :class="isSelected(item) ? 'text-primary' : 'text-foreground'">{{ item.name || '(无名称)' }}</span>

        <!-- 只读标识 -->
        <Lock v-if="item.readonly" class="w-3 h-3 text-muted-foreground flex-shrink-0" />

      </div>

      <!-- 子节点 -->
      <div v-if="item.expanded && item.children" class="ml-4">
        <CatalogTree 
          :items="item.children" 
          :parent-id="item.id"
          :selected-id="selectedId"
          @select="(child) => emit('select', child)"
          @toggle-expand="(child) => emit('toggle-expand', child)"
          @context-menu="(e, child, pId) => emit('context-menu', e, child, pId || item.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, Folder, Database, Table, FolderOpen, Bot, FileText, Lock, Code, Cpu, Layers } from "lucide-vue-next";
import type { CatalogItem } from "@/types/catalog";

const props = defineProps<{
  items: CatalogItem[];
  parentId?: string;
  selectedId?: string;
}>();

const emit = defineEmits<{
  select: [item: CatalogItem];
  'toggle-expand': [item: CatalogItem];
  'context-menu': [event: MouseEvent, item: CatalogItem, parentId?: string];
}>();

// 判断节点是否被选中
const isSelected = (item: CatalogItem) => {
  if (!props.selectedId) return false;
  return item.id === props.selectedId;
};

const getIcon = (type: string) => {
  const iconMap: Record<string, any> = {
    catalog: Folder,
    schema: Database,
    asset_type: Layers,
    table: Table,
    volume: FolderOpen,
    function: Code,
    model: Cpu,
    agent: Bot,
    note: FileText,
    placeholder: FileText,
    folder: Folder,
    skill: Code,
    prompt: FileText,
  };
  return iconMap[type] || Folder;
};

const getIconColor = (type: string) => {
  const colorMap: Record<string, string> = {
    catalog: "text-yellow-500",
    schema: "text-purple-500",
    asset_type: "text-gray-500",
    table: "text-blue-500",
    volume: "text-green-500",
    function: "text-purple-500",
    model: "text-orange-500",
    agent: "text-orange-500",
    note: "text-gray-500",
    placeholder: "text-gray-400",
    folder: "text-yellow-500",
    skill: "text-cyan-500",
    prompt: "text-emerald-500",
  };
  return colorMap[type] || "text-gray-500";
};

// 判断节点是否可展开
const canExpand = (item: CatalogItem) => {
  if (item.type === 'placeholder') {
    return false;
  }
  // 有子节点的可展开
  if (item.children && item.children.length > 0) {
    return true;
  }
  // folder 类型即使没有子节点也显示展开箭头（空文件夹）
  if (item.type === 'folder') {
    return true;
  }
  return false;
};

const handleToggleExpand = (item: CatalogItem) => {
  emit("toggle-expand", item);
};

const handleClick = (item: CatalogItem) => {
  // 占位符节点不响应点击
  if (item.type === "placeholder") {
    return;
  }
  
  // 记录点击日志，便于调试
  console.log("CatalogTree.handleClick:", item.type, item.name);
  
  // 根据节点类型决定行为
  // 1. 容器类节点（只展开，不选择）：asset_type, folder
  // 2. 可展开+可选择的节点：catalog, schema, agent
  // 3. 只选择的叶子节点：prompt, skill, table, volume, model
  
  switch (item.type) {
    // 纯容器节点：只切换展开状态
    case "asset_type":
    case "folder":
      emit("toggle-expand", item);
      break;
    
    // 可展开的父节点：展开 + 选择
    case "catalog":
    case "schema":
    case "agent":
      emit("toggle-expand", item);
      emit("select", item);
      break;
    
    // 叶子节点：只选择
    case "prompt":
    case "skill":
    case "table":
    case "volume":
    case "model":
    case "note":
    case "function":
      emit("select", item);
      break;
    
    // 其他未知类型：默认选择行为
    default:
      emit("select", item);
  }
};

const handleContextMenu = (event: MouseEvent, item: CatalogItem) => {
  // 资产类型节点、文件夹节点和占位符节点不显示右键菜单
  if (item.type !== "placeholder" && item.type !== "asset_type" && item.type !== "folder") {
    emit("context-menu", event, item, props.parentId);
  }
};
</script>
