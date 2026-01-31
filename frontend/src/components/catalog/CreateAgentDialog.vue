<!--
  CreateAgentDialog - 创建 Agent 弹窗
  简化版：仅需要输入 Agent 名称
  其他配置通过 Agent 详情页的配置文件完成
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('catalog.createAgent')"
    :icon="Bot"
    width="md"
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

      <!-- 提示信息 -->
      <div class="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-900">
        <div class="flex gap-2">
          <Info class="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div class="text-xs text-blue-700 dark:text-blue-300">
            <p class="font-medium mb-1">{{ t('catalog.agentStructure') }}</p>
            <ul class="list-disc list-inside space-y-0.5 text-blue-600 dark:text-blue-400">
              <li><code class="text-xs">agent_spec.yaml</code> - {{ t('catalog.agentSpecDesc') }}</li>
              <li><code class="text-xs">skills/</code> - {{ t('catalog.skillsDesc') }}</li>
              <li><code class="text-xs">prompts/</code> - {{ t('catalog.promptsDesc') }}</li>
            </ul>
            <p class="mt-2 text-blue-500 dark:text-blue-400">
              {{ t('catalog.agentConfigHint') }}
            </p>
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
import type { AgentCreate } from '@/types/catalog';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';

const { t } = useI18n();

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

// 表单状态 - 只保留 name
const form = reactive({
  name: '',
});

// 错误状态
const errors = reactive({
  name: '',
});

// 提交状态
const isSubmitting = ref(false);

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
    
    emit('submit', props.catalogId, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  form.name = '';
  errors.name = '';
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});
</script>
