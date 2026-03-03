<template>
  <div class="catalog-panel h-full flex flex-col">
    <!-- 头部 -->
    <div class="px-4 py-3 border-b border-border">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs text-muted-foreground uppercase tracking-wider">{{ t('businessUnit.workspace') }}</span>
        <button 
          class="w-6 h-6 rounded flex items-center justify-center bg-primary text-white hover:bg-primary/90 transition-colors"
          :title="t('businessUnit.createBusinessUnit')"
          @click="showCreateBusinessUnitDialog = true"
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
          @click="showCreateBusinessUnitDialog = true"
          class="px-3 py-1.5 text-sm bg-primary text-white rounded hover:bg-primary/90 transition-colors"
        >
          {{ t('businessUnit.createBusinessUnit') }}
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
        @ensure-expand="handleEnsureExpand"
        @context-menu="handleContextMenu"
      />
    </div>

    <!-- 创建 BusinessUnit 弹窗 -->
    <CreateBusinessUnitDialog
      :is-open="showCreateBusinessUnitDialog"
      @close="showCreateBusinessUnitDialog = false"
      @submit="handleCreateBusinessUnit"
    />

    <!-- 创建 AssetBundle 弹窗 -->
    <AssetBundleDialog
      :is-open="showCreateAssetBundleDialog"
      :business-unit-id="selectedBusinessUnitId"
      @close="showCreateAssetBundleDialog = false"
      @create="handleCreateAssetBundle"
    />

    <!-- 创建 Agent 弹窗 -->
    <CreateAgentDialog
      :is-open="showCreateAgentDialog"
      :business-unit-id="selectedBusinessUnitId"
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
        <!-- BusinessUnit 右键菜单 -->
        <template v-if="contextMenu.type === 'catalog'">
          <button
            v-if="contextMenu.item?.metadata?.allow_custom_schema !== false"
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            @click="handleAddAssetBundle"
          >
            <Plus class="w-4 h-4" />
            {{ t('businessUnit.createAssetBundle') }}
          </button>
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center gap-2"
            @click="handleAddAgent"
          >
            <Bot class="w-4 h-4" />
            {{ t('businessUnit.createAgent') }}
          </button>
          <div class="border-t border-border my-1"></div>
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteBusinessUnit"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('businessUnit.deleteBusinessUnit') }}
          </button>
        </template>

        <!-- Agent 右键菜单 -->
        <template v-else-if="contextMenu.type === 'agent'">
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteAgent"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('businessUnit.deleteAgent') }}
          </button>
        </template>

        <!-- AssetBundle 右键菜单 -->
        <template v-else-if="contextMenu.type === 'schema'">
          <button
            class="w-full px-3 py-2 text-sm text-left hover:bg-muted text-red-600 flex items-center gap-2"
            @click="handleDeleteAssetBundle"
          >
            <Trash2 class="w-4 h-4" />
            {{ t('businessUnit.deleteAssetBundle') }}
          </button>
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
import CreateBusinessUnitDialog from "./CreateBusinessUnitDialog.vue";
import AssetBundleDialog from "./AssetBundleDialog.vue";
import CreateAgentDialog from "./CreateAgentDialog.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import { useBusinessUnitStore } from "@/stores/businessUnitStore";
import type { BusinessUnitItem, BusinessUnitCreate, AssetBundleCreate, AgentCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useBusinessUnitStore();

// 从 store 获取响应式状态
const loading = store.loading;  // reactive 对象，不需要 .value
const errorMsg = computed(() => store.error.value);  // ref 需要通过计算属性访问

// 创建计算属性来正确访问 ref 的值
const catalogItems = computed(() => store.businessUnitItems.value);

// 使用 store 中统一的选中节点 ID 计算
// 所有节点类型的 ID 生成逻辑都在 store 中集中管理
const selectedNodeId = computed(() => store.selectedNodeId.value);

// 弹窗状态
const showCreateBusinessUnitDialog = ref(false);
const showCreateAssetBundleDialog = ref(false);
const showCreateAgentDialog = ref(false);
const showDeleteDialog = ref(false);
const selectedBusinessUnitId = ref('');
const deleteMessage = ref('');
const deleteDescription = ref('');
const deleteTarget = ref<{ type: 'catalog' | 'schema' | 'agent'; id: string; name: string } | null>(null);

// 右键菜单状态
const contextMenu = ref<{
  visible: boolean;
  x: number;
  y: number;
  type: 'catalog' | 'schema' | 'asset' | 'agent' | null;
  item: BusinessUnitItem | null;
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
function handleSelect(item: BusinessUnitItem) {
  console.log("CatalogPanel.handleSelect:", item.type, item.name, item.metadata);
  
  // 根据节点类型调用对应的 store 方法
  // 所有状态清除逻辑都在 store 的 selectXxx 方法中处理
  switch (item.type) {
    case 'catalog':
    case 'business_unit':
      // 选择 BusinessUnit：清除所有子级选择
      store.clearSelectedAssetBundle();
      store.clearSelectedAgent();
      store.selectBusinessUnit(item.id);
      break;
      
    case 'schema':
    case 'asset_bundle': {
      // 选择 AssetBundle：需要 business_unit_id
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      if (businessUnitId) {
        store.selectAssetBundleByName(businessUnitId, item.name);
      } else {
        // 兼容旧数据：从 item.id 中提取 business_unit_id
        const fallbackBusinessUnitId = item.id.substring(0, item.id.lastIndexOf('_' + item.name));
        store.selectAssetBundleByName(fallbackBusinessUnitId, item.name);
      }
      break;
    }
    
    case 'agent': {
      // 选择 Agent：需要 business_unit_id
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      if (businessUnitId) {
        store.selectAgent(businessUnitId, item.name);
      }
      break;
    }
    
    case 'prompt': {
      // 选择 Prompt：需要 business_unit_id 和 agent_name
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      const agentName = item.metadata?.agent_name as string | undefined;
      if (businessUnitId && agentName) {
        // 从节点 ID 中提取原始文件名
        // 节点 ID 格式: {agentId}_prompt_{filename}
        // 例如: market_analysis_agent_dd_prompt_ddd.md
        const prefix = '_prompt_';
        const prefixIndex = item.id.lastIndexOf(prefix);
        const originalFileName = prefixIndex >= 0 
          ? item.id.substring(prefixIndex + prefix.length) 
          : item.name;
        store.selectPrompt(businessUnitId, agentName, originalFileName);
      }
      break;
    }
    
    case 'skill': {
      // 选择 Skill：需要 business_unit_id 和 agent_name
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      const agentName = item.metadata?.agent_name as string | undefined;
      if (businessUnitId && agentName) {
        // 从节点 ID 中提取 skill 名称
        // 节点 ID 格式: {agentId}_skill_{skillName}
        // 例如: market_analysis_agent_dd_skill_my-skill
        const prefix = '_skill_';
        const prefixIndex = item.id.lastIndexOf(prefix);
        const skillName = prefixIndex >= 0 
          ? item.id.substring(prefixIndex + prefix.length) 
          : item.name;
        store.selectSkill(businessUnitId, agentName, skillName);
      }
      break;
    }
    
    case 'model': {
      // 选择 Model：需要 business_unit_id 和 agent_name
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      const agentName = item.metadata?.agent_name as string | undefined;
      if (businessUnitId && agentName) {
        store.selectModel(businessUnitId, agentName, item.name);
      } else {
        console.warn('Model metadata missing business_unit_id or agent_name');
      }
      break;
    }
    
    case 'mcp': {
      // 选择 MCP：需要 business_unit_id 和 agent_name
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      const agentName = item.metadata?.agent_name as string | undefined;
      if (businessUnitId && agentName) {
        store.selectMCP(businessUnitId, agentName, item.name);
      } else {
        console.warn('MCP metadata missing business_unit_id or agent_name');
      }
      break;
    }
    
    case 'table':
    case 'volume': {
      // 选择 Table/Volume（Asset）：需要 business_unit_id 和 bundle_name
      const businessUnitId = item.metadata?.business_unit_id as string | undefined;
      const bundleName = item.metadata?.bundle_name as string | undefined;
      if (businessUnitId && bundleName) {
        store.selectAssetByName(businessUnitId, bundleName, item.name);
      } else {
        console.warn('Asset metadata missing business_unit_id or bundle_name');
      }
      break;
    }
    
    default:
      console.warn('Unknown item type:', item.type);
  }
}

// 切换展开/折叠（点击展开箭头时）
function handleToggleExpand(item: BusinessUnitItem) {
  store.toggleNodeExpanded(item.id);
}

// 确保展开（点击节点内容时）
function handleEnsureExpand(item: BusinessUnitItem) {
  store.toggleNodeExpanded(item.id, true);
}

// 右键菜单
function handleContextMenu(event: MouseEvent, item: BusinessUnitItem, parentId?: string) {
  event.preventDefault();
  
  // 根据节点类型确定菜单类型
  let menuType: 'catalog' | 'schema' | 'asset' | 'agent' | null = null;
  if (item.type === 'catalog' || item.type === 'business_unit') {
    menuType = 'catalog';
  } else if (item.type === 'schema' || item.type === 'asset_bundle') {
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

// 添加 AssetBundle
function handleAddAssetBundle() {
  if (contextMenu.value.item) {
    selectedBusinessUnitId.value = contextMenu.value.item.id;
    showCreateAssetBundleDialog.value = true;
  }
  closeContextMenu();
}

// 添加 Agent
function handleAddAgent() {
  if (contextMenu.value.item) {
    selectedBusinessUnitId.value = contextMenu.value.item.id;
    showCreateAgentDialog.value = true;
  }
  closeContextMenu();
}

// 删除 BusinessUnit
function handleDeleteBusinessUnit() {
  if (contextMenu.value.item) {
    deleteTarget.value = {
      type: 'catalog',
      id: contextMenu.value.item.id,
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('businessUnit.confirmDeleteBusinessUnit', { name: contextMenu.value.item.name });
    deleteDescription.value = t('businessUnit.confirmDeleteBusinessUnitDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 删除 AssetBundle
function handleDeleteAssetBundle() {
  if (contextMenu.value.item && contextMenu.value.parentId) {
    deleteTarget.value = {
      type: 'schema',
      id: contextMenu.value.parentId,
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('businessUnit.confirmDeleteAssetBundle', { name: contextMenu.value.item.name });
    deleteDescription.value = t('businessUnit.confirmDeleteAssetBundleDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 删除 Agent
function handleDeleteAgent() {
  if (contextMenu.value.item) {
    const businessUnitId = contextMenu.value.item.metadata?.business_unit_id as string || contextMenu.value.parentId;
    deleteTarget.value = {
      type: 'agent',
      id: businessUnitId || '',
      name: contextMenu.value.item.name,
    };
    deleteMessage.value = t('businessUnit.confirmDeleteAgent', { name: contextMenu.value.item.name });
    deleteDescription.value = t('businessUnit.confirmDeleteAgentDesc');
    showDeleteDialog.value = true;
  }
  closeContextMenu();
}

// 创建 BusinessUnit
async function handleCreateBusinessUnit(data: BusinessUnitCreate) {
  const result = await store.createBusinessUnit(data);
  if (result) {
    showCreateBusinessUnitDialog.value = false;
  }
}

// 创建 AssetBundle
async function handleCreateAssetBundle(businessUnitId: string, data: AssetBundleCreate) {
  const result = await store.createAssetBundle(businessUnitId, data);
  if (result) {
    showCreateAssetBundleDialog.value = false;
  }
}

// 创建 Agent
async function handleCreateAgent(businessUnitId: string, data: AgentCreate) {
  const result = await store.createAgent(businessUnitId, data);
  if (result) {
    showCreateAgentDialog.value = false;
  }
}

// 确认删除
async function handleConfirmDelete() {
  if (!deleteTarget.value) return;

  let success = false;
  if (deleteTarget.value.type === 'catalog') {
    success = await store.deleteBusinessUnit(deleteTarget.value.id);
  } else if (deleteTarget.value.type === 'schema') {
    success = await store.deleteAssetBundle(deleteTarget.value.id, deleteTarget.value.name);
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
