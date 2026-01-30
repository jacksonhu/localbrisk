<template>
  <div class="catalog-panel h-full flex flex-col">
    <!-- 头部 -->
    <div class="px-4 py-3 border-b border-border">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs text-muted-foreground uppercase tracking-wider">{{ t('catalog.Workspace') }}</span>
        <button 
          class="w-6 h-6 rounded flex items-center justify-center bg-primary text-white hover:bg-primary/90 transition-colors"
          :title="t('catalog.createCatalog')"
          @click="showCreateCatalogDialog = true"
        >
          <Plus class="w-4 h-4" />
        </button>
      </div>
      
      <!-- 刷新按钮 -->
      <button
        v-if="!loading.tree"
        @click="handleRefresh"
        class="w-full flex items-center justify-center gap-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
      >
        <RefreshCw class="w-3 h-3" />
        <span>{{ t('common.refresh') }}</span>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading.tree" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <Loader2 class="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
        <span class="text-sm text-muted-foreground">{{ t('common.loading') }}</span>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="errorMsg" class="flex-1 flex items-center justify-center p-4">
      <div class="text-center">
        <AlertCircle class="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p class="text-sm text-muted-foreground mb-3">{{ errorMsg }}</p>
        <button
          @click="handleRefresh"
          class="px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary/90 transition-colors"
        >
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="catalogItems.length === 0" class="flex-1 flex items-center justify-center p-4">
      <div class="text-center">
        <Folder class="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
        <p class="text-sm text-muted-foreground mb-3">{{ t('common.noData') }}</p>
        <button
          @click="showCreateCatalogDialog = true"
          class="px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary/90 transition-colors"
        >
          {{ t('catalog.createCatalog') }}
        </button>
      </div>
    </div>

    <!-- 树形结构 -->
    <div v-else class="flex-1 overflow-y-auto p-2">
      <CatalogTree 
        :items="catalogItems"
        :selected-id="selectedNodeId"
        @select="handleSelect"
        @toggle-expand="handleToggleExpand"
        @context-menu="handleContextMenu"
      />
    </div>

    <!-- 创建 Catalog 弹窗 -->
    <CreateCatalogDialog
      :is-open="showCreateCatalogDialog"
      @close="showCreateCatalogDialog = false"
      @submit="handleCreateCatalog"
    />

    <!-- 创建 Schema 弹窗 -->
    <CreateSchemaDialog
      :is-open="showCreateSchemaDialog"
      :catalog-id="selectedCatalogId"
      @close="showCreateSchemaDialog = false"
      @submit="handleCreateSchema"
    />

    <!-- 创建 Agent 弹窗 -->
    <CreateAgentDialog
      :is-open="showCreateAgentDialog"
      :catalog-id="selectedCatalogId"
      @close="showCreateAgentDialog = false"
      @submit="handleCreateAgent"
    />

    <!-- 确认删除弹窗 -->
    <ConfirmDialog
      :is-open="showDeleteDialog"
      :message="deleteMessage"
      :description="deleteDescription"
      @close="showDeleteDialog = false"
      @confirm="handleConfirmDelete"
    />

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="fixed bg-card border border-border rounded-lg shadow-lg py-1 z-50 min-w-[160px]"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <!-- Catalog 右键菜单 -->
        <template v-if="contextMenu.type === 'catalog'">
          <button
            v-if="contextMenu.item?.metadata?.allow_custom_schema !== false"
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            @click="handleAddSchema"
          >
            <Plus class="w-4 h-4" />
            {{ t('catalog.createSchema') }}
          </button>
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            @click="handleAddAgent"
          >
            <Bot class="w-4 h-4" />
            {{ t('catalog.createAgent') }}
          </button>
          <div class="border-t border-border my-1"></div>
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteCatalog"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('catalog.deleteCatalog') }}
          </button>
        </template>

        <!-- Agent 右键菜单 -->
        <template v-else-if="contextMenu.type === 'agent'">
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteAgent"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('catalog.deleteAgent') }}
          </button>
        </template>

        <!-- Schema 右键菜单 -->
        <template v-else-if="contextMenu.type === 'schema'">
          <button
            v-if="!contextMenu.item?.readonly"
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteSchema"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('catalog.deleteSchema') }}
          </button>
          <div v-if="contextMenu.item?.readonly" class="px-3 py-2 text-sm text-muted-foreground">
            {{ t('catalog.readonly') }}
          </div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useI18n } from "vue-i18n";
import { Plus, RefreshCw, Loader2, AlertCircle, Folder, Trash2, Bot } from "lucide-vue-next";
import CatalogTree from "./CatalogTree.vue";
import CreateCatalogDialog from "./CreateCatalogDialog.vue";
import CreateSchemaDialog from "./CreateSchemaDialog.vue";
import CreateAgentDialog from "./CreateAgentDialog.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import type { CatalogItem, CatalogCreate, SchemaCreate, AgentCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// 从 store 获取响应式状态
const loading = store.loading;  // reactive 对象，不需要 .value
const errorMsg = computed(() => store.error.value);  // ref 需要通过计算属性访问

// 创建计算属性来正确访问 ref 的值
const catalogItems = computed(() => store.catalogItems.value);

// 计算当前选中的节点 ID
const selectedNodeId = computed(() => {
  // 优先级：Model > Asset > Schema > Agent > Catalog
  // Model 选中时
  if (store.selectedModel.value) {
    return store.selectedModel.value.id;
  }
  // Asset 选中时
  if (store.selectedAsset.value) {
    return store.selectedAsset.value.id;
  }
  // Schema 选中时
  if (store.selectedSchema.value) {
    return store.selectedSchema.value.id;
  }
  // Agent 选中时
  if (store.selectedAgent.value) {
    return store.selectedAgent.value.id;
  }
  // Catalog 选中时
  if (store.selectedCatalog.value) {
    return store.selectedCatalog.value.id;
  }
  return undefined;
});

// 弹窗状态
const showCreateCatalogDialog = ref(false);
const showCreateSchemaDialog = ref(false);
const showCreateAgentDialog = ref(false);
const showDeleteDialog = ref(false);
const selectedCatalogId = ref('');
const deleteMessage = ref('');
const deleteDescription = ref('');
const deleteTarget = ref<{ type: 'catalog' | 'schema' | 'agent'; id: string; name: string } | null>(null);

// 右键菜单状态
const contextMenu = ref<{
  visible: boolean;
  x: number;
  y: number;
  type: 'catalog' | 'schema' | 'asset' | 'agent' | null;
  item: CatalogItem | null;
  parentId?: string;
}>({
  visible: false,
  x: 0,
  y: 0,
  type: null,
  item: null,
});

// 刷新数据
async function handleRefresh() {
  await store.fetchTree();
}

// 选择项目
function handleSelect(item: CatalogItem) {
  console.log("Selected:", item);
  if (item.type === 'catalog') {
    // 点击 Catalog，打开 Catalog 详情页
    store.clearSelectedSchema();
    store.clearSelectedAgent();
    store.selectCatalog(item.id);
  } else if (item.type === 'schema') {
    // 点击 Schema，展开并打开 Schema 详情页
    store.clearSelectedAgent();
    store.clearSelectedAsset();  // 清除 Asset 选中状态
    // 优先从 metadata 获取 catalog_id，避免名称中包含下划线导致解析错误
    const catalogId = item.metadata?.catalog_id as string | undefined;
    if (catalogId) {
      store.selectSchemaByName(catalogId, item.name);
    } else {
      // 兼容旧数据：从 item.id 中提取 catalog_id（格式为 catalogId_schemaName）
      const fallbackCatalogId = item.id.substring(0, item.id.lastIndexOf('_' + item.name));
      store.selectSchemaByName(fallbackCatalogId, item.name);
    }
  } else if (item.type === 'agent') {
    // 点击 Agent，打开 Agent 详情页
    store.clearSelectedSchema();
    const catalogId = item.metadata?.catalog_id as string | undefined;
    if (catalogId) {
      store.selectAgent(catalogId, item.name);
    }
  } else if (item.type === 'model') {
    // 点击 Model，打开 Model 详情页
    store.clearSelectedAgent();
    store.clearSelectedAsset();
    // 优先从 metadata 获取 catalog_id 和 schema_name
    const catalogId = item.metadata?.catalog_id as string | undefined;
    const schemaName = item.metadata?.schema_name as string | undefined;
    
    if (catalogId && schemaName) {
      store.selectModel(catalogId, schemaName, item.name);
    } else {
      console.warn('Model metadata missing catalog_id or schema_name');
    }
  } else if (item.type === 'table' || item.type === 'volume') {
    // 点击 Table 或 Volume，打开资产详情页
    store.clearSelectedAgent();
    // 优先从 metadata 获取 catalog_id 和 schema_name
    const catalogId = item.metadata?.catalog_id as string | undefined;
    const schemaName = item.metadata?.schema_name as string | undefined;
    
    if (catalogId && schemaName) {
      store.selectAssetByName(catalogId, schemaName, item.name);
    } else {
      // 兼容旧数据：尝试从 ID 解析（可能因名称含下划线而失败）
      console.warn('Asset metadata missing catalog_id or schema_name, falling back to ID parsing');
    }
  }
}

// 切换展开/折叠
function handleToggleExpand(item: CatalogItem) {
  store.toggleNodeExpanded(item.id);
}

// 右键菜单
function handleContextMenu(event: MouseEvent, item: CatalogItem, parentId?: string) {
  event.preventDefault();
  
  // 根据节点类型确定菜单类型
  let menuType: 'catalog' | 'schema' | 'asset' | 'agent' | null = null;
  if (item.type === 'catalog') {
    menuType = 'catalog';
  } else if (item.type === 'schema') {
    menuType = 'schema';
  } else if (item.type === 'agent') {
    menuType = 'agent';
  } else {
    menuType = 'asset';
  }
  
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    type: menuType,
    item,
    parentId,
  };
}

// 关闭右键菜单
function closeContextMenu() {
  contextMenu.value.visible = false;
}

// 添加 Schema
function handleAddSchema() {
  if (contextMenu.value.item) {
    selectedCatalogId.value = contextMenu.value.item.id;
    showCreateSchemaDialog.value = true;
  }
  closeContextMenu();
}

// 添加 Agent
function handleAddAgent() {
  if (contextMenu.value.item) {
    selectedCatalogId.value = contextMenu.value.item.id;
    showCreateAgentDialog.value = true;
  }
  closeContextMenu();
}

// 删除 Catalog
function handleDeleteCatalog() {
  if (contextMenu.value.item) {
    deleteTarget.value = {
      type: 'catalog',
      id: contextMenu.value.item.id,
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('catalog.confirmDeleteCatalog', { name: contextMenu.value.item.name });
    deleteDescription.value = t('catalog.confirmDeleteCatalogDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 删除 Schema
function handleDeleteSchema() {
  if (contextMenu.value.item && contextMenu.value.parentId) {
    deleteTarget.value = {
      type: 'schema',
      id: contextMenu.value.parentId,
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('catalog.confirmDeleteSchema', { name: contextMenu.value.item.name });
    deleteDescription.value = t('catalog.confirmDeleteSchemaDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 删除 Agent
function handleDeleteAgent() {
  if (contextMenu.value.item) {
    const catalogId = contextMenu.value.item.metadata?.catalog_id as string || contextMenu.value.parentId;
    deleteTarget.value = {
      type: 'agent',
      id: catalogId || '',
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('catalog.confirmDeleteAgent', { name: contextMenu.value.item.name });
    deleteDescription.value = t('catalog.confirmDeleteAgentDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 创建 Catalog
async function handleCreateCatalog(data: CatalogCreate) {
  const result = await store.createCatalog(data);
  if (result) {
    showCreateCatalogDialog.value = false;
  }
}

// 创建 Schema
async function handleCreateSchema(catalogId: string, data: SchemaCreate) {
  const result = await store.createSchema(catalogId, data);
  if (result) {
    showCreateSchemaDialog.value = false;
  }
}

// 创建 Agent
async function handleCreateAgent(catalogId: string, data: AgentCreate) {
  const result = await store.createAgent(catalogId, data);
  if (result) {
    showCreateAgentDialog.value = false;
  }
}

// 确认删除
async function handleConfirmDelete() {
  if (!deleteTarget.value) return;

  let success = false;
  if (deleteTarget.value.type === 'catalog') {
    success = await store.deleteCatalog(deleteTarget.value.id);
  } else if (deleteTarget.value.type === 'schema') {
    success = await store.deleteSchema(deleteTarget.value.id, deleteTarget.value.name);
  } else if (deleteTarget.value.type === 'agent') {
    success = await store.deleteAgent(deleteTarget.value.id, deleteTarget.value.name);
  }

  if (success) {
    showDeleteDialog.value = false;
    deleteTarget.value = null;
  }
}

// 点击外部关闭右键菜单
function handleClickOutside(_event: MouseEvent) {
  if (contextMenu.value.visible) {
    closeContextMenu();
  }
}

// 初始化
onMounted(async () => {
  document.addEventListener('click', handleClickOutside);
  await store.fetchTree();
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>
