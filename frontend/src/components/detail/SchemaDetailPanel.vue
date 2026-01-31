<template>
  <div v-if="selectedSchema" class="schema-detail-panel h-full flex flex-col p-6">
    <!-- 面包屑导航 -->
    <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4">
      <button 
        class="flex items-center gap-1 hover:text-foreground transition-colors"
        @click="goBack"
      >
        <ArrowLeft class="w-4 h-4" />
      </button>
      <span class="text-primary cursor-pointer hover:underline" @click="goToCatalog">
        {{ selectedCatalog?.display_name || selectedCatalog?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span>{{ selectedSchema?.name }}</span>
    </div>

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <Database class="w-6 h-6 text-purple-500" />
        <h1 class="text-2xl font-semibold">{{ selectedSchema.name }}</h1>
        <!-- 类型标识 -->
        <span 
          :class="selectedSchema.schema_type === 'local' 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'"
          class="px-2 py-0.5 text-xs rounded flex items-center gap-1"
        >
          <HardDrive v-if="selectedSchema.schema_type === 'local'" class="w-3 h-3" />
          <PlugZap v-else class="w-3 h-3" />
          {{ selectedSchema.schema_type === 'local' ? t('catalog.local') : t('catalog.external') }}
        </span>
        <!-- 连接类型标识 -->
        <span 
          v-if="selectedSchema.connection"
          class="px-2 py-0.5 text-xs bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400 rounded flex items-center gap-1"
        >
          {{ selectedSchema.connection.type.toUpperCase() }}
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="showEditSchemaDialog = true"
            class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            :title="t('catalog.editSchema')"
          >
            <Pencil class="w-4 h-4 text-muted-foreground hover:text-foreground" />
          </button>
          <button
            v-if="selectedSchema.schema_type === 'external'"
            @click="handleSyncMetadata"
            :disabled="syncing"
            class="p-1.5 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
            :title="t('detail.syncMetadata')"
          >
            <RefreshCw class="w-4 h-4 text-muted-foreground hover:text-blue-600" :class="{ 'animate-spin': syncing }" />
          </button>
          <button
            @click="confirmDeleteSchema"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('catalog.deleteSchema')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
      </div>
      <!-- 创建按钮 -->
      <div v-if="selectedSchema.schema_type=='local'" class="relative">
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
              @click="showEditSchemaDialog = true"
              class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center"
            >
              <Pencil class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
          <p class="text-muted-foreground text-sm">
            {{ selectedSchema.description || t('detail.noDescription') }}
          </p>
        </div>

        <!-- Schema 基本信息 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-4">{{ t('detail.schemaInfo') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('common.name') }}</label>
              <p class="font-medium">{{ selectedSchema.name }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('catalog.schemaType') }}</label>
              <p class="font-medium">
                {{ selectedSchema.schema_type === 'local' ? t('catalog.schemaTypeLocal') : t('catalog.schemaTypeExternal') }}
              </p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedSchema.created_at) }}</p>
            </div>
            <div v-if="selectedSchema.synced_at">
              <label class="text-muted-foreground">{{ t('detail.lastSyncedAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedSchema.synced_at) }}</p>
            </div>
            <div v-if="selectedSchema.path" class="col-span-2">
              <label class="text-muted-foreground">{{ t('common.path') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedSchema.path }}
              </p>
            </div>
          </div>
        </div>

        <!-- 数据库连接配置 (仅 External 类型显示) -->
        <div v-if="selectedSchema.schema_type === 'external' && selectedSchema.connection" class="card-float p-4">
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
              <p class="font-medium">{{ selectedSchema.connection.type.toUpperCase() }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('connection.database') }}</label>
              <p class="font-medium">{{ selectedSchema.connection.db_name }}</p>
            </div>
            <div v-if="selectedSchema.connection.host">
              <label class="text-muted-foreground">{{ t('connection.host') }}</label>
              <p class="font-medium">{{ selectedSchema.connection.host }}</p>
            </div>
            <div v-if="selectedSchema.connection.port">
              <label class="text-muted-foreground">{{ t('connection.port') }}</label>
              <p class="font-medium">{{ selectedSchema.connection.port }}</p>
            </div>
            <div v-if="selectedSchema.connection.username">
              <label class="text-muted-foreground">{{ t('connection.username') }}</label>
              <p class="font-medium">{{ selectedSchema.connection.username }}</p>
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
        <div class="card-float overflow-hidden">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h3 class="font-medium">{{ t('detail.assets') }}</h3>
            <span class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
              {{ t('detail.assetsCount', { count: filteredAssets.length }) }}
            </span>
          </div>
          
          <!-- 搜索 -->
          <div class="p-4 border-b border-border">
            <div class="relative">
              <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                v-model="assetFilter"
                type="text"
                :placeholder="t('detail.filterAssets')"
                class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background"
              />
            </div>
          </div>

          <!-- 表头 -->
          <div class="grid grid-cols-4 gap-4 text-sm font-medium text-muted-foreground border-b border-border px-4 py-3 bg-muted/30">
            <span>{{ t('common.name') }}</span>
            <span>{{ t('common.type') }}</span>
            <span>{{ t('common.createdAt') }}</span>
            <span>{{ t('common.actions') }}</span>
          </div>

          <!-- Asset 行 -->
          <div v-if="filteredAssets.length > 0">
            <div
              v-for="asset in filteredAssets"
              :key="asset.id"
              class="grid grid-cols-4 gap-4 text-sm px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
              @click="handleAssetClick(asset)"
            >
              <div class="flex items-center gap-2">
                <component :is="getAssetIcon(asset.asset_type)" class="w-4 h-4" :class="getAssetIconColor(asset.asset_type)" />
                <span class="font-medium truncate">{{ asset.name }}</span>
              </div>
              <div class="flex items-center">
                <span class="px-2 py-0.5 text-xs rounded" :class="getAssetTypeClass(asset.asset_type)">
                  {{ getAssetTypeLabel(asset.asset_type) }}
                </span>
              </div>
              <span class="text-muted-foreground">{{ formatDate(asset.created_at) }}</span>
              <div class="flex items-center gap-2">
                <button
                  @click.stop="confirmDeleteAsset(asset)"
                  class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition-colors"
                  :title="t('common.delete')"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="flex flex-col items-center justify-center py-12 text-center">
            <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
              <FolderOpen class="w-8 h-8 text-muted-foreground" />
            </div>
            <p class="text-muted-foreground">{{ t('detail.noAssets') }}</p>
          </div>
        </div>
      </div>

      <!-- 配置 Tab -->
      <div v-if="activeTab === 'config'" class="h-full">
        <div class="card-float h-full flex flex-col">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h3 class="font-medium flex items-center gap-2">
              <FileCode class="w-4 h-4" />
              {{ t('detail.configFile') }}
            </h3>
            <div class="flex items-center gap-2">
              <button
                @click="saveConfig"
                :disabled="!configModified || savingConfig"
                class="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Save class="w-4 h-4" />
                {{ t('common.save') }}
              </button>
              <button
                @click="copyConfig"
                class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2"
              >
                <Copy class="w-4 h-4" />
                {{ t('common.copy') }}
              </button>
            </div>
          </div>
          <div class="flex-1 p-4 overflow-hidden">
            <textarea
              v-model="configContent"
              class="w-full h-full font-mono text-sm bg-muted/50 border border-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
              spellcheck="false"
            ></textarea>
          </div>
        </div>
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

    <!-- 编辑 Schema 弹窗 -->
    <SchemaDialog
      :is-open="showEditSchemaDialog"
      :catalog-id="selectedCatalog?.id || ''"
      :schema="selectedSchema"
      @close="showEditSchemaDialog = false"
      @update="handleUpdateSchema"
    />

    <!-- 创建 Volume 弹窗 -->
    <CreateVolumeDialog
      :is-open="showCreateVolumeDialog"
      :catalog-id="selectedCatalog?.id || ''"
      :schema-name="selectedSchema?.name || ''"
      @close="showCreateVolumeDialog = false"
      @submit="handleCreateVolume"
    />

    <!-- 创建 Model 弹窗 -->
    <CreateModelDialog
      :is-open="showCreateModelDialog"
      :catalog-id="selectedCatalog?.id || ''"
      :schema-name="selectedSchema?.name || ''"
      @close="showCreateModelDialog = false"
      @submit="handleCreateModel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, ChevronDown, Database, Pencil, Search, 
  HardDrive, Trash2, Table, FolderOpen, Bot, FileText, Plus, Code, Cpu,
  FileCode, Save, Copy, PlugZap, RefreshCw, CheckCircle, XCircle
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import SchemaDialog from "@/components/catalog/SchemaDialog.vue";
import CreateVolumeDialog from "@/components/catalog/CreateVolumeDialog.vue";
import CreateModelDialog from "@/components/catalog/CreateModelDialog.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { schemaApi } from "@/services/api";
import type { SchemaUpdate, AssetCreate, Asset, ModelCreate, SyncResult } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// 使用 computed 保持响应式，直接从 store 获取
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedSchema = computed(() => store.selectedSchema.value);
const currentAssets = computed(() => store.currentAssets.value);

// Tab 状态
const activeTab = ref<'overview' | 'config'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// 配置内容
const configContent = ref('');
const originalConfig = ref('');
const savingConfig = ref(false);

const configModified = computed(() => configContent.value !== originalConfig.value);

// 同步状态
const syncing = ref(false);
const syncResult = ref<SyncResult | null>(null);

// 弹窗状态
const showDeleteDialog = ref(false);
const showEditSchemaDialog = ref(false);
const showCreateMenu = ref(false);
const showCreateVolumeDialog = ref(false);
const showCreateModelDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 创建菜单项
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
  { 
    type: 'model', 
    label: t('asset.createModel'), 
    icon: Cpu, 
    iconColor: 'text-orange-500' 
  },
]);

// Asset 筛选
const assetFilter = ref('');

const filteredAssets = computed(() => {
  const assets = currentAssets.value || [];
  if (!assetFilter.value) return assets;
  
  const filter = assetFilter.value.toLowerCase();
  return assets.filter(a => 
    a.name.toLowerCase().includes(filter)
  );
});

// 加载配置 - 从后端获取 schema.yaml 文件原始内容
async function loadConfig() {
  if (!selectedCatalog.value || !selectedSchema.value) {
    configContent.value = '';
    originalConfig.value = '';
    return;
  }
  
  try {
    const response = await schemaApi.getConfig(selectedCatalog.value.id, selectedSchema.value.name);
    configContent.value = response.content;
    originalConfig.value = response.content;
  } catch (e) {
    console.error('Failed to load schema config:', e);
    configContent.value = '';
    originalConfig.value = '';
  }
}

// 保存配置
async function saveConfig() {
  savingConfig.value = true;
  try {
    // TODO: 调用后端 API 保存配置
    console.log('Save config:', configContent.value);
    originalConfig.value = configContent.value;
  } finally {
    savingConfig.value = false;
  }
}

// 复制配置
async function copyConfig() {
  try {
    await navigator.clipboard.writeText(configContent.value);
    // TODO: 显示复制成功提示
  } catch (e) {
    console.error('Failed to copy:', e);
  }
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

// 返回到 Catalog 列表
function goBack() {
  store.clearSelectedSchema();
  store.selectedCatalog.value = null;
}

// 返回到 Catalog 详情
function goToCatalog() {
  store.clearSelectedSchema();
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

// 确认删除 Schema
function confirmDeleteSchema() {
  if (!selectedSchema.value) return;
  deleteMessage.value = t('catalog.confirmDeleteSchema', { name: selectedSchema.value.name });
  deleteDescription.value = t('catalog.confirmDeleteSchemaDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedCatalog.value || !selectedSchema.value) return;
  
  // 如果有待删除的 Asset
  if (assetToDelete.value) {
    const success = await store.deleteAsset(
      selectedCatalog.value.id, 
      selectedSchema.value.name, 
      assetToDelete.value.name
    );
    if (success) {
      showDeleteDialog.value = false;
      assetToDelete.value = null;
    }
    return;
  }
  
  // 删除 Schema
  const success = await store.deleteSchema(selectedCatalog.value.id, selectedSchema.value.name);
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedSchema();
  }
}

// 更新 Schema
async function handleUpdateSchema(catalogId: string, schemaName: string, data: SchemaUpdate) {
  const result = await store.updateSchema(catalogId, schemaName, data);
  if (result) {
    showEditSchemaDialog.value = false;
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
    case 'model':
      showCreateModelDialog.value = true;
      break;
    default:
      console.log(`Create ${type} - Not implemented yet`);
  }
}

// 创建 Volume
async function handleCreateVolume(catalogId: string, schemaName: string, data: AssetCreate) {
  const result = await store.createAsset(catalogId, schemaName, data);
  if (result) {
    showCreateVolumeDialog.value = false;
  }
}

// 创建 Model
async function handleCreateModel(catalogId: string, schemaName: string, data: ModelCreate) {
  const result = await store.createModel(catalogId, schemaName, data);
  if (result) {
    showCreateModelDialog.value = false;
  }
}

// 同步元数据
async function handleSyncMetadata() {
  if (!selectedCatalog.value || !selectedSchema.value || selectedSchema.value.schema_type !== 'external') return;
  
  syncing.value = true;
  syncResult.value = null;
  
  try {
    const result = await schemaApi.sync(selectedCatalog.value.id, selectedSchema.value.name);
    syncResult.value = result;
    
    // 同步成功后刷新 Schema 数据
    if (result.success) {
      // 重新加载 catalog 以获取更新后的 schema
      await store.fetchCatalog(selectedCatalog.value.id);
      // 重新加载 assets
      await store.fetchAssets(selectedCatalog.value.id, selectedSchema.value.name);
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

// 确认删除 Asset
const assetToDelete = ref<Asset | null>(null);

function confirmDeleteAsset(asset: Asset) {
  assetToDelete.value = asset;
  deleteMessage.value = t('detail.confirmDeleteAsset', { name: asset.name });
  deleteDescription.value = t('detail.confirmDeleteAssetDesc');
  showDeleteDialog.value = true;
}

// 监听 Schema 变化，重新加载配置
watch(selectedSchema, () => {
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
