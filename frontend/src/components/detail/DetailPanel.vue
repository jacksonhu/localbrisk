<template>
  <div class="detail-panel h-full flex flex-col">
    <!-- 未选中状态 -->
    <div v-if="!selectedBusinessUnit && !selectedAssetBundle && !selectedAsset && !selectedAgent && !selectedModel" class="h-full flex items-center justify-center p-6">
      <div class="text-center">
        <Folder class="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
        <p class="text-muted-foreground">{{ t('detail.selectBusinessUnit') }}</p>
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

    <!-- Asset Bundle 详情页 -->
    <AssetBundleDetailPanel 
      v-else-if="selectedAssetBundle" 
    />

    <!-- Business Unit 详情页 -->
    <div v-else-if="selectedBusinessUnit" class="h-full flex flex-col p-6">
      <!-- 面包屑导航 -->
      <div class="flex items-center gap-2 text-sm text-muted-foreground mb-4">
        <button 
          class="flex items-center gap-1 hover:text-foreground transition-colors"
          @click="goBack"
        >
          <ArrowLeft class="w-4 h-4" />
        </button>
        <span class="text-primary cursor-pointer hover:underline" @click="goBack">
          {{ t('detail.businessUnitExplorer') }}
        </span>
        <ChevronRight class="w-3 h-3" />
        <span>{{ selectedBusinessUnit.display_name || selectedBusinessUnit.name }}</span>
      </div>

      <!-- 标题区域 -->
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <Folder class="w-6 h-6 text-yellow-500" />
          <h1 class="text-2xl font-semibold">{{ selectedBusinessUnit.display_name || selectedBusinessUnit.name }}</h1>
          <!-- 修改和删除图标 -->
          <div class="flex items-center gap-1 ml-2">
            <button
              @click="showEditBusinessUnitDialog = true"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
              :title="t('businessUnit.editBusinessUnit')"
            >
              <Pencil class="w-4 h-4 text-muted-foreground hover:text-foreground" />
            </button>
            <button
              @click="confirmDeleteBusinessUnit"
              class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
              :title="t('businessUnit.deleteBusinessUnit')"
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
          v-for="tab in businessUnitTabs"
          :key="tab.id"
          @click="activeBusinessUnitTab = tab.id"
          class="px-4 py-2 text-sm font-medium transition-colors relative"
          :class="activeBusinessUnitTab === tab.id 
            ? 'text-primary' 
            : 'text-muted-foreground hover:text-foreground'"
        >
          <div class="flex items-center gap-2">
            <component :is="tab.icon" class="w-4 h-4" />
            {{ tab.label }}
          </div>
          <!-- 激活指示器 -->
          <div
            v-if="activeBusinessUnitTab === tab.id"
            class="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
          ></div>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <!-- 概览 Tab -->
        <template v-if="activeBusinessUnitTab === 'overview'">
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
                {{ selectedBusinessUnit.description || t('detail.noDescription') }}
              </p>
            </div>

            <!-- Business Unit 基本信息 -->
            <div class="card-float p-4">
              <h3 class="font-medium mb-4">{{ t('detail.businessUnitInfo') }}</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <label class="text-muted-foreground">{{ t('common.name') }}</label>
                  <p class="font-medium">{{ selectedBusinessUnit.name }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
                  <p class="font-medium">{{ formatDate(selectedBusinessUnit.created_at) }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('common.updatedAt') }}</label>
                  <p class="font-medium">{{ formatDate(selectedBusinessUnit.updated_at) }}</p>
                </div>
                <div>
                  <label class="text-muted-foreground">{{ t('info.assetBundlesCount') }}</label>
                  <p class="font-medium">{{ selectedBusinessUnit.asset_bundles?.length || 0 }}</p>
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
                    v-for="tag in selectedBusinessUnit.tags"
                    :key="tag"
                    class="px-2 py-1 text-xs bg-primary/10 text-primary rounded"
                >
                  {{ tag }}
                </span>
                <span v-if="!selectedBusinessUnit.tags?.length" class="text-sm text-muted-foreground">
                  {{ t('common.noData') }}
                </span>
              </div>
            </div>

            <!-- Asset Bundle 列表 -->
            <div class="card-float overflow-hidden">
              <div class="p-4 border-b border-border flex items-center justify-between">
                <h3 class="font-medium">Asset Bundles</h3>
                <span class="text-sm text-primary bg-primary/10 px-2 py-1 rounded">
                  {{ t('detail.assetBundlesCount', { count: filteredAssetBundles.length }) }}
                </span>
              </div>
              
              <!-- 搜索 -->
              <div class="p-4 border-b border-border">
                <div class="relative">
                  <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    v-model="assetBundleFilter"
                    type="text"
                    :placeholder="t('detail.filterAssetBundles')"
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

              <!-- Asset Bundle 行 -->
              <div v-if="filteredAssetBundles.length > 0">
                <div
                  v-for="bundle in filteredAssetBundles"
                  :key="bundle.id"
                  class="grid grid-cols-4 gap-4 text-sm px-4 py-3 border-b border-border last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                  @click="handleAssetBundleClick(bundle)"
                >
                  <div class="flex items-center gap-2">
                    <Database class="w-4 h-4 text-purple-500" />
                    <span class="font-medium">{{ bundle.name }}</span>
                    <HardDrive v-if="bundle.bundle_type === 'local'" class="w-3 h-3 text-green-500" />
                    <PlugZap v-else class="w-3 h-3 text-cyan-500" :title="bundle.connection?.type" />
                  </div>
                  <div class="flex items-center gap-1">
                    <span :class="bundle.bundle_type === 'local' ? 'text-green-600' : 'text-blue-600'">
                      {{ bundle.bundle_type === 'local' ? t('businessUnit.local') : t('businessUnit.external') }}
                    </span>
                  </div>
                  <span class="text-muted-foreground">{{ formatDate(bundle.created_at) }}</span>
                  <div class="flex items-center gap-2">
                    <button
                      @click.stop="confirmDeleteAssetBundle(bundle)"
                      class="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 transition-colors"
                      :title="t('businessUnit.deleteAssetBundle')"
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
                <p class="text-muted-foreground mb-4">{{ t('detail.noAssetBundles') }}</p>
                <button
                  @click="showCreateAssetBundleDialog = true"
                  class="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                >
                  {{ t('detail.createFirstAssetBundle') }}
                </button>
              </div>
            </div>
          </div>
        </template>

        <!-- 配置 Tab -->
        <div v-if="activeBusinessUnitTab === 'config'" class="flex-1">
          <ConfigEditor
            v-model="businessUnitConfigContent"
            :modified="businessUnitConfigModified"
            :saving="savingBusinessUnitConfig"
            @save="saveBusinessUnitConfig"
            @copy="copyBusinessUnitConfig"
          />
        </div>
      </div>
    </div>

    <!-- 创建 Asset Bundle 弹窗 -->
    <AssetBundleDialog
      :is-open="showCreateAssetBundleDialog"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      @close="showCreateAssetBundleDialog = false"
      @create="handleCreateAssetBundle"
    />

    <!-- 创建 Agent 弹窗 -->
    <CreateAgentDialog
      :is-open="showCreateAgentDialog"
      :business-unit-id="selectedBusinessUnit?.id || ''"
      @close="showCreateAgentDialog = false"
      @submit="handleCreateAgent"
    />

    <!-- 编辑 Business Unit 弹窗 -->
    <CreateBusinessUnitDialog
      :is-open="showEditBusinessUnitDialog"
      :business-unit="selectedBusinessUnit"
      @close="showEditBusinessUnitDialog = false"
      @update="handleUpdateBusinessUnit"
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
  Database, HardDrive, Trash2, FileText, FileCode, Bot, PlugZap
} from "lucide-vue-next";
import AssetBundleDialog from "@/components/catalog/AssetBundleDialog.vue";
import CreateAgentDialog from "@/components/catalog/CreateAgentDialog.vue";
import CreateBusinessUnitDialog from "@/components/catalog/CreateBusinessUnitDialog.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import ConfigEditor from "@/components/common/ConfigEditor.vue";
import AssetBundleDetailPanel from "@/components/detail/AssetBundleDetailPanel.vue";
import TableDetailPanel from "@/components/detail/TableDetailPanel.vue";
import VolumeDetailPanel from "@/components/detail/VolumeDetailPanel.vue";
import AgentDetailPanel from "@/components/detail/AgentDetailPanel.vue";
import ModelDetailPanel from "@/components/detail/ModelDetailPanel.vue";
import { useBusinessUnitStore } from "@/stores/businessUnitStore";
import { useConfigManager } from "@/composables/useConfigManager";
import { businessUnitApi } from "@/services/api";
import type { AssetBundle, AssetBundleCreate, BusinessUnitUpdate, AgentCreate } from "@/types/catalog";

const { t } = useI18n();
const store = useBusinessUnitStore();

// 使用 computed 保持响应式
const selectedBusinessUnit = computed(() => store.selectedBusinessUnit.value);
const selectedAssetBundle = computed(() => store.selectedAssetBundle.value);
const selectedAsset = computed(() => store.selectedAsset.value);
const selectedAgent = computed(() => store.selectedAgent.value);
const selectedModel = computed(() => store.selectedModel.value);

// Business Unit Tab 状态
const activeBusinessUnitTab = ref<'overview' | 'config'>('overview');

const businessUnitTabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
]);

// 使用配置管理器处理 Business Unit 配置
const businessUnitConfigManager = useConfigManager({
  type: 'business_unit',
  getConfigPath: () => {
    if (!selectedBusinessUnit.value?.path) return undefined;
    return `${selectedBusinessUnit.value.path}/config.yaml`;
  },
  loadConfig: async () => {
    if (!selectedBusinessUnit.value) return '';
    try {
      const response = await businessUnitApi.getConfig(selectedBusinessUnit.value.id);
      return response.content;
    } catch (e) {
      console.error('Failed to load business unit config:', e);
      return '';
    }
  },
  onSaved: async () => {
    // 刷新 business unit 数据
    if (selectedBusinessUnit.value) {
      await store.fetchBusinessUnit(selectedBusinessUnit.value.id);
    }
  },
});

// 解构配置管理器的状态和方法
const {
  configContent: businessUnitConfigContent,
  configModified: businessUnitConfigModified,
  savingConfig: savingBusinessUnitConfig,
  saveConfig: saveBusinessUnitConfig,
  copyConfig: copyBusinessUnitConfig,
  loadConfigContent: loadBusinessUnitConfig,
} = businessUnitConfigManager;

// 弹窗状态
const showCreateAssetBundleDialog = ref(false);
const showCreateAgentDialog = ref(false);
const showEditBusinessUnitDialog = ref(false);
const showDeleteDialog = ref(false);
const showCreateMenu = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');
const assetBundleToDelete = ref<AssetBundle | null>(null);
const deleteType = ref<'asset_bundle' | 'business_unit'>('asset_bundle');

// 创建菜单项
const createMenuItems = computed(() => [
  { 
    type: 'asset_bundle', 
    label: t('businessUnit.createAssetBundle'), 
    icon: Database, 
    iconColor: 'text-purple-500' 
  },
  { 
    type: 'agent', 
    label: t('businessUnit.createAgent'), 
    icon: Bot, 
    iconColor: 'text-orange-500' 
  },
]);

// Asset Bundle 筛选
const assetBundleFilter = ref('');

const filteredAssetBundles = computed(() => {
  const bundles = selectedBusinessUnit.value?.asset_bundles || [];
  if (!assetBundleFilter.value) return bundles;
  
  const filter = assetBundleFilter.value.toLowerCase();
  return bundles.filter(s => 
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
  store.selectedBusinessUnit.value = null;
}

// 点击 Asset Bundle 行打开详情
function handleAssetBundleClick(bundle: AssetBundle) {
  store.selectAssetBundle(selectedBusinessUnit.value!.id, bundle);
}

// 创建 Asset Bundle
async function handleCreateAssetBundle(businessUnitId: string, data: AssetBundleCreate) {
  const result = await store.createAssetBundle(businessUnitId, data);
  if (result) {
    showCreateAssetBundleDialog.value = false;
  }
}

// 处理创建菜单项点击
function handleCreateItem(type: string) {
  showCreateMenu.value = false;
  
  switch (type) {
    case 'asset_bundle':
      showCreateAssetBundleDialog.value = true;
      break;
    case 'agent':
      showCreateAgentDialog.value = true;
      break;
  }
}

// 创建 Agent
async function handleCreateAgent(businessUnitId: string, data: AgentCreate) {
  const result = await store.createAgent(businessUnitId, data);
  if (result) {
    showCreateAgentDialog.value = false;
  }
}

// 确认删除 Asset Bundle
function confirmDeleteAssetBundle(bundle: AssetBundle) {
  assetBundleToDelete.value = bundle;
  deleteType.value = 'asset_bundle';
  deleteMessage.value = t('businessUnit.confirmDeleteAssetBundle', { name: bundle.name });
  deleteDescription.value = t('businessUnit.confirmDeleteAssetBundleDesc');
  showDeleteDialog.value = true;
}

// 确认删除 Business Unit
function confirmDeleteBusinessUnit() {
  if (!selectedBusinessUnit.value) return;
  deleteType.value = 'business_unit';
  deleteMessage.value = t('businessUnit.confirmDeleteBusinessUnit', { name: selectedBusinessUnit.value.name });
  deleteDescription.value = t('businessUnit.confirmDeleteBusinessUnitDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (deleteType.value === 'asset_bundle') {
    if (!assetBundleToDelete.value || !selectedBusinessUnit.value) return;
    
    const success = await store.deleteAssetBundle(selectedBusinessUnit.value.id, assetBundleToDelete.value.name);
    if (success) {
      showDeleteDialog.value = false;
      assetBundleToDelete.value = null;
    }
  } else if (deleteType.value === 'business_unit') {
    if (!selectedBusinessUnit.value) return;
    
    const success = await store.deleteBusinessUnit(selectedBusinessUnit.value.id);
    if (success) {
      showDeleteDialog.value = false;
      store.selectedBusinessUnit.value = null;
    }
  }
}

// 更新 Business Unit
async function handleUpdateBusinessUnit(businessUnitId: string, data: BusinessUnitUpdate) {
  const result = await store.updateBusinessUnit(businessUnitId, data);
  if (result) {
    showEditBusinessUnitDialog.value = false;
  }
}

// 监听 Business Unit 变化
watch(selectedBusinessUnit, () => {
  activeBusinessUnitTab.value = 'overview';
  loadBusinessUnitConfig();
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
