<!--
  CreateAgentDialog - 创建 Agent 弹窗
  使用 BaseDialog 和公共表单组件
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('catalog.createAgent')"
    :icon="Bot"
    width="lg"
    max-height="screen"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Agent 名称 -->
      <FormField
        :label="t('catalog.agentName')"
        :error="errors.name"
        :hint="t('catalog.agentNameHint')"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('catalog.agentNameHint')"
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
          :placeholder="t('catalog.agentDescHint')"
          :rows="2"
        />
      </FormField>

      <!-- 模型引用 -->
      <div class="space-y-4">
        <FormField
          :label="t('catalog.modelReference')"
          :hint="models.length === 0 && selectedSchemaName && !loadingModels 
            ? t('catalog.noModelsInSchema') 
            : t('catalog.modelReferenceDesc')"
          :hint-type="models.length === 0 && selectedSchemaName && !loadingModels ? 'warning' : 'default'"
          optional
        >
          <div class="grid grid-cols-2 gap-3">
            <!-- Schema 下拉框 -->
            <FormSelect
              v-model="selectedSchemaName"
              :options="schemaOptions"
              :placeholder="t('catalog.selectSchema')"
              @update:model-value="onSchemaChange"
            />
            
            <!-- Model 下拉框 -->
            <FormSelect
              v-model="form.model_reference"
              :options="modelOptions"
              :placeholder="loadingModels ? t('common.loading') : t('catalog.selectModel')"
              :disabled="!selectedSchemaName || loadingModels"
              :loading="loadingModels"
            />
          </div>
        </FormField>
      </div>

      <!-- 系统提示词 -->
      <FormField
        :label="t('catalog.systemPrompt')"
        :hint="t('catalog.systemPromptDesc')"
        optional
      >
        <FormTextarea
          v-model="form.system_prompt"
          :placeholder="t('catalog.systemPromptHint')"
          :rows="4"
          class="font-mono"
        />
      </FormField>

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
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Bot, Info } from 'lucide-vue-next';
import type { AgentCreate, Schema, Model } from '@/types/catalog';
import { useCatalogStore } from '@/stores/catalogStore';
import { modelApi } from '@/services/api';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';
import FormTextarea from '@/components/common/FormTextarea.vue';
import FormSelect from '@/components/common/FormSelect.vue';

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

// Schema 选项
const schemaOptions = computed(() => 
  schemas.value.map(s => ({ value: s.name, label: s.name }))
);

// Model 选项
const modelOptions = computed(() => 
  models.value.map(m => ({ 
    value: `${selectedSchemaName.value}.${m.name}`, 
    label: m.name 
  }))
);

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.agentNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.agentNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  return form.name && NAME_REGEX.test(form.name);
});

// 加载 Schemas
async function loadSchemas() {
  if (!props.catalogId) return;
  
  try {
    const catalog = store.selectedCatalog.value;
    if (catalog && catalog.id === props.catalogId) {
      schemas.value = catalog.schemas || [];
    } else {
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
function onSchemaChange(schemaName: string | number) {
  selectedSchemaName.value = schemaName as string;
  form.model_reference = '';
  loadModels(schemaName as string);
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
    await loadSchemas();
  }
});
</script>
