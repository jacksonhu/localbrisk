<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[560px] max-h-[85vh] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <div class="flex items-center gap-2">
              <Cpu class="w-5 h-5 text-primary" />
              <h2 class="text-lg font-semibold text-foreground">
                {{ t('model.createModel') }}
              </h2>
            </div>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 表单内容 -->
          <form @submit.prevent="handleSubmit" class="p-6 space-y-5 overflow-y-auto max-h-[65vh]">
            <!-- 模型名称 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('model.modelName') }}
                <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                :placeholder="t('model.modelNameHint')"
                class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                :class="errors.name ? 'border-red-500' : 'border-input'"
                @input="validateName"
              />
              <p v-if="errors.name" class="text-xs text-red-500">{{ errors.name }}</p>
            </div>

            <!-- 描述 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('common.description') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <textarea
                v-model="form.description"
                rows="2"
                :placeholder="t('model.descriptionHint')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              ></textarea>
            </div>

            <!-- 模型类型选择 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('model.modelType') }}
                <span class="text-red-500">*</span>
              </label>
              <div class="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  @click="form.model_type = 'local'"
                  class="flex flex-col items-center gap-2 p-4 border rounded-lg transition-colors"
                  :class="form.model_type === 'local' 
                    ? 'border-primary bg-primary/5 text-primary' 
                    : 'border-input hover:border-muted-foreground'"
                >
                  <HardDrive class="w-6 h-6" />
                  <span class="text-sm font-medium">{{ t('model.localModel') }}</span>
                  <span class="text-xs text-muted-foreground">{{ t('model.localModelDesc') }}</span>
                </button>
                <button
                  type="button"
                  @click="form.model_type = 'endpoint'"
                  class="flex flex-col items-center gap-2 p-4 border rounded-lg transition-colors"
                  :class="form.model_type === 'endpoint' 
                    ? 'border-primary bg-primary/5 text-primary' 
                    : 'border-input hover:border-muted-foreground'"
                >
                  <Cloud class="w-6 h-6" />
                  <span class="text-sm font-medium">{{ t('model.endpointModel') }}</span>
                  <span class="text-xs text-muted-foreground">{{ t('model.endpointModelDesc') }}</span>
                </button>
              </div>
            </div>

            <!-- 本地模型配置 -->
            <template v-if="form.model_type === 'local'">
              <!-- 开源模型类型 -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.localProvider') }}
                  <span class="text-red-500">*</span>
                </label>
                <select
                  v-model="form.local_provider"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">{{ t('model.selectProvider') }}</option>
                  <option v-for="provider in localProviders" :key="provider.value" :value="provider.value">
                    {{ provider.label }}
                  </option>
                </select>
              </div>

              <!-- 模型来源 -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.modelSource') }}
                  <span class="text-red-500">*</span>
                </label>
                <div class="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    @click="form.local_source = 'volume'"
                    class="flex items-center gap-3 p-3 border rounded-lg transition-colors"
                    :class="form.local_source === 'volume' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-input hover:border-muted-foreground'"
                  >
                    <FolderOpen class="w-5 h-5" :class="form.local_source === 'volume' ? 'text-primary' : ''" />
                    <div class="text-left">
                      <div class="text-sm font-medium">{{ t('model.volumeSource') }}</div>
                      <div class="text-xs text-muted-foreground">{{ t('model.volumeSourceDesc') }}</div>
                    </div>
                  </button>
                  <button
                    type="button"
                    @click="form.local_source = 'huggingface'"
                    class="flex items-center gap-3 p-3 border rounded-lg transition-colors"
                    :class="form.local_source === 'huggingface' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-input hover:border-muted-foreground'"
                  >
                    <Download class="w-5 h-5" :class="form.local_source === 'huggingface' ? 'text-primary' : ''" />
                    <div class="text-left">
                      <div class="text-sm font-medium">HuggingFace</div>
                      <div class="text-xs text-muted-foreground">{{ t('model.huggingfaceDesc') }}</div>
                    </div>
                  </button>
                </div>
              </div>

              <!-- Volume 引用 -->
              <div v-if="form.local_source === 'volume'" class="space-y-4">
                <!-- Schema 选择 -->
                <div class="space-y-2">
                  <label class="block text-sm font-medium text-foreground">
                    {{ t('model.selectSchema') }}
                    <span class="text-red-500">*</span>
                  </label>
                  <select
                    v-model="selectedSchemaName"
                    @change="onSchemaChange(selectedSchemaName)"
                    class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    <option value="">{{ t('model.selectSchemaHint') }}</option>
                    <option v-for="schema in schemas" :key="schema.id" :value="schema.name">
                      {{ schema.name }}
                    </option>
                  </select>
                </div>

                <!-- Volume 选择 -->
                <div class="space-y-2">
                  <label class="block text-sm font-medium text-foreground">
                    {{ t('model.volumeReference') }}
                    <span class="text-red-500">*</span>
                  </label>
                  <div class="relative">
                    <select
                      v-model="form.volume_reference"
                      :disabled="!selectedSchemaName || loadingVolumes"
                      class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <option value="">{{ loadingVolumes ? t('common.loading') : t('model.selectVolumeHint') }}</option>
                      <option v-for="volume in volumes" :key="volume.id" :value="`${selectedSchemaName}.${volume.name}`">
                        {{ volume.name }}
                      </option>
                    </select>
                    <Loader2 v-if="loadingVolumes" class="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground" />
                  </div>
                  <p v-if="volumes.length === 0 && selectedSchemaName && !loadingVolumes" class="text-xs text-amber-600">
                    {{ t('model.noVolumesInSchema') }}
                  </p>
                  <p v-else class="text-xs text-muted-foreground">{{ t('model.volumeReferenceDesc') }}</p>
                </div>
              </div>

              <!-- HuggingFace 配置 -->
              <template v-if="form.local_source === 'huggingface'">
                <div class="space-y-2">
                  <label class="block text-sm font-medium text-foreground">
                    {{ t('model.huggingfaceRepo') }}
                    <span class="text-red-500">*</span>
                  </label>
                  <input
                    v-model="form.huggingface_repo"
                    type="text"
                    :placeholder="t('model.huggingfaceRepoHint')"
                    class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                  />
                </div>
                <div class="space-y-2">
                  <label class="block text-sm font-medium text-foreground">
                    {{ t('model.huggingfaceFilename') }}
                    <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
                  </label>
                  <input
                    v-model="form.huggingface_filename"
                    type="text"
                    :placeholder="t('model.huggingfaceFilenameHint')"
                    class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                  />
                </div>
              </template>
            </template>

            <!-- API 端点配置 -->
            <template v-if="form.model_type === 'endpoint'">
              <!-- API 提供商 -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.endpointProvider') }}
                  <span class="text-red-500">*</span>
                </label>
                <div class="grid grid-cols-4 gap-2">
                  <button
                    v-for="provider in endpointProviders"
                    :key="provider.value"
                    type="button"
                    @click="selectEndpointProvider(provider.value)"
                    class="flex flex-col items-center gap-1.5 p-3 border rounded-lg transition-colors"
                    :class="form.endpoint_provider === provider.value 
                      ? 'border-primary bg-primary/5' 
                      : 'border-input hover:border-muted-foreground'"
                  >
                    <component :is="provider.icon" class="w-5 h-5" :class="form.endpoint_provider === provider.value ? 'text-primary' : 'text-muted-foreground'" />
                    <span class="text-xs font-medium">{{ provider.label }}</span>
                  </button>
                </div>
              </div>

              <!-- API Base URL -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.apiBaseUrl') }}
                  <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
                </label>
                <input
                  v-model="form.api_base_url"
                  type="text"
                  :placeholder="getApiUrlPlaceholder()"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                />
                <p class="text-xs text-muted-foreground">{{ t('model.apiBaseUrlDesc') }}</p>
              </div>

              <!-- API Key -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.apiKey') }}
                  <span class="text-red-500">*</span>
                </label>
                <div class="relative">
                  <input
                    v-model="form.api_key"
                    :type="showApiKey ? 'text' : 'password'"
                    :placeholder="t('model.apiKeyHint')"
                    class="w-full px-3 py-2 pr-10 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                  />
                  <button
                    type="button"
                    @click="showApiKey = !showApiKey"
                    class="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded"
                  >
                    <Eye v-if="!showApiKey" class="w-4 h-4 text-muted-foreground" />
                    <EyeOff v-else class="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>
              </div>

              <!-- 模型 ID -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('model.modelId') }}
                  <span class="text-red-500">*</span>
                </label>
                <select
                  v-if="getModelOptions().length > 0"
                  v-model="form.model_id"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">{{ t('model.selectModel') }}</option>
                  <option v-for="model in getModelOptions()" :key="model.value" :value="model.value">
                    {{ model.label }}
                  </option>
                </select>
                <input
                  v-else
                  v-model="form.model_id"
                  type="text"
                  :placeholder="t('model.modelIdHint')"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                />
              </div>
            </template>
          </form>
          
          <!-- 底部按钮 -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
            <button
              type="button"
              @click="close"
              class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="handleSubmit"
              :disabled="isSubmitting || !isValid"
              class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
              {{ t('common.create') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { 
  X, Loader2, Cpu, HardDrive, Cloud, FolderOpen, Download,
  Eye, EyeOff, Sparkles, Bot, Zap, Globe, Brain, MessageSquare
} from 'lucide-vue-next';
import type { ModelCreate, Schema, Asset } from '@/types/catalog';
import { useCatalogStore } from '@/stores/catalogStore';
import { assetApi } from '@/services/api';

const { t } = useI18n();
const store = useCatalogStore();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
  schemaName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, schemaName: string, data: ModelCreate): void;
}>();

// 本地模型提供商选项
const localProviders = [
  { value: 'qianwen', label: '通义千问 (Qwen)' },
  { value: 'deepseek', label: 'DeepSeek' },
  { value: 'llama', label: 'Llama' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'chatglm', label: 'ChatGLM' },
  { value: 'baichuan', label: '百川' },
  { value: 'internlm', label: 'InternLM' },
  { value: 'qwen2', label: 'Qwen2' },
  { value: 'other', label: '其他' },
];

// API 端点提供商选项
const endpointProviders = [
  { value: 'openai', label: 'OpenAI', icon: Sparkles },
  { value: 'claude', label: 'Claude', icon: Bot },
  { value: 'qianwen', label: '通义千问', icon: Brain },
  { value: 'qianfan', label: '百度千帆', icon: Globe },
  { value: 'gemini', label: 'Gemini', icon: Zap },
  { value: 'deepseek', label: 'DeepSeek', icon: MessageSquare },
  { value: 'zhipu', label: '智谱 AI', icon: Brain },
  { value: 'moonshot', label: 'Moonshot', icon: Sparkles },
];

// 各提供商的模型列表
const providerModels: Record<string, { value: string; label: string }[]> = {
  openai: [
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
    { value: 'gpt-4', label: 'GPT-4' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  ],
  claude: [
    { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
  ],
  qianwen: [
    { value: 'qwen-turbo', label: 'Qwen Turbo' },
    { value: 'qwen-plus', label: 'Qwen Plus' },
    { value: 'qwen-max', label: 'Qwen Max' },
    { value: 'qwen-max-longcontext', label: 'Qwen Max Long Context' },
  ],
  qianfan: [
    { value: 'ernie-4.0-8k', label: 'ERNIE 4.0' },
    { value: 'ernie-3.5-8k', label: 'ERNIE 3.5' },
    { value: 'ernie-speed-128k', label: 'ERNIE Speed' },
    { value: 'ernie-lite-8k', label: 'ERNIE Lite' },
  ],
  gemini: [
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
    { value: 'gemini-1.0-pro', label: 'Gemini 1.0 Pro' },
  ],
  deepseek: [
    { value: 'deepseek-chat', label: 'DeepSeek Chat' },
    { value: 'deepseek-coder', label: 'DeepSeek Coder' },
  ],
  zhipu: [
    { value: 'glm-4', label: 'GLM-4' },
    { value: 'glm-4-flash', label: 'GLM-4 Flash' },
    { value: 'glm-3-turbo', label: 'GLM-3 Turbo' },
  ],
  moonshot: [
    { value: 'moonshot-v1-8k', label: 'Moonshot V1 8K' },
    { value: 'moonshot-v1-32k', label: 'Moonshot V1 32K' },
    { value: 'moonshot-v1-128k', label: 'Moonshot V1 128K' },
  ],
};

// 各提供商默认 API URL
const providerDefaultUrls: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  claude: 'https://api.anthropic.com/v1',
  qianwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  qianfan: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop',
  gemini: 'https://generativelanguage.googleapis.com/v1',
  deepseek: 'https://api.deepseek.com/v1',
  zhipu: 'https://open.bigmodel.cn/api/paas/v4',
  moonshot: 'https://api.moonshot.cn/v1',
};

// 表单状态
const form = reactive<ModelCreate>({
  name: '',
  description: '',
  model_type: 'endpoint',
  local_provider: '',
  local_source: 'volume',
  volume_reference: '',
  huggingface_repo: '',
  huggingface_filename: '',
  endpoint_provider: '',
  api_base_url: '',
  api_key: '',
  model_id: '',
});

// 错误状态
const errors = reactive({
  name: '',
});

// 提交状态
const isSubmitting = ref(false);
const showApiKey = ref(false);

// Schema 和 Volume 列表
const schemas = ref<Schema[]>([]);
const volumes = ref<Asset[]>([]);
const selectedSchemaName = ref('');
const loadingVolumes = ref(false);

// 名称验证正则
const nameRegex = /^[a-zA-Z][a-zA-Z0-9_-]*$/;

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.modelNameRequired');
    return false;
  }
  if (!nameRegex.test(form.name)) {
    errors.name = t('errors.modelNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  if (!form.name || !nameRegex.test(form.name)) return false;
  
  if (form.model_type === 'local') {
    if (!form.local_provider) return false;
    if (form.local_source === 'volume' && !form.volume_reference) return false;
    if (form.local_source === 'huggingface' && !form.huggingface_repo) return false;
  } else {
    if (!form.endpoint_provider) return false;
    if (!form.api_key) return false;
    if (!form.model_id) return false;
  }
  
  return true;
});

// 选择端点提供商
function selectEndpointProvider(provider: string) {
  form.endpoint_provider = provider;
  // 自动填充默认 API URL
  if (providerDefaultUrls[provider]) {
    form.api_base_url = providerDefaultUrls[provider];
  }
  // 清空之前选择的模型
  form.model_id = '';
}

// 获取 API URL 占位符
function getApiUrlPlaceholder() {
  if (form.endpoint_provider && providerDefaultUrls[form.endpoint_provider]) {
    return providerDefaultUrls[form.endpoint_provider];
  }
  return 'https://api.example.com/v1';
}

// 获取模型选项
function getModelOptions() {
  if (form.endpoint_provider && providerModels[form.endpoint_provider]) {
    return providerModels[form.endpoint_provider];
  }
  return [];
}

// 加载 Schemas
async function loadSchemas() {
  if (!props.catalogId) return;
  
  try {
    // 从 store 的 selectedCatalog 中获取 schemas
    const catalog = store.selectedCatalog.value;
    if (catalog && catalog.id === props.catalogId) {
      schemas.value = catalog.schemas || [];
    } else {
      // 如果没有，则调用 API 获取
      const schemaList = await store.fetchSchemas(props.catalogId);
      schemas.value = schemaList;
    }
  } catch (e) {
    console.error('Failed to load schemas:', e);
    schemas.value = [];
  }
}

// 加载 Volumes
async function loadVolumes(schemaName: string) {
  if (!props.catalogId || !schemaName) {
    volumes.value = [];
    return;
  }
  
  loadingVolumes.value = true;
  try {
    const assets = await assetApi.list(props.catalogId, schemaName);
    // 只筛选 volume 类型的 asset
    volumes.value = assets.filter(a => a.asset_type === 'volume');
  } catch (e) {
    console.error('Failed to load volumes:', e);
    volumes.value = [];
  } finally {
    loadingVolumes.value = false;
  }
}

// 选择 Schema 时加载 Volumes
function onSchemaChange(schemaName: string) {
  selectedSchemaName.value = schemaName;
  form.volume_reference = '';
  loadVolumes(schemaName);
}

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  if (!validateName() || isSubmitting.value || !isValid.value) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    const data: ModelCreate = {
      name: form.name,
      model_type: form.model_type,
    };
    
    if (form.description) {
      data.description = form.description;
    }
    
    if (form.model_type === 'local') {
      data.local_provider = form.local_provider;
      data.local_source = form.local_source;
      if (form.local_source === 'volume') {
        data.volume_reference = form.volume_reference;
      } else {
        data.huggingface_repo = form.huggingface_repo;
        if (form.huggingface_filename) {
          data.huggingface_filename = form.huggingface_filename;
        }
      }
    } else {
      data.endpoint_provider = form.endpoint_provider;
      data.api_key = form.api_key;
      data.model_id = form.model_id;
      if (form.api_base_url) {
        data.api_base_url = form.api_base_url;
      }
    }
    
    emit('submit', props.catalogId, props.schemaName, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  form.name = '';
  form.description = '';
  form.model_type = 'endpoint';
  form.local_provider = '';
  form.local_source = 'volume';
  form.volume_reference = '';
  form.huggingface_repo = '';
  form.huggingface_filename = '';
  form.endpoint_provider = '';
  form.api_base_url = '';
  form.api_key = '';
  form.model_id = '';
  errors.name = '';
  showApiKey.value = false;
  selectedSchemaName.value = '';
  schemas.value = [];
  volumes.value = [];
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    resetForm();
    // 加载 Schema 列表
    await loadSchemas();
  }
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
