<template>
  <div class="model-detail-panel h-full flex flex-col p-6">
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
      <span class="text-primary cursor-pointer hover:underline" @click="goToAgent">
        {{ selectedAgent?.name }}
      </span>
      <ChevronRight class="w-3 h-3" />
      <span>{{ selectedModel?.name }}</span>
    </div>

    <!-- 标题区域 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <Cpu class="w-6 h-6 text-orange-500" />
        <h1 class="text-2xl font-semibold">{{ selectedModel?.name }}</h1>
        <!-- 模型类型标签 -->
        <span 
          class="px-2 py-0.5 text-xs rounded"
          :class="selectedModel?.model_type === 'local' 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'"
        >
          {{ selectedModel?.model_type === 'local' ? t('model.localModel') : t('model.endpointModel') }}
        </span>
        <!-- 操作图标 -->
        <div class="flex items-center gap-1 ml-2">
          <button
            @click="showEditModelDialog = true"
            class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            :title="t('common.edit')"
          >
            <Pencil class="w-4 h-4 text-muted-foreground hover:text-foreground" />
          </button>
          <button
            @click="confirmDeleteModel"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            :title="t('common.delete')"
          >
            <Trash2 class="w-4 h-4 text-muted-foreground hover:text-red-600" />
          </button>
        </div>
      </div>
      <!-- 启用开关 -->
      <div class="flex items-center gap-3">
        <span class="text-sm text-muted-foreground">{{ t('model.enabledStatus') }}</span>
        <label class="relative inline-flex items-center cursor-pointer" :class="{ 'opacity-50 pointer-events-none': enablingModel }" @click.stop>
          <input
            type="checkbox"
            :checked="isModelEnabled"
            @change.stop="toggleModelEnabled"
            :disabled="enablingModel"
            class="sr-only peer"
          />
          <div class="w-11 h-6 bg-muted rounded-full peer-checked:bg-primary transition-colors"></div>
          <div class="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow peer-checked:translate-x-5 transition-transform"></div>
        </label>
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
              @click="showEditModelDialog = true"
              class="w-6 h-6 rounded hover:bg-muted flex items-center justify-center"
            >
              <Pencil class="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
          <p class="text-muted-foreground text-sm">
            {{ selectedModel?.description || t('detail.noDescription') }}
          </p>
        </div>

        <!-- Model 基本信息 -->
        <div class="card-float p-4">
          <h3 class="font-medium mb-4">{{ t('modelDetail.info') }}</h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <label class="text-muted-foreground">{{ t('common.name') }}</label>
              <p class="font-medium">{{ selectedModel?.name }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('model.modelType') }}</label>
              <p class="font-medium">
                {{ selectedModel?.model_type === 'local' ? t('model.localModel') : t('model.endpointModel') }}
              </p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('model.temperature') }}</label>
              <p class="font-medium">{{ selectedModel?.temperature ?? 0 }}</p>
            </div>
            <div>
              <label class="text-muted-foreground">{{ t('common.createdAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedModel?.created_at) }}</p>
            </div>
            <div v-if="selectedModel?.updated_at">
              <label class="text-muted-foreground">{{ t('common.updatedAt') }}</label>
              <p class="font-medium">{{ formatDate(selectedModel?.updated_at) }}</p>
            </div>
            <div v-if="selectedModel?.path" class="col-span-2">
              <label class="text-muted-foreground">{{ t('common.path') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedModel.path }}
              </p>
            </div>
          </div>
        </div>

        <!-- 本地模型配置 -->
        <div v-if="selectedModel?.model_type === 'local'" class="card-float p-4">
          <h3 class="font-medium mb-4 flex items-center gap-2">
            <HardDrive class="w-4 h-4" />
            {{ t('modelDetail.localConfig') }}
          </h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div v-if="selectedModel?.local_provider">
              <label class="text-muted-foreground">{{ t('model.localProvider') }}</label>
              <p class="font-medium">{{ formatProviderName(selectedModel.local_provider) }}</p>
            </div>
            <div v-if="selectedModel?.local_source">
              <label class="text-muted-foreground">{{ t('model.modelSource') }}</label>
              <p class="font-medium">
                {{ selectedModel.local_source === 'volume' ? t('model.volumeSource') : 'HuggingFace' }}
              </p>
            </div>
            <div v-if="selectedModel?.volume_reference" class="col-span-2">
              <label class="text-muted-foreground">{{ t('model.volumeReference') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1">
                {{ selectedModel.volume_reference }}
              </p>
            </div>
            <div v-if="selectedModel?.huggingface_repo" class="col-span-2">
              <label class="text-muted-foreground">{{ t('model.huggingfaceRepo') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1">
                {{ selectedModel.huggingface_repo }}
              </p>
            </div>
            <div v-if="selectedModel?.huggingface_filename">
              <label class="text-muted-foreground">{{ t('model.huggingfaceFilename') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1">
                {{ selectedModel.huggingface_filename }}
              </p>
            </div>
          </div>
        </div>

        <!-- API 端点配置 -->
        <div v-if="selectedModel?.model_type === 'endpoint'" class="card-float p-4">
          <h3 class="font-medium mb-4 flex items-center gap-2">
            <Cloud class="w-4 h-4" />
            {{ t('modelDetail.endpointConfig') }}
          </h3>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div v-if="selectedModel?.endpoint_provider">
              <label class="text-muted-foreground">{{ t('model.endpointProvider') }}</label>
              <p class="font-medium">{{ formatProviderName(selectedModel.endpoint_provider) }}</p>
            </div>
            <div v-if="selectedModel?.model_id">
              <label class="text-muted-foreground">{{ t('model.modelId') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1">
                {{ selectedModel.model_id }}
              </p>
            </div>
            <div v-if="selectedModel?.api_base_url" class="col-span-2">
              <label class="text-muted-foreground">{{ t('model.apiBaseUrl') }}</label>
              <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded mt-1 break-all">
                {{ selectedModel.api_base_url }}
              </p>
            </div>
            <div class="col-span-2">
              <label class="text-muted-foreground">{{ t('model.apiKey') }}</label>
              <div class="flex items-center gap-2 mt-1">
                <p class="font-medium font-mono text-xs bg-muted px-2 py-1 rounded flex-1">
                  {{ showApiKey ? selectedModel?.api_key : maskApiKey(selectedModel?.api_key) }}
                </p>
                <button
                  @click="showApiKey = !showApiKey"
                  class="p-1.5 rounded hover:bg-muted transition-colors"
                  :title="showApiKey ? t('modelDetail.hideApiKey') : t('modelDetail.showApiKey')"
                >
                  <Eye v-if="!showApiKey" class="w-4 h-4 text-muted-foreground" />
                  <EyeOff v-else class="w-4 h-4 text-muted-foreground" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 配置 Tab -->
      <div v-if="activeTab === 'config'" class="h-full">
        <ConfigEditor
          v-model="configContent"
          :title="`${t('detail.configFile')} (${selectedModel?.name || 'model'}.yaml)`"
          :modified="configModified"
          :saving="savingConfig"
          @save="saveConfig"
          @copy="copyConfig"
        />
      </div>

        <!-- Chat Tab -->
        <div v-if="activeTab === 'chat'" class="h-full">
          <ModelChatPanel
            v-if="selectedBusinessUnit && selectedAgent && selectedModel"
            :business-unit-id="selectedBusinessUnit.id"
            :agent-name="selectedAgent.name"
            :model-name="selectedModel.name"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { 
  ArrowLeft, ChevronRight, Cpu, Pencil, Trash2,
  FileText, FileCode, MessageSquare,
  HardDrive, Cloud, Eye, EyeOff
} from "lucide-vue-next";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import ConfigEditor from "@/components/common/ConfigEditor.vue";
import ModelChatPanel from "@/components/detail/ModelChatPanel.vue";
import { useBusinessUnitStore } from "@/stores/businessUnitStore";
import { useConfigManager } from "@/composables/useConfigManager";
import { modelApi } from "@/services/api";

const { t } = useI18n();
const store = useBusinessUnitStore();

// 使用 computed 保持响应式
const selectedBusinessUnit = computed(() => store.selectedBusinessUnit.value);
const selectedAgent = computed(() => store.selectedAgent.value);
const selectedModel = computed(() => store.selectedModel.value);

// 检查当前 Model 是否启用（通过 Agent 的 active_model 或 llm_config.llm_model）
const isModelEnabled = computed(() => {
  if (!selectedModel.value || !selectedAgent.value) return false;
  const modelName = selectedModel.value.name;
  // 检查 active_model 字段
  if (selectedAgent.value.active_model === modelName) {
    return true;
  }
  // 也检查 llm_config.llm_model 是否包含该模型名称
  const llmModel = selectedAgent.value.llm_config?.llm_model || '';
  return llmModel.includes(modelName);
});

// 启用/禁用 Model 状态
const enablingModel = ref(false);

// Tab 状态
const activeTab = ref<'overview' | 'config' | 'chat'>('overview');

const tabs = computed(() => [
  { id: 'overview' as const, label: t('detail.overview'), icon: FileText },
  { id: 'config' as const, label: t('detail.config'), icon: FileCode },
  { id: 'chat' as const, label: 'Chat', icon: MessageSquare },
]);

// 使用配置管理器处理 Model 配置
const modelConfigManager = useConfigManager({
  type: 'model',
  getConfigPath: () => {
    if (!selectedModel.value?.path) return undefined;
    // Model 配置文件名为 {modelName}.yaml
    return selectedModel.value.path;
  },
  loadConfig: async () => {
    if (!selectedBusinessUnit.value || !selectedAgent.value || !selectedModel.value) return '';
    try {
      const response = await modelApi.getConfig(
        selectedBusinessUnit.value.id,
        selectedAgent.value.name,
        selectedModel.value.name
      );
      return response.content;
    } catch (e) {
      console.error('Failed to load model config:', e);
      return '';
    }
  },
  onSaved: async () => {
    // 刷新 model 数据
    if (selectedBusinessUnit.value && selectedAgent.value && selectedModel.value) {
      await store.selectModel(selectedBusinessUnit.value.id, selectedAgent.value.name, selectedModel.value.name);
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
} = modelConfigManager;

// 弹窗状态
const showDeleteDialog = ref(false);
const showEditModelDialog = ref(false);
const deleteMessage = ref('');
const deleteDescription = ref('');

// API Key 显示状态
const showApiKey = ref(false);

// 提供商名称映射
const providerNames: Record<string, string> = {
  qianwen: '通义千问',
  deepseek: 'DeepSeek',
  llama: 'Llama',
  mistral: 'Mistral',
  chatglm: 'ChatGLM',
  baichuan: '百川',
  internlm: 'InternLM',
  qwen2: 'Qwen2',
  openai: 'OpenAI',
  claude: 'Anthropic Claude',
  qianfan: '百度千帆',
  gemini: 'Google Gemini',
  zhipu: '智谱 AI',
  moonshot: 'Moonshot',
  other: '其他',
};

// 格式化提供商名称
function formatProviderName(provider: string): string {
  return providerNames[provider] || provider;
}

// 遮蔽 API Key
function maskApiKey(apiKey?: string): string {
  if (!apiKey) return '-';
  if (apiKey.length <= 8) return '********';
  return apiKey.slice(0, 4) + '****' + apiKey.slice(-4);
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

// 返回到 Agent
function goBack() {
  store.clearSelectedModel();
}

// 返回到 Business Unit 详情
function goToBusinessUnit() {
  store.clearSelectedModel();
  store.clearSelectedAgent();
}

// 返回到 Agent 详情
function goToAgent() {
  store.clearSelectedModel();
}

// 确认删除 Model
function confirmDeleteModel() {
  if (!selectedModel.value) return;
  deleteMessage.value = t('modelDetail.confirmDeleteModel', { name: selectedModel.value.name });
  deleteDescription.value = t('modelDetail.confirmDeleteModelDesc');
  showDeleteDialog.value = true;
}

// 执行删除
async function handleConfirmDelete() {
  if (!selectedBusinessUnit.value || !selectedAgent.value || !selectedModel.value) return;
  
  const success = await store.deleteModel(
    selectedBusinessUnit.value.id, 
    selectedAgent.value.name, 
    selectedModel.value.name
  );
  if (success) {
    showDeleteDialog.value = false;
    store.clearSelectedModel();
  }
}

// 切换 Model 启用状态
async function toggleModelEnabled() {
  if (!selectedBusinessUnit.value || !selectedAgent.value || !selectedModel.value) return;
  
  const newEnabled = !isModelEnabled.value;
  enablingModel.value = true;
  
  try {
    if (newEnabled) {
      // 启用模型
      await modelApi.enable(
        selectedBusinessUnit.value.id,
        selectedAgent.value.name,
        selectedModel.value.name
      );
    } else {
      // 禁用模型
      await modelApi.update(
        selectedBusinessUnit.value.id,
        selectedAgent.value.name,
        selectedModel.value.name,
        { enabled: false }
      );
    }
    // 刷新 Agent 详情以更新状态
    await store.selectAgent(selectedBusinessUnit.value.id, selectedAgent.value.name);
    // 刷新 Model 详情
    await store.selectModel(selectedBusinessUnit.value.id, selectedAgent.value.name, selectedModel.value.name);
  } catch (e) {
    console.error('Failed to toggle model enabled:', e);
  } finally {
    enablingModel.value = false;
  }
}

// 监听 Model 变化，重新加载配置
watch(selectedModel, () => {
  activeTab.value = 'overview';
  showApiKey.value = false;
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
