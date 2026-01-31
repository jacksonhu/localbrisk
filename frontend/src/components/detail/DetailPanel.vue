<template>
  <div class="detail-panel h-full flex flex-col">
    <!-- 未选中状态 -->
    <div v-if="!selectedCatalog && !selectedSchema && !selectedAsset && !selectedAgent && !selectedModel" class="h-full flex items-center justify-center p-6">
      <div class="text-center">
        <Folder class="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
        <p class="text-muted-foreground">{{ t('detail.selectCatalog') }}</p>
      </div>
    </div>

    <!-- Model 详情页 -->
    <ModelDetailPanel 
      v-else-if="selectedModel" 
    />

    <!-- Agent 详情页 -->
    <AgentDetailPanel 
      v-else-if="selectedAgent" 
    />

    <!-- Asset 详情页 -->
    <TableDetailPanel 
      v-else-if="selectedAsset && selectedAsset.asset_type === 'table'" 
    />
    
    <VolumeDetailPanel 
      v-else-if="selectedAsset && selectedAsset.asset_type === 'volume'" 
    />

    <!-- Schema 详情页 -->
    <SchemaDetailPanel 
      v-else-if="selectedSchema" 
    />

    <!-- Catalog 详情页 -->
    <div v-else-if="selectedCatalog" class="h-full flex flex-col p-6">
      <!-- 面包屑导航 -->
      <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4">
        <button 
          class="flex items-center gap-1 hover:text-foreground transition-colors"
          @click="goBack"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <span class="text-primary cursor-pointer hover:underline" @click="goBack">
          {{ t('detail.catalogExplorer') }}
        </span>
        <ChevronRight class="w-3 h-3" />
        <span>{{ selectedCatalog.display_name || selectedCatalog.name }}</span>
      </div>

      <!-- 标题区域 -->
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <Folder class="w-6 h-6 text-yellow-500" />
          <h1 class="text-2xl font-semibold">{{ selectedCatalog.display_name || selectedCatalog.name }}</h1>
          <!-- 修改和删除图标 -->
          <div class="flex items-center gap-1 ml-2">
            <button
              @click="showEditCatalogDialog = true"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
              :title="t('catalog.editCatalog')"
            >
              <Pencil class="w-4 h-4 text-muted-foreground hover:text-foreground" />
            </button>
            <button
              @click="confirmDeleteCatalog"
              class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              :title="t('catalog.deleteCatalog')"
            >
              <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
            </button>
          </div>
        </div>
        
        <!-- 操作按钮 -->
        <div class="flex items-center gap-2 relative">
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
                @click="handleCreateItem(item.type)"
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
          v-for="tab in catalogTabs"
          :key="tab.id"
          @click="activeCatalogTab = tab.id"
          class="px-4 py-2 text-sm font-medium transition-colors relative"
          :class="activeCatalogTab === tab.id 
            ? 'text-primary' 
            : 'text-muted-foreground hover:text-foreground'"
        >
          <div class="flex items-center gap-2">
            <component :is="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </div>
          <!-- 激活指示器 -->
          <div
            v-if="activeCatalogTab === tab.id"
            class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
          ></div>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <!-- 概览 Tab -->
        <template v-if="activeCatalogTab === 'overview'">
          <div class="flex-1 overflow-y-auto space-y-6">
            <!-- 描述卡片 -->
            <div class="card-float p-4">
              <div class="flex items-center justify-between mb-2">
                <h3 class="font-medium">{{ t('common.description') }}</h3>
                <button class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center">
                  <Pencil class="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
              <p class="text-muted-foreground text-sm">
                {{ selectedCatalog.description || t('detail.noDescription') }}
              </p>
            </div>

            <!-- Catalog 基本信息 -->
            <div class="card-float p-4">
              <h3 class="font-medium mb-4">{{ t('detail.catalogInfo') }}</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <label class="text-muted-foreground">{{ t('common.name') }}</label>
                  <p class="font-medium">{{ selectedCatalog.name }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
                  <p class="font-medium">{{ formatDate(selectedCatalog.created_at) }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('common.updatedAt') }}</label>
                  <p class="font-medium">{{ formatDate(selectedCatalog.updated_at) }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('info.schemasCount') }}</label>
                  <p class="font-medium">{{ selectedCatalog.schemas?.length || 0 }}</p>
                </div>
              </div>
            </div>

            <!-- 标签 -->
            <div class="card-float p-4">
              <div class="flex items-center justify-between mb-3">
                <h3 class="font-medium">{{ t('common.tags') }}</h3>
                <button class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center">
                  <Plus class="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
              <div class="flex flex-wrap gap-2">
                <span
                    v-for="tag in selectedCatalog.tags"
                    :key="tag"
                    class="px-2 py-1 text-xs bg-primary/10 text-primary rounded"
                >
                  {{ tag }}
                </span>
                <span v-if="!selectedCatalog.tags?.length" class="text-sm text-muted-foreground">
                  {{ t('common.noData') }}
                </span>
              </div>
            </div>

            <!-- Schema 列表 -->
            <div class="card-float overflow-hidden">
              <div class="p-4 border-b border-border flex items-center justify-between">
                <h3 class="font-medium">Schemas</h3>
                <span class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
                  {{ t('detail.schemasCount', { count: filteredSchemas.length }) }}
                </span>
              </div>
              
              <!-- 搜索 -->
              <div class="p-4 border-b border-border">
                <div class="relative">
                  <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    v-model="schemaFilter"
                    type="text"
                    :placeholder="t('detail.filterSchemas')"
                    class="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background"
                  />
                </div>
              </div>

              <!-- 表头 -->
              <div class="grid grid-cols-4 gap-4 text-sm font-medium text-muted-foreground border-b border-border px-4 py-3 bg-muted/30">
                <span>{{ t('common.name') }}</span>
                <span>{{ t('detail.source') }}</span>
                <span>{{ t('common.createdAt') }}</span>
                <span>{{ t('common.actions') }}</span>
              </div>

              <!-- Schema 行 -->
              <div v-if="filteredSchemas.length > 0">
                <div
                  v-for="schema in filteredSchemas"
                  :key="schema.id"
                  class="grid grid-cols-4 gap-4 text-sm px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                  @click="handleSchemaClick(schema)"
                >
                  <div class="flex items-center gap-2">
                    <Database class="w-4 h-4 text-purple-500" />
                    <span class="font-medium">{{ schema.name }}</span>
                    <HardDrive v-if="schema.schema_type === 'local'" class="w-3 h-3 text-green-500" />
                    <PlugZap v-else class="w-3 h-3 text-cyan-500" :title="schema.connection?.type" />
                  </div>
                  <div class="flex items-center gap-1">
                    <span :class="schema.schema_type === 'local' ? 'text-green-600' : 'text-blue-600'">
                      {{ schema.schema_type === 'local' ? t('catalog.local') : t('catalog.external') }}
                    </span>
                  </div>
                  <span class="text-muted-foreground">{{ formatDate(schema.created_at) }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      @click.stop="confirmDeleteSchema(schema)"
                      class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition-colors"
                      :title="t('catalog.deleteSchema')"
                    >
                      <Trash2 class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-else class="flex flex-col items-center justify-center py-12 text-center">
                <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
                  <Database class="w-8 h-8 text-muted-foreground" />
                </div>
                <p class="text-muted-foreground mb-4">{{ t('detail.noSchemas') }}</p>
                <button
                  @click="showCreateSchemaDialog = true"
                  class="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  {{ t('detail.createFirstSchema') }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- 配置 Tab -->
        <div v-if="activeCatalogTab === 'config'" class="flex-1">
          <div class="card-float h-full flex flex-col">
            <div class="p-4 border-b border-border flex items-center justify-between">
              <h3 class="font-medium flex items-center gap-2">
                <FileCode class="w-4 h-4" />
                {{ t('detail.configFile') }}
              </h3>
              <div class="flex items-center gap-2">
                <button
                  @click="saveCatalogConfig"
                  :disabled="!catalogConfigModified || savingCatalogConfig"
                  class="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <Save class="w-4 h-4" />
                  {{ t('common.save') }}
                </button>
                <button
                  @click="copyCatalogConfig"
                  class="px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-muted transition-colors flex items-center gap-2"
                >
                  <Copy class="w-4 h-4" />
                  {{ t('common.copy') }}
                </button>
              </div>
            </div>
            <div class="flex-1 p-4 overflow-hidden">
              <textarea
                v-model="catalogConfigContent"
                class="w-full h-full font-mono text-sm bg-muted/50 border border-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                spellcheck="false"
              ></textarea>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建 Schema 弹窗 -->
    <SchemaDialog
      :is-open="showCreateSchemaDialog"
      :catalog-id="selectedCatalog?.id || ''"
      @close="showCreateSchemaDialog = false"
      @create="handleCreateSchema"
    />

    <!-- 创建 Agent 弹窗 -->
    <CreateAgentDialog
      :is-open="showCreateAgentDialog"
      :catalog-id="selectedCatalog?.id || ''"
      @close="showCreateAgentDialog = false"
      @submit="handleCreateAgent"
    />

    <!-- 编辑 Catalog 弹窗 -->
    <CreateCatalogDialog
      :is-open="showEditCatalogDialog"
      :catalog="selectedCatalog"
      @close="showEditCatalogDialog = false"
      @update="handleUpdateCatalog"
    />

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
  ArrowLeft, ChevronRight, ChevronDown, Folder, Pencil, Search, Plus, 
  Database, HardDrive, Trash2, FileText, FileCode, Save, Copy, Bot, PlugZap
} from "lucide-vue-next";
import SchemaDialog from "@/components/catalog/SchemaDialog.vue";
import CreateAgentDialog from "@/components/catalog/CreateAgentDialog.vue";
import CreateCatalogDialog from "@/components/catalog/CreateCatalogDialog.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import SchemaDetailPanel from "@/components/detail/SchemaDetailPanel.vue";
import TableDetailPanel from "@/components/detail/TableDetailPanel.vue";
import VolumeDetailPanel from "@/components/detail/VolumeDetailPanel.vue";
import AgentDetailPanel from "@/components/detail/AgentDetailPanel.vue";
import ModelDetailPanel from "@/components/detail/ModelDetailPanel.vue";
import { useCatalogStore } from "@/stores/catalogStore";
import type { Schema, SchemaCreate, CatalogUpdate, AgentCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useCatalogStore();

// 使用 computed 保持响应式
const selectedCatalog = computed(() => store.selectedCatalog.value);
const selectedSchema = computed(() => store.selectedSchema.value);
const selectedAsset = computed(() => store.selectedAsset.value);
const selectedAgent = computed(() => store.selectedAgent.value);
const selectedModel = computed(() => store.selectedModel.value);

// Catalog Tab 状态
const activeCatalogTab = ref<'overview' | 'config'>('overview');

const catalogTabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// 配置内容
const catalogConfigContent = ref('');
const originalCatalogConfig = ref('');
const savingCatalogConfig = ref(false);

const catalogConfigModified = computed(() => catalogConfigContent.value !== originalCatalogConfig.value);

// 弹窗状态
const showCreateSchemaDialog = ref(false);
const showCreateAgentDialog = ref(false);
const showEditCatalogDialog = ref(false);
const showDeleteDialog = ref(false);
const showCreateMenu = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');
const schemaToDelete = ref<Schema | null>(null);
const deleteType = ref<'schema' | 'catalog'>('schema');

// 创建菜单项
const createMenuItems = computed(() => [
  { 
    type: 'schema', 
    label: t('catalog.createSchema'), 
    icon: Database, 
    iconColor: 'text-purple-500' 
  },
  { 
    type: 'agent', 
    label: t('catalog.createAgent'), 
    icon: Bot, 
    iconColor: 'text-orange-500' 
  },
]);

// Schema 筛选
const schemaFilter = ref('');

const filteredSchemas = computed(() => {
  const schemas = selectedCatalog.value?.schemas || [];
  if (!schemaFilter.value) return schemas;
  
  const filter = schemaFilter.value.toLowerCase();
  return schemas.filter(s => 
    s.name.toLowerCase().includes(filter)
  );
});

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
  store.selectedCatalog.value = null;
}

// 点击 Schema 行打开详情
function handleSchemaClick(schema: Schema) {
  store.selectSchema(selectedCatalog.value!.id, schema);
}

// 创建 Schema
async function handleCreateSchema(catalogId: string, data: SchemaCreate) {
  const result = await store.createSchema(catalogId, data);
  if (result) {
    showCreateSchemaDialog.value = false;
  }
}

// 处理创建菜单项点击
function handleCreateItem(type: string) {
  showCreateMenu.value = false;
  
  switch (type) {
    case 'schema':
      showCreateSchemaDialog.value = true;
      break;
    case 'agent':
      showCreateAgentDialog.value = true;
      break;
  }
}

// 创建 Agent
async function handleCreateAgent(catalogId: string, data: AgentCreate) {
  const result = await store.createAgent(catalogId, data);
  if (result) {
    showCreateAgentDialog.value = false;
  }
}

// 确认删除 Schema
function confirmDeleteSchema(schema: Schema) {
  schemaToDelete.value = schema;
  deleteType.value = 'schema';
  deleteMessage.value = t('catalog.confirmDeleteSchema', { name: schema.name });
  deleteDescription.value = t('catalog.confirmDeleteSchemaDesc');
  showDeleteDialog.value = true;
}

// 确认删除 Catalog
function confirmDeleteCatalog() {
  if (!selectedCatalog.value) return;
  deleteType.value = 'catalog';
  deleteMessage.value = t('catalog.confirmDeleteCatalog', { name: selectedCatalog.value.name });
  deleteDescription.value = t('catalog.confirmDeleteCatalogDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (deleteType.value === 'schema') {
    if (!schemaToDelete.value || !selectedCatalog.value) return;
    
    const success = await store.deleteSchema(selectedCatalog.value.id, schemaToDelete.value.name);
    if (success) {
      showDeleteDialog.value = false;
      schemaToDelete.value = null;
    }
  } else if (deleteType.value === 'catalog') {
    if (!selectedCatalog.value) return;
    
    const success = await store.deleteCatalog(selectedCatalog.value.id);
    if (success) {
      showDeleteDialog.value = false;
      store.selectedCatalog.value = null;
    }
  }
}

// 更新 Catalog
async function handleUpdateCatalog(catalogId: string, data: CatalogUpdate) {
  const result = await store.updateCatalog(catalogId, data);
  if (result) {
    showEditCatalogDialog.value = false;
  }
}

// 生成 Catalog YAML 配置
function generateCatalogConfigYaml(): string {
  if (!selectedCatalog.value) return '';
  
  const catalog = selectedCatalog.value;
  const lines: string[] = [];
  
  lines.push(`name: ${catalog.name}`);
  if (catalog.display_name) {
    lines.push(`display_name: ${catalog.display_name}`);
  }
  if (catalog.description) {
    lines.push(`description: "${catalog.description}"`);
  }
  
  if (catalog.tags && catalog.tags.length > 0) {
    lines.push('tags:');
    catalog.tags.forEach(tag => {
      lines.push(`  - ${tag}`);
    });
  }
  
  if (catalog.schemas && catalog.schemas.length > 0) {
    lines.push('schemas:');
    catalog.schemas.forEach(schema => {
      lines.push(`  - name: ${schema.name}`);
      lines.push(`    schema_type: ${schema.schema_type}`);
      if (schema.connection) {
        lines.push(`    has_connection: true`);
      }
    });
  }
  
  lines.push(`created_at: ${catalog.created_at}`);
  if (catalog.updated_at) {
    lines.push(`updated_at: ${catalog.updated_at}`);
  }
  
  return lines.join('\n');
}

// 加载 Catalog 配置
function loadCatalogConfig() {
  const yaml = generateCatalogConfigYaml();
  catalogConfigContent.value = yaml;
  originalCatalogConfig.value = yaml;
}

// 保存 Catalog 配置
async function saveCatalogConfig() {
  savingCatalogConfig.value = true;
  try {
    // TODO: 调用后端 API 保存配置
    console.log('Save catalog config:', catalogConfigContent.value);
    originalCatalogConfig.value = catalogConfigContent.value;
  } finally {
    savingCatalogConfig.value = false;
  }
}

// 复制 Catalog 配置
async function copyCatalogConfig() {
  try {
    await navigator.clipboard.writeText(catalogConfigContent.value);
    // TODO: 显示复制成功提示
  } catch (e) {
    console.error('Failed to copy:', e);
  }
}

// 监听 Catalog 变化
watch(selectedCatalog, () => {
  activeCatalogTab.value = 'overview';
  loadCatalogConfig();
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
