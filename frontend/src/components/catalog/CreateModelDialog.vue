<!--
  CreateModelDialog - 创建 Model 弹窗
  支持本地模型和 API 端点两种模式
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('model.createModel')"
    :icon="Cpu"
    width="xl"
    max-height="screen"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- 模型名称 -->
      <FormField
        :label="t('model.modelName')"
        :error="errors.name"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('model.modelNameHint')"
          :error="!!errors.name"
          @input="validateName"
        />
      </FormField>

      <!-- 描述 -->
      <FormField
        :label="t('common.description')"
        optional
      >
        <FormTextarea
          v-model="form.description"
          :placeholder="t('model.descriptionHint')"
          :rows="2"
        />
      </FormField>

      <!-- 模型类型选择 -->
      <FormField
        :label="t('model.modelType')"
        required
      >
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
      </FormField>

      <!-- 本地模型配置 -->
      <template v-if="form.model_type === 'local'">
        <!-- 开源模型类型 -->
        <FormField
          :label="t('model.localProvider')"
          required
        >
          <FormSelect
            v-model="form.local_provider"
            :options="localProviderOptions"
            :placeholder="t('model.selectProvider')"
          />
        </FormField>

        <!-- 模型来源 -->
        <FormField
          :label="t('model.modelSource')"
          required
        >
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
        </FormField>

        <!-- Volume 引用 -->
        <template v-if="form.local_source === 'volume'">
          <FormField
            :label="t('model.selectAssetBundle')"
            required
          >
            <FormSelect
              v-model="selectedBundleName"
              :options="assetBundleOptions"
              :placeholder="t('model.selectAssetBundleHint')"
              @update:model-value="onAssetBundleChange"
            />
          </FormField>

          <FormField
            :label="t('model.volumeReference')"
            :hint="volumes.length === 0 && selectedBundleName && !loadingVolumes 
              ? t('model.noVolumesInAssetBundle') 
              : t('model.volumeReferenceDesc')"
            :hint-type="volumes.length === 0 && selectedBundleName && !loadingVolumes ? 'warning' : 'default'"
            required
          >
            <FormSelect
              v-model="form.volume_reference"
              :options="volumeOptions"
              :placeholder="loadingVolumes ? t('common.loading') : t('model.selectVolumeHint')"
              :disabled="!selectedBundleName || loadingVolumes"
              :loading="loadingVolumes"
            />
          </FormField>
        </template>

        <!-- HuggingFace 配置 -->
        <template v-if="form.local_source === 'huggingface'">
          <FormField
            :label="t('model.huggingfaceRepo')"
            required
          >
            <FormInput
              v-model="form.huggingface_repo"
              :placeholder="t('model.huggingfaceRepoHint')"
              class="font-mono"
            />
          </FormField>
          <FormField
            :label="t('model.huggingfaceFilename')"
            optional
          >
            <FormInput
              v-model="form.huggingface_filename"
              :placeholder="t('model.huggingfaceFilenameHint')"
              class="font-mono"
            />
          </FormField>
        </template>
      </template>

      <!-- API 端点配置 -->
      <template v-if="form.model_type === 'endpoint'">
        <!-- API 提供商 -->
        <FormField
          :label="t('model.endpointProvider')"
          required
        >
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
        </FormField>

        <!-- API Base URL -->
        <FormField
          :label="t('model.apiBaseUrl')"
          :hint="t('model.apiBaseUrlDesc')"
          optional
        >
          <FormInput
            v-model="form.api_base_url"
            :placeholder="getApiUrlPlaceholder()"
            class="font-mono"
          />
        </FormField>

        <!-- API Key -->
        <FormField
          :label="t('model.apiKey')"
          required
        >
          <div class="relative">
            <FormInput
              v-model="form.api_key"
              :type="showApiKey ? 'text' : 'password'"
              :placeholder="t('model.apiKeyHint')"
              class="font-mono pr-10"
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
        </FormField>

        <!-- 模型 ID -->
        <FormField
          :label="t('model.modelId')"
          :hint="getModelHint()"
          required
        >
          <FormInput
            v-model="form.model_id"
            :placeholder="t('model.modelIdHint')"
            class="font-mono"
          />
        </FormField>
      </template>

      <!-- Temperature 参数（所有模型类型都可设置） -->
      <FormField
        :label="t('model.temperature')"
        :hint="t('model.temperatureHint')"
      >
        <div class="flex items-center gap-4">
          <input
            type="range"
            v-model.number="form.temperature"
            min="0"
            max="2"
            step="0.1"
            class="flex-1 h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
          />
          <FormInput
            v-model.number="form.temperature"
            type="number"
            min="0"
            max="2"
            step="0.1"
            class="w-20 text-center"
          />
        </div>
      </FormField>
    </form>

    <template #footer>
      <DialogFooter
        :submitting="isSubmitting"
        :disabled="!isValid"
        @cancel="close"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { 
  Cpu, HardDrive, Cloud, FolderOpen, Download,
  Eye, EyeOff, Sparkles, Bot, Zap, Globe, Brain, MessageSquare
} from 'lucide-vue-next';
import type { Component } from 'vue';
import type { ModelCreate, AssetBundle, Asset } from '@/types/catalog';
import { useBusinessUnitStore } from '@/stores/businessUnitStore';
import { assetApi } from '@/services/api';
import { llmApi, type ProviderOption, type ModelOption } from '@/services/llm-api';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';
import FormTextarea from '@/components/common/FormTextarea.vue';
import FormSelect from '@/components/common/FormSelect.vue';

const { t } = useI18n();
const store = useBusinessUnitStore();

// Props
const props = defineProps<{
  isOpen: boolean;
  businessUnitId: string;
  agentName: string;  // 改为 agentName，Model 现在在 Agent 下
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', businessUnitId: string, agentName: string, data: ModelCreate): void;
}>();

// 图标映射
const iconMap: Record<string, Component> = {
  Sparkles,
  Bot,
  Brain,
  Globe,
  Zap,
  MessageSquare,
};

// LLM 配置数据（从后端获取）
const localProviderOptions = ref<{ value: string; label: string }[]>([]);
const endpointProviders = ref<{ value: string; label: string; icon: Component }[]>([]);
const providerModels = ref<Record<string, { value: string; label: string }[]>>({});
const providerDefaultUrls = ref<Record<string, string>>({});
const loadingLLMConfig = ref(false);

// 加载 LLM 配置
async function loadLLMConfig() {
  loadingLLMConfig.value = true;
  try {
    // 并行加载所有配置
    const [localData, endpointData] = await Promise.all([
      llmApi.getLocalProviders(),
      llmApi.getEndpointProviders(),
    ]);

    // 设置本地提供商选项
    localProviderOptions.value = localData.map(p => ({
      value: p.value,
      label: p.label,
    }));

    // 设置端点提供商选项（带图标）
    endpointProviders.value = endpointData.map(p => ({
      value: p.value,
      label: p.label,
      icon: iconMap[p.icon || 'Sparkles'] || Sparkles,
    }));

    // 并行加载所有提供商的模型和默认 URL
    await Promise.all(
      endpointData.map(async (provider) => {
        try {
          const [models, defaultUrl] = await Promise.all([
            llmApi.getProviderModels(provider.value),
            llmApi.getProviderDefaultUrl(provider.value),
          ]);
          
          providerModels.value[provider.value] = models.map(m => ({
            value: m.value,
            label: m.label,
          }));
          providerDefaultUrls.value[provider.value] = defaultUrl;
        } catch (e) {
          console.warn(`Failed to load config for provider ${provider.value}:`, e);
        }
      })
    );
  } catch (e) {
    console.error('Failed to load LLM configuration:', e);
    // 回退到默认配置
    localProviderOptions.value = [
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
    endpointProviders.value = [
      { value: 'openai', label: 'OpenAI', icon: Sparkles },
      { value: 'claude', label: 'Claude', icon: Bot },
      { value: 'qianwen', label: '通义千问', icon: Brain },
      { value: 'qianfan', label: '百度千帆', icon: Globe },
      { value: 'gemini', label: 'Gemini', icon: Zap },
      { value: 'deepseek', label: 'DeepSeek', icon: MessageSquare },
      { value: 'zhipu', label: '智谱 AI', icon: Brain },
      { value: 'moonshot', label: 'Moonshot', icon: Sparkles },
    ];
  } finally {
    loadingLLMConfig.value = false;
  }
}

// 组件挂载时加载配置
onMounted(() => {
  loadLLMConfig();
});

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
  temperature: 0,
});

// 错误状态
const errors = reactive({
  name: '',
});

// 提交状态
const isSubmitting = ref(false);
const showApiKey = ref(false);

// Asset Bundle 和 Volume 列表
const assetBundles = ref<AssetBundle[]>([]);
const volumes = ref<Asset[]>([]);
const selectedBundleName = ref('');
const loadingVolumes = ref(false);

// Asset Bundle 选项
const assetBundleOptions = computed(() => 
  assetBundles.value.map(s => ({ value: s.name, label: s.name }))
);

// Volume 选项
const volumeOptions = computed(() => 
  volumes.value.map(v => ({ 
    value: `${selectedBundleName.value}.${v.name}`, 
    label: v.name 
  }))
);

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.modelNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.modelNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  if (!form.name || !NAME_REGEX.test(form.name)) return false;
  
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
  if (providerDefaultUrls.value[provider]) {
    form.api_base_url = providerDefaultUrls.value[provider];
  }
  form.model_id = '';
}

// 获取 API URL 占位符
function getApiUrlPlaceholder() {
  if (form.endpoint_provider && providerDefaultUrls.value[form.endpoint_provider]) {
    return providerDefaultUrls.value[form.endpoint_provider];
  }
  return 'https://api.example.com/v1';
}

// 获取模型提示信息
function getModelHint() {
  if (form.endpoint_provider && providerModels.value[form.endpoint_provider]) {
    const models = providerModels.value[form.endpoint_provider];
    if (models.length > 0) {
      const examples = models.slice(0, 3).map(m => m.value).join(', ');
      return `${t('model.modelIdDesc')}: ${examples}${models.length > 3 ? ', ...' : ''}`;
    }
  }
  return t('model.modelIdDesc');
}

// 加载 Asset Bundles
async function loadAssetBundles() {
  if (!props.businessUnitId) return;
  
  try {
    const businessUnit = store.selectedBusinessUnit.value;
    if (businessUnit && businessUnit.id === props.businessUnitId) {
      assetBundles.value = businessUnit.asset_bundles || [];
    } else {
      const bundleList = await store.fetchAssetBundles(props.businessUnitId);
      assetBundles.value = bundleList;
    }
  } catch (e) {
    console.error('Failed to load asset bundles:', e);
    assetBundles.value = [];
  }
}

// 加载 Volumes
async function loadVolumes(bundleName: string) {
  if (!props.businessUnitId || !bundleName) {
    volumes.value = [];
    return;
  }
  
  loadingVolumes.value = true;
  try {
    const assets = await assetApi.list(props.businessUnitId, bundleName);
    volumes.value = assets.filter(a => a.asset_type === 'volume');
  } catch (e) {
    console.error('Failed to load volumes:', e);
    volumes.value = [];
  } finally {
    loadingVolumes.value = false;
  }
}

// 选择 Asset Bundle 时加载 Volumes
function onAssetBundleChange(bundleName: string | number) {
  selectedBundleName.value = bundleName as string;
  form.volume_reference = '';
  loadVolumes(bundleName as string);
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
      temperature: form.temperature,
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
    
    emit('submit', props.businessUnitId, props.agentName, data);
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
  form.temperature = 0;
  errors.name = '';
  showApiKey.value = false;
  selectedBundleName.value = '';
  assetBundles.value = [];
  volumes.value = [];
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    resetForm();
    await loadAssetBundles();
  }
});
</script>
