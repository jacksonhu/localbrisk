<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[520px] max-h-[85vh] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <div class="flex items-center gap-2">
              <Bot class="w-5 h-5 text-primary" />
              <h2 class="text-lg font-semibold text-foreground">
                {{ t('catalog.createAgent') }}
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
            <!-- Agent 名称 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('catalog.agentName') }}
                <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                :placeholder="t('catalog.agentNameHint')"
                class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                :class="errors.name ? 'border-red-500' : 'border-input'"
                @input="validateName"
              />
              <p v-if="errors.name" class="text-xs text-red-500">{{ errors.name }}</p>
              <p v-else class="text-xs text-muted-foreground">{{ t('catalog.agentNameHint') }}</p>
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
                :placeholder="t('catalog.agentDescHint')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              ></textarea>
            </div>

            <!-- 模型引用 -->
            <div class="space-y-4">
              <!-- Schema 选择 -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('catalog.modelReference') }}
                  <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
                </label>
                <div class="grid grid-cols-2 gap-3">
                  <!-- Schema 下拉框 -->
                  <div class="relative">
                    <select
                      v-model="selectedSchemaName"
                      @change="onSchemaChange(selectedSchemaName)"
                      class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring appearance-none pr-8"
                    >
                      <option value="">{{ t('catalog.selectSchema') }}</option>
                      <option v-for="schema in schemas" :key="schema.id" :value="schema.name">
                        {{ schema.name }}
                      </option>
                    </select>
                    <ChevronDown class="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                  </div>
                  
                  <!-- Model 下拉框 -->
                  <div class="relative">
                    <select
                      v-model="form.model_reference"
                      :disabled="!selectedSchemaName || loadingModels"
                      class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed appearance-none pr-8"
                    >
                      <option value="">{{ loadingModels ? t('common.loading') : t('catalog.selectModel') }}</option>
                      <option v-for="model in models" :key="model.id" :value="`${selectedSchemaName}.${model.name}`">
                        {{ model.name }}
                      </option>
                    </select>
                    <Loader2 v-if="loadingModels" class="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground" />
                    <ChevronDown v-else class="w-4 h-4 absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
                <p v-if="models.length === 0 && selectedSchemaName && !loadingModels" class="text-xs text-amber-600">
                  {{ t('catalog.noModelsInSchema') }}
                </p>
                <p v-else class="text-xs text-muted-foreground">{{ t('catalog.modelReferenceDesc') }}</p>
              </div>
            </div>

            <!-- 系统提示词 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('catalog.systemPrompt') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <textarea
                v-model="form.system_prompt"
                rows="4"
                :placeholder="t('catalog.systemPromptHint')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none font-mono"
              ></textarea>
              <p class="text-xs text-muted-foreground">{{ t('catalog.systemPromptDesc') }}</p>
            </div>

            <!-- 提示信息 -->
            <div class="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-900">
              <div class="flex gap-2">
                <Info class="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                <div class="text-xs text-blue-700 dark:text-blue-300">
                  <p class="font-medium mb-1">{{ t('catalog.agentStructure') }}</p>
                  <ul class="list-disc list-inside space-y-0.5 text-blue-600 dark:text-blue-400">
                    <li><code class="text-xs">skills/</code> - {{ t('catalog.skillsDesc') }}</li>
                    <li><code class="text-xs">prompts/</code> - {{ t('catalog.promptsDesc') }}</li>
                  </ul>
                </div>
              </div>
            </div>
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
import { X, Loader2, Bot, Info, ChevronDown } from 'lucide-vue-next';
import type { AgentCreate, Schema, Model } from '@/types/catalog';
import { useCatalogStore } from '@/stores/catalogStore';
import { modelApi } from '@/services/api';

const { t } = useI18n();
const store = useCatalogStore();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, data: AgentCreate): void;
}>();

// 表单状态
const form = reactive<AgentCreate>({
  name: '',
  description: '',
  system_prompt: '',
  model_reference: '',
});

// 错误状态
const errors = reactive({
  name: '',
});

// 提交状态
const isSubmitting = ref(false);

// Schema 和 Model 列表
const schemas = ref<Schema[]>([]);
const models = ref<Model[]>([]);
const selectedSchemaName = ref('');
const loadingModels = ref(false);

// 名称验证正则（字母开头，允许字母、数字、下划线、连字符）
const nameRegex = /^[a-zA-Z][a-zA-Z0-9_-]*$/;

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.agentNameRequired');
    return false;
  }
  if (!nameRegex.test(form.name)) {
    errors.name = t('errors.agentNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  return form.name && nameRegex.test(form.name);
});

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

// 加载 Models
async function loadModels(schemaName: string) {
  if (!props.catalogId || !schemaName) {
    models.value = [];
    return;
  }
  
  loadingModels.value = true;
  try {
    models.value = await modelApi.list(props.catalogId, schemaName);
  } catch (e) {
    console.error('Failed to load models:', e);
    models.value = [];
  } finally {
    loadingModels.value = false;
  }
}

// 选择 Schema 时加载 Models
function onSchemaChange(schemaName: string) {
  selectedSchemaName.value = schemaName;
  form.model_reference = '';
  loadModels(schemaName);
}

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  if (!validateName() || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    const data: AgentCreate = {
      name: form.name,
    };
    
    if (form.description) {
      data.description = form.description;
    }
    if (form.system_prompt) {
      data.system_prompt = form.system_prompt;
    }
    if (form.model_reference) {
      data.model_reference = form.model_reference;
    }
    
    emit('submit', props.catalogId, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  form.name = '';
  form.description = '';
  form.system_prompt = '';
  form.model_reference = '';
  errors.name = '';
  selectedSchemaName.value = '';
  schemas.value = [];
  models.value = [];
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
