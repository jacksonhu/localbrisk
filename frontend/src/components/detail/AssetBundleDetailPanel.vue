<template>
  <div v-if="selectedAssetBundle" class="asset-bundle-detail-panel h-full flex flex-col p-6">
    <!-- 面包屑导航 -->
    <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4">
      <button 
        class="flex items-center gap-1 hover:text-foreground transition-colors"
        @click="goBack"
      >
        <ArrowLeft class="w-4 h-4" />
      </button>
      <span class="text-primary cursor-pointer hover:underline" @click="goToBusinessUnit">
        {{ selectedBusinessUnit?.display_name || selectedBusinessUnit?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span>{{ selectedAssetBundle?.name }}</span>
    </div>

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <Database class="w-6 h-6 text-purple-500" />
        <h1 class="text-2xl font-semibold">{{ selectedAssetBundle.name }}</h1>
        <!-- 类型标识 -->
        <span 
          :class="selectedAssetBundle.bundle_type === 'local' 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'"
          class="px-2 py-0.5 text-xs rounded flex items-center gap-1"
        >
          <HardDrive v-if="selectedAssetBundle.bundle_type === 'local'" class="w-3 h-3" />
          <PlugZap v-else class="w-3 h-3" />
          {{ selectedAssetBundle.bundle_type === 'local' ? t('businessUnit.local') : t('businessUnit.external') }}
        </span>
        <!-- 连接类型标识 -->
        <span 
          v-if="selectedAssetBundle.connection"
          class="px-2 py-0.5 text-xs bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400 rounded flex items-center gap-1"
        >
          {{ selectedAssetBundle.connection.type.toUpperCase() }}
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="showEditAssetBundleDialog = true"
            class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            :title="t('businessUnit.editAssetBundle')"
          >
            <Pencil class="w-4 h-4 text-muted-foreground hover:text-foreground" />
          </button>
          <button
            v-if="selectedAssetBundle.bundle_type === 'external'"
            @click="handleSyncMetadata"
            :disabled="syncing"
            class="p-1.5 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
            :title="t('detail.syncMetadata')"
          >
            <RefreshCw class="w-4 h-4 text-muted-foreground hover:text-blue-600" :class="{ 'animate-spin': syncing }" />
          </button>
          <button
            @click="confirmDeleteAssetBundle"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('businessUnit.deleteAssetBundle')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
      </div>
      <!-- 创建按钮 -->
      <div v-if="selectedAssetBundle.bundle_type=='local'" class="relative">
        <button
          @click="showCreateMenu = !showCreateMenu"
          class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
        >
          <Plus class="w-4 h-4" />
          {{ t('common.create') }}
          <ChevronDown class="w-4 h-4" />
        </button>
        
        <!-- 创建下拉菜单 -->
        <Transition name="dropdown">
          <div 
            v-if="showCreateMenu" 
            class="absolute right-0 top-full mt-2 w-48 bg-card border border-border rounded-lg shadow-float-lg py-1 z-50"
          >
            <button
              v-for="item in createMenuItems"
              :key="item.type"
              @click="handleCreateAsset(item.type)"
              class="w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-muted transition-colors text-left"
            >
              <component :is="item.icon" class="w-4 h-4" :class="item.iconColor" />
              <span>{{ item.label }}</span>
            </button>
          </div>
        </Transition>
        
        <!-- 点击外部关闭菜单 -->
        <div 
          v-if="showCreateMenu" 
          class="fixed inset-0 z-40" 
          @click="showCreateMenu = false"
        ></div>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="flex items-center gap-1 border-b border-border mb-6">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        class="px-4 py-2 text-sm font-medium transition-colors relative"
        :class="activeTab === tab.id 
          ? 'text-primary' 
          : 'text-muted-foreground hover:text-foreground'"
      >
        <div class="flex items-center gap-2">
          <component :is="tab.icon" class="w-4 h-4" />
          {{ tab.label }}
        </div>
        <!-- 激活指示器 -->
        <div
          v-if="activeTab === tab.id"
          class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
        ></div>
      </button>
    </div>

    <!-- Tab 内容 -->
    <div class="flex-1 overflow-y-auto">
      <!-- 概览 Tab -->
      <div v-if="activeTab === 'overview'" class="space-y-6">
        <!-- 描述卡片 -->
        <div class="card-float p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-medium">{{ t('common.description') }}</h3>
            <button 
              @click="showEditAssetBundleDialog = true"
              class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center"
            >
              <Pencil class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
          <p class="text-muted-foreground text-sm">
            {{ selectedAssetBundle.description || t('detail.noDescription') }}
          </p>
        </div>

        <!-- Asset Bundle 基本信息 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-4">{{ t('detail.assetBundleInfo') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('common.name') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.name }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('businessUnit.bundleType') }}</label>
              <p class="font-medium">
                {{ selectedAssetBundle.bundle_type === 'local' ? t('businessUnit.bundleTypeLocal') : t('businessUnit.bundleTypeExternal') }}
              </p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedAssetBundle.created_at) }}</p>
            </div>
            <div v-if="selectedAssetBundle.synced_at">
              <label class="text-muted-foreground">{{ t('detail.lastSyncedAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedAssetBundle.synced_at) }}</p>
            </div>
            <div v-if="selectedAssetBundle.path" class="col-span-2">
              <label class="text-muted-foreground">{{ t('common.path') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedAssetBundle.path }}
              </p>
            </div>
          </div>
        </div>

        <!-- 数据库连接配置 (仅 External 类型显示) -->
        <div v-if="selectedAssetBundle.bundle_type === 'external' && selectedAssetBundle.connection" class="card-float p-4">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-medium flex items-center gap-2">
              <PlugZap class="w-4 h-4 text-cyan-500" />
              {{ t('detail.connectionConfig') }}
            </h3>
            <button
              @click="handleSyncMetadata"
              :disabled="syncing"
              class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': syncing }" />
              {{ syncing ? t('detail.syncing') : t('detail.syncNow') }}
            </button>
          </div>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('connection.type') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.connection.type.toUpperCase() }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('connection.database') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.connection.db_name }}</p>
            </div>
            <div v-if="selectedAssetBundle.connection.host">
              <label class="text-muted-foreground">{{ t('connection.host') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.connection.host }}</p>
            </div>
            <div v-if="selectedAssetBundle.connection.port">
              <label class="text-muted-foreground">{{ t('connection.port') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.connection.port }}</p>
            </div>
            <div v-if="selectedAssetBundle.connection.username">
              <label class="text-muted-foreground">{{ t('connection.username') }}</label>
              <p class="font-medium">{{ selectedAssetBundle.connection.username }}</p>
            </div>
          </div>
          
          <!-- 同步结果提示 -->
          <div v-if="syncResult" class="mt-4 p-3 rounded-lg" :class="syncResult.success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'">
            <div class="flex items-center gap-2 mb-2">
              <CheckCircle v-if="syncResult.success" class="w-4 h-4 text-green-500" />
              <XCircle v-else class="w-4 h-4 text-red-500" />
              <span class="font-medium" :class="syncResult.success ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'">
                {{ syncResult.success ? t('detail.syncSuccess') : t('detail.syncFailed') }}
              </span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p>{{ t('detail.tablesSynced', { count: syncResult.tables_synced }) }}</p>
              <p>{{ t('detail.columnsSynced', { count: syncResult.columns_synced }) }}</p>
              <p v-if="syncResult.errors.length > 0" class="text-red-600 dark:text-red-400">
                {{ t('detail.syncErrors', { count: syncResult.errors.length }) }}: {{ syncResult.errors.join(', ') }}
              </p>
            </div>
          </div>
        </div>

        <!-- Asset 列表 -->
        <ItemListCard
          :title="t('detail.assets')"
          :items="currentAssets"
          :columns="assetColumns"
          key-field="id"
          show-count
          :count-label="t('agent.items')"
          :empty-text="t('detail.noAssets')"
          :empty-icon="FolderOpen"
          searchable
          :search-placeholder="t('detail.filterAssets')"
          :search-fields="['name']"
          row-clickable
          @row-click="handleAssetRowClick"
          @action="handleAssetAction"
        />
      </div>

      <!-- 配置 Tab -->
      <div v-if="activeTab === 'config'" class="h-full">
        <ConfigEditor
          v-model="configContent"
          :modified="configModified"
          :saving="savingConfig"
          @save="saveConfig"
          @copy="copyConfig"
        />
      </div>
    </div>

    <!-- 确认删除弹窗 -->
    <ConfirmDialog
      :is-open="showDeleteDialog"
      :message="deleteMessage"
      :description="deleteDescription"
      @close="showDeleteDialog = false"
      @confirm="handleConfirmDelete"
    />

    <!-- 编辑 Asset Bundle 弹窗 -->
    <AssetBundleDialog
      :is-open="showEditAssetBundleDialog"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      :asset-bundle="selectedAssetBundle"
      @close="showEditAssetBundleDialog = false"
      @update="handleUpdateAssetBundle"
    />

    <!-- 创建 Volume 弹窗 -->
    <CreateVolumeDialog
      :is-open="showCreateVolumeDialog"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      :bundle-name="selectedAssetBundle?.name || ''"
      @close="showCreateVolumeDialog = false"
      @submit="handleCreateVolume"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, ChevronDown, Database, Pencil, 
  HardDrive, Trash2, Table, FolderOpen, Bot, FileText, Plus, Code,
  FileCode, PlugZap, RefreshCw, CheckCircle, XCircle
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import AssetBundleDialog from "@/components/catalog/AssetBundleDialog.vue";
import CreateVolumeDialog from "@/components/catalog/CreateVolumeDialog.vue";
import ItemListCard from "@/components/common/ItemListCard.vue";
import ConfigEditor from "@/components/common/ConfigEditor.vue";
import type { ColumnConfig } from "@/components/common/ItemListCard.vue";
import { useBusinessUnitStore } from "@/stores/businessUnitStore";
import { useConfigManager } from "@/composables/useConfigManager";
import { assetBundleApi } from "@/services/api";
import type { AssetBundleUpdate, AssetCreate, Asset, SyncResult } from "@/types/catalog";

const { t } = useI18n();
const store = useBusinessUnitStore();

// 使用 computed 保持响应式，直接从 store 获取
const selectedBusinessUnit = computed(() => store.selectedBusinessUnit.value);
const selectedAssetBundle = computed(() => store.selectedAssetBundle.value);
const currentAssets = computed(() => store.currentAssets.value);

// Tab 状态
const activeTab = ref<'overview' | 'config'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// 使用配置管理器处理 Asset Bundle 配置
const assetBundleConfigManager = useConfigManager({
  type: 'asset_bundle',
  getConfigPath: () => {
    if (!selectedAssetBundle.value?.path) return undefined;
    return `${selectedAssetBundle.value.path}/bundle.yaml`;
  },
  loadConfig: async () => {
    if (!selectedBusinessUnit.value || !selectedAssetBundle.value) return '';
    try {
      const response = await assetBundleApi.getConfig(selectedBusinessUnit.value.id, selectedAssetBundle.value.name);
      return response.content;
    } catch (e) {
      console.error('Failed to load asset bundle config:', e);
      return '';
    }
  },
  onSaved: async () => {
    // 刷新 asset bundle 数据
    if (selectedBusinessUnit.value && selectedAssetBundle.value) {
      await store.fetchBusinessUnit(selectedBusinessUnit.value.id);
    }
  },
});

// 解构配置管理器的状态和方法
const {
  configContent,
  configModified,
  savingConfig,
  saveConfig,
  copyConfig,
  loadConfigContent: loadConfig,
} = assetBundleConfigManager;

// 同步状态
const syncing = ref(false);
const syncResult = ref<SyncResult | null>(null);

// 弹窗状态
const showDeleteDialog = ref(false);
const showEditAssetBundleDialog = ref(false);
const showCreateMenu = ref(false);
const showCreateVolumeDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 创建菜单项（移除 Model 创建选项）
const createMenuItems = computed(() => [
  { 
    type: 'table', 
    label: t('asset.createTable'), 
    icon: Table, 
    iconColor: 'text-blue-500' 
  },
  { 
    type: 'volume', 
    label: t('asset.createVolume'), 
    icon: FolderOpen, 
    iconColor: 'text-green-500' 
  },
  { 
    type: 'function', 
    label: t('asset.createFunction'), 
    icon: Code, 
    iconColor: 'text-purple-500' 
  },
]);

// ItemListCard 列配置类型
type ItemType = string | number | Record<string, unknown>;

// Asset 列配置
const assetColumns: ColumnConfig[] = [
  { 
    key: 'icon', 
    type: 'icon', 
    iconFn: (item: ItemType) => getAssetIcon((item as Record<string, unknown>).asset_type as string),
    classFn: (item: ItemType) => getAssetIconColor((item as Record<string, unknown>).asset_type as string),
  },
  { 
    key: 'name', 
    type: 'text', 
    field: 'name', 
    flex: true, 
    class: 'font-medium',
    searchable: true,
  },
  { 
    key: 'type', 
    type: 'badge', 
    valueFn: (item: ItemType) => getAssetTypeLabel((item as Record<string, unknown>).asset_type as string),
    classFn: (item: ItemType) => getAssetTypeClass((item as Record<string, unknown>).asset_type as string),
  },
  { 
    key: 'created_at', 
    type: 'text', 
    valueFn: (item: ItemType) => formatDate((item as Record<string, unknown>).created_at as string),
    class: 'text-muted-foreground',
  },
  { 
    key: 'delete', 
    type: 'button', 
    icon: Trash2,
    action: 'delete',
    class: 'p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition-colors',
  },
];

// 获取 Asset 图标颜色
function getAssetIconColor(type: string) {
  const colorMap: Record<string, string> = {
    table: "text-blue-500",
    volume: "text-green-500",
    agent: "text-orange-500",
    note: "text-gray-500",
  };
  return colorMap[type] || "text-gray-500";
}

// 格式化日期
function formatDate(dateStr?: string): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return dateStr;
  }
}

// 返回到 Business Unit 列表
function goBack() {
  store.clearSelectedAssetBundle();
  store.selectedBusinessUnit.value = null;
}

// 返回到 Business Unit 详情
function goToBusinessUnit() {
  store.clearSelectedAssetBundle();
}

// 获取 Asset 图标
function getAssetIcon(type: string) {
  const iconMap: Record<string, any> = {
    table: Table,
    volume: FolderOpen,
    agent: Bot,
    note: FileText,
  };
  return iconMap[type] || FileText;
}

// 获取 Asset 类型标签
function getAssetTypeLabel(type: string) {
  const labelMap: Record<string, string> = {
    table: 'Table',
    volume: 'Volume',
    agent: 'Agent',
    note: 'Note',
  };
  return labelMap[type] || type;
}

// 获取 Asset 类型样式
function getAssetTypeClass(type: string) {
  const classMap: Record<string, string> = {
    table: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    volume: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    agent: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    note: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
  };
  return classMap[type] || "bg-gray-100 text-gray-700";
}

// 确认删除 Asset Bundle
function confirmDeleteAssetBundle() {
  if (!selectedAssetBundle.value) return;
  deleteMessage.value = t('businessUnit.confirmDeleteAssetBundle', { name: selectedAssetBundle.value.name });
  deleteDescription.value = t('businessUnit.confirmDeleteAssetBundleDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedBusinessUnit.value || !selectedAssetBundle.value) return;
  
  // 如果有待删除的 Asset
  if (assetToDelete.value) {
    const success = await store.deleteAsset(
      selectedBusinessUnit.value.id, 
      selectedAssetBundle.value.name, 
      assetToDelete.value.name
    );
    if (success) {
      showDeleteDialog.value = false;
      assetToDelete.value = null;
    }
    return;
  }
  
  // 删除 Asset Bundle
  const success = await store.deleteAssetBundle(selectedBusinessUnit.value.id, selectedAssetBundle.value.name);
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedAssetBundle();
  }
}

// 更新 Asset Bundle
async function handleUpdateAssetBundle(businessUnitId: string, bundleName: string, data: AssetBundleUpdate) {
  const result = await store.updateAssetBundle(businessUnitId, bundleName, data);
  if (result) {
    showEditAssetBundleDialog.value = false;
  }
}

// 创建资产
function handleCreateAsset(type: string) {
  showCreateMenu.value = false;
  
  switch (type) {
    case 'volume':
      showCreateVolumeDialog.value = true;
      break;
    case 'table':
      // TODO: 打开创建 Table 弹窗
      console.log('Create Table - Not implemented yet');
      break;
    case 'function':
      // TODO: 打开创建 Function 弹窗
      console.log('Create Function - Not implemented yet');
      break;
    default:
      console.log(`Create ${type} - Not implemented yet`);
  }
}

// 创建 Volume
async function handleCreateVolume(businessUnitId: string, bundleName: string, data: AssetCreate) {
  const result = await store.createAsset(businessUnitId, bundleName, data);
  if (result) {
    showCreateVolumeDialog.value = false;
  }
}

// 同步元数据
async function handleSyncMetadata() {
  if (!selectedBusinessUnit.value || !selectedAssetBundle.value || selectedAssetBundle.value.bundle_type !== 'external') return;
  
  syncing.value = true;
  syncResult.value = null;
  
  try {
    const result = await assetBundleApi.sync(selectedBusinessUnit.value.id, selectedAssetBundle.value.name);
    syncResult.value = result;
    
    // 同步成功后刷新 Asset Bundle 数据
    if (result.success) {
      // 重新加载 business unit 以获取更新后的 asset bundle
      await store.fetchBusinessUnit(selectedBusinessUnit.value.id);
      // 重新加载 assets
      await store.fetchAssets(selectedBusinessUnit.value.id, selectedAssetBundle.value.name);
    }
  } catch (error) {
    console.error('Sync metadata failed:', error);
    syncResult.value = {
      success: false,
      schemas_synced: 0,
      tables_synced: 0,
      columns_synced: 0,
      errors: [error instanceof Error ? error.message : 'Unknown error'],
      warnings: [],
    };
  } finally {
    syncing.value = false;
  }
}

// 点击 Asset 行打开详情
function handleAssetClick(asset: Asset) {
  store.selectAsset(asset);
}

// 处理 Asset 行点击事件（ItemListCard）
function handleAssetRowClick(payload: { item: ItemType; index: number }) {
  const item = payload.item as Asset;
  handleAssetClick(item);
}

// 处理 Asset 操作事件（ItemListCard）
function handleAssetAction(payload: { column: ColumnConfig; item: ItemType; index: number; action: string }) {
  if (payload.action === 'delete') {
    const item = payload.item as Asset;
    confirmDeleteAsset(item);
  }
}

// 确认删除 Asset
const assetToDelete = ref<Asset | null>(null);

function confirmDeleteAsset(asset: Asset) {
  assetToDelete.value = asset;
  deleteMessage.value = t('detail.confirmDeleteAsset', { name: asset.name });
  deleteDescription.value = t('detail.confirmDeleteAssetDesc');
  showDeleteDialog.value = true;
}

// 监听 Asset Bundle 变化，重新加载配置
watch(selectedAssetBundle, () => {
  activeTab.value = 'overview';
  syncResult.value = null;
  loadConfig();
}, { immediate: true });
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.15s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
