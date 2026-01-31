<template>
  <div class="table-detail-panel h-full flex flex-col p-6">
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
      <span class="text-primary cursor-pointer hover:underline" @click="goToSchema">
        {{ selectedSchema?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span>{{ selectedAsset?.name }}</span>
    </div>

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <Table class="w-6 h-6 text-blue-500" />
        <h1 class="text-2xl font-semibold">{{ selectedAsset?.name }}</h1>
        <!-- 类型标识 -->
        <span class="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded">
          Table
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="confirmDeleteTable"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('tableDetail.deleteTable')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
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
              @click="editDescription"
              class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center"
            >
              <Pencil class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
          <p class="text-muted-foreground text-sm">
            {{ tableDescription || t('detail.noDescription') }}
          </p>
        </div>

        <!-- 表基本信息 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-4">{{ t('tableDetail.tableInfo') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('common.name') }}</label>
              <p class="font-medium">{{ selectedAsset?.name }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('tableDetail.format') }}</label>
              <p class="font-medium uppercase">{{ tableFormat || '-' }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedAsset?.created_at) }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('tableDetail.columnCount') }}</label>
              <p class="font-medium">{{ tableColumns.length }} {{ t('tableDetail.columns') }}</p>
            </div>
            <div v-if="selectedAsset?.path" class="col-span-2">
              <label class="text-muted-foreground">{{ t('common.path') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedAsset.path }}
              </p>
            </div>
          </div>
        </div>

        <!-- 表字段列表 -->
        <div class="card-float overflow-hidden">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h3 class="font-medium">{{ t('tableDetail.columns') }}</h3>
            <span class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
              {{ tableColumns.length }} {{ t('tableDetail.columnsCount') }}
            </span>
          </div>
          
          <!-- 搜索 -->
          <div class="p-4 border-b border-border">
            <div class="relative">
              <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                v-model="columnFilter"
                type="text"
                :placeholder="t('tableDetail.filterColumns')"
                class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background"
              />
            </div>
          </div>

          <!-- 表头 -->
          <div class="grid grid-cols-4 gap-4 text-sm font-medium text-muted-foreground border-b border-border px-4 py-3 bg-muted/30">
            <span>{{ t('tableDetail.columnName') }}</span>
            <span>{{ t('tableDetail.dataType') }}</span>
            <span>{{ t('tableDetail.nullable') }}</span>
            <span>{{ t('common.description') }}</span>
          </div>

          <!-- 字段行 -->
          <div v-if="filteredColumns.length > 0">
            <div
              v-for="(column, index) in filteredColumns"
              :key="column.name"
              class="grid grid-cols-4 gap-4 text-sm px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
            >
              <div class="flex items-center gap-2">
                <span class="w-6 h-6 flex items-center justify-center text-xs text-muted-foreground bg-muted rounded">
                  {{ index + 1 }}
                </span>
                <span class="font-medium font-mono">{{ column.name }}</span>
              </div>
              <div class="flex items-center">
                <span class="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 font-mono">
                  {{ column.type }}
                </span>
              </div>
              <div class="flex items-center">
                <span v-if="column.nullable" class="text-green-600">{{ t('common.yes') }}</span>
                <span v-else class="text-red-600">{{ t('common.no') }}</span>
              </div>
              <span class="text-muted-foreground truncate" :title="column.description">
                {{ column.description || '-' }}
              </span>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="flex flex-col items-center justify-center py-12 text-center">
            <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
              <Table class="w-8 h-8 text-muted-foreground" />
            </div>
            <p class="text-muted-foreground">{{ t('tableDetail.noColumns') }}</p>
          </div>
        </div>
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

      <!-- 数据预览 Tab -->
      <div v-if="activeTab === 'preview'" class="h-full flex flex-col">
        <div class="card-float flex-1 flex flex-col overflow-hidden">
          <!-- 工具栏 -->
          <div class="p-4 border-b border-border flex items-center justify-between">
            <div class="flex items-center gap-2">
              <h3 class="font-medium flex items-center gap-2">
                <Database class="w-4 h-4" />
                {{ t('tableDetail.dataPreview') }}
              </h3>
              <span v-if="previewData" class="text-sm text-muted-foreground">
                ({{ t('tableDetail.totalRows', { count: previewData.total }) }})
              </span>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="loadPreviewData()"
                :disabled="previewLoading"
                class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw :class="['w-4 h-4', previewLoading && 'animate-spin']" />
                {{ t('common.refresh') }}
              </button>
            </div>
          </div>

          <!-- 加载状态 -->
          <div v-if="previewLoading" class="flex-1 flex items-center justify-center">
            <div class="text-center">
              <Loader2 class="w-8 h-8 animate-spin text-primary mx-auto mb-2" />
              <p class="text-muted-foreground">{{ t('common.loading') }}</p>
            </div>
          </div>

          <!-- 错误状态 -->
          <div v-else-if="previewError" class="flex-1 flex items-center justify-center">
            <div class="text-center max-w-md">
              <AlertCircle class="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p class="text-foreground font-medium mb-2">{{ t('tableDetail.previewError') }}</p>
              <p class="text-sm text-muted-foreground mb-4">{{ previewError }}</p>
              <button
                @click="loadPreviewData()"
                class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                {{ t('common.retry') }}
              </button>
            </div>
          </div>

          <!-- 数据表格 -->
          <div v-else-if="previewData && previewData.rows.length > 0" class="flex-1 overflow-auto">
            <table class="w-full text-sm">
              <thead class="bg-muted/50 sticky top-0">
                <tr>
                  <th class="px-4 py-3 text-left font-medium text-muted-foreground border-b border-border w-12">#</th>
                  <th 
                    v-for="col in previewData.columns" 
                    :key="col"
                    class="px-4 py-3 text-left font-medium text-muted-foreground border-b border-border whitespace-nowrap"
                  >
                    {{ col }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="(row, rowIndex) in previewData.rows" 
                  :key="rowIndex"
                  class="hover:bg-muted/30 transition-colors"
                >
                  <td class="px-4 py-2 border-b border-border text-muted-foreground">
                    {{ previewData.offset + rowIndex + 1 }}
                  </td>
                  <td 
                    v-for="col in previewData.columns" 
                    :key="col"
                    class="px-4 py-2 border-b border-border font-mono text-xs max-w-xs truncate"
                    :title="String(row[col] ?? '')"
                  >
                    <span v-if="row[col] === null" class="text-muted-foreground italic">NULL</span>
                    <span v-else>{{ formatCellValue(row[col]) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 空数据 -->
          <div v-else-if="previewData && previewData.rows.length === 0" class="flex-1 flex items-center justify-center">
            <div class="text-center">
              <Table class="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p class="text-muted-foreground">{{ t('viewer.noData') }}</p>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="previewData && previewData.total > 0" class="p-4 border-t border-border flex items-center justify-between">
            <div class="text-sm text-muted-foreground">
              {{ t('viewer.showing') }} {{ previewData.offset + 1 }}-{{ Math.min(previewData.offset + previewData.rows.length, previewData.total) }} {{ t('viewer.of') }} {{ previewData.total }}
            </div>
            <div class="flex items-center gap-2">
              <button
                @click="prevPage"
                :disabled="previewData.offset === 0"
                class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ t('common.previous') }}
              </button>
              <button
                @click="nextPage"
                :disabled="previewData.offset + previewData.limit >= previewData.total"
                class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ t('common.next') }}
              </button>
            </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, Table, Pencil, Search, 
  Trash2, FileText, FileCode, Database,
  RefreshCw, Loader2, AlertCircle
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import ConfigEditor from "@/components/common/ConfigEditor.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import { useConfigManager } from "@/composables/useConfigManager";
import { assetApi, type TablePreviewResult } from "@/services/api";
import type { Column } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedSchema = computed(() => store.selectedSchema.value);
const selectedAsset = computed(() => store.selectedAsset.value);

// Tab 状态
const activeTab = ref<'overview' | 'config' | 'preview'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'preview' as const, label: t('tableDetail.dataPreview'), icon: Database },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// 表信息
const tableDescription = computed(() => {
  return selectedAsset.value?.metadata?.description || '';
});

const tableFormat = computed(() => {
  return selectedAsset.value?.metadata?.format || 'parquet';
});

const tableColumns = computed<Column[]>(() => {
  const columns = selectedAsset.value?.metadata?.columns || [];
  // 映射字段名：后端返回 data_type，前端使用 type
  return columns.map((col: any) => ({
    name: col.name,
    type: col.data_type || col.type || '',
    nullable: col.nullable ?? true,
    description: col.comment || col.description || '',
  }));
});

// 字段筛选
const columnFilter = ref('');

const filteredColumns = computed(() => {
  if (!columnFilter.value) return tableColumns.value;
  
  const filter = columnFilter.value.toLowerCase();
  return tableColumns.value.filter(c => 
    c.name.toLowerCase().includes(filter) ||
    c.type.toLowerCase().includes(filter)
  );
});

// 使用配置管理器处理 Asset 配置
const assetConfigManager = useConfigManager({
  type: 'asset',
  getConfigPath: () => {
    if (!selectedAsset.value?.path) return undefined;
    return selectedAsset.value.path;
  },
  loadConfig: async () => {
    if (!selectedCatalog.value || !selectedSchema.value || !selectedAsset.value) return '';
    try {
      const response = await assetApi.getConfig(
        selectedCatalog.value.id,
        selectedSchema.value.name,
        selectedAsset.value.name
      );
      return response.content;
    } catch (e) {
      console.error('Failed to load asset config:', e);
      return '';
    }
  },
  onSaved: async () => {
    // 刷新 asset 数据
    if (selectedCatalog.value && selectedSchema.value) {
      await store.fetchAssets(selectedCatalog.value.id, selectedSchema.value.name);
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
} = assetConfigManager;

// 弹窗状态
const showDeleteDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// 数据预览状态
const previewData = ref<TablePreviewResult | null>(null);
const previewLoading = ref(false);
const previewError = ref<string | null>(null);
const previewPageSize = 100;

// 判断是否支持数据预览（仅外部连接的表支持）
const canPreview = computed(() => {
  return selectedAsset.value?.metadata?.source === 'connection';
});

// 加载数据预览
async function loadPreviewData(offset: number = 0) {
  if (!selectedCatalog.value || !selectedSchema.value || !selectedAsset.value) return;
  
  previewLoading.value = true;
  previewError.value = null;
  
  try {
    // 从 metadata 中提取 schema_name
    const schemaName = selectedAsset.value.metadata?.schema_name || selectedSchema.value.name;
    
    previewData.value = await assetApi.previewTableData(
      selectedCatalog.value.id,
      schemaName,
      selectedAsset.value.name,
      previewPageSize,
      offset
    );
  } catch (e: any) {
    console.error('Failed to load preview data:', e);
    previewError.value = e.message || t('tableDetail.previewError');
    previewData.value = null;
  } finally {
    previewLoading.value = false;
  }
}

// 分页
function prevPage() {
  if (!previewData.value || previewData.value.offset === 0) return;
  loadPreviewData(Math.max(0, previewData.value.offset - previewPageSize));
}

function nextPage() {
  if (!previewData.value) return;
  const nextOffset = previewData.value.offset + previewPageSize;
  if (nextOffset < previewData.value.total) {
    loadPreviewData(nextOffset);
  }
}

// 格式化单元格值
function formatCellValue(value: any): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  const str = String(value);
  // 截断过长的值
  return str.length > 100 ? str.substring(0, 100) + '...' : str;
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

// 返回
function goBack() {
  store.clearSelectedAsset();
}

// 返回到 Catalog
function goToCatalog() {
  store.clearSelectedAsset();
  store.clearSelectedSchema();
}

// 返回到 Schema
function goToSchema() {
  store.clearSelectedAsset();
}

// 编辑描述
function editDescription() {
  // TODO: 实现编辑描述功能
  console.log('Edit description - Not implemented yet');
}

// 确认删除 Table
function confirmDeleteTable() {
  if (!selectedAsset.value) return;
  deleteMessage.value = t('tableDetail.confirmDeleteTable', { name: selectedAsset.value.name });
  deleteDescription.value = t('tableDetail.confirmDeleteTableDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedCatalog.value || !selectedSchema.value || !selectedAsset.value) return;
  
  const success = await store.deleteAsset(
    selectedCatalog.value.id, 
    selectedSchema.value.name, 
    selectedAsset.value.name
  );
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedAsset();
  }
}

// 监听资产变化重置 tab 和加载配置
watch(selectedAsset, () => {
  activeTab.value = 'overview';
  columnFilter.value = '';
  loadConfig();
  // 重置预览数据
  previewData.value = null;
  previewError.value = null;
}, { immediate: true });

// 监听 Tab 切换，懒加载预览数据
watch(activeTab, (newTab) => {
  if (newTab === 'preview' && !previewData.value && !previewLoading.value && canPreview.value) {
    loadPreviewData();
  }
});
</script>

<style scoped>
</style>
