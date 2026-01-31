<!-- 
  CreatePromptDialog - 创建 Prompt 弹窗
  使用公共组件重构，减少重复代码
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('prompt.create')"
    :icon="FileText"
    width="md"
    @close="close"
  >
    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Prompt 名称 -->
      <FormField
        :label="t('prompt.name')"
        :error="errors.name"
        :hint="t('prompt.nameHint')"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('prompt.nameHint')"
          @input="validateName"
        />
      </FormField>

      <!-- 初始内容 -->
      <FormField
        :label="t('prompt.content')"
        :hint="t('prompt.contentHint')"
        optional
      >
        <FormTextarea
          v-model="form.content"
          :rows="6"
          :placeholder="t('prompt.contentHint')"
          class="font-mono"
        />
      </FormField>

      <!-- 提示信息 -->
      <div class="p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-900">
        <div class="flex gap-2">
          <Info class="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
          <div class="text-xs text-blue-700 dark:text-blue-300">
            <p>Prompt 文件将保存为 Markdown 格式（.md），支持标题、列表、代码块等 Markdown 语法。</p>
          </div>
        </div>
      </div>
    </form>
    
    <!-- 底部按钮 -->
    <template #footer>
      <DialogFooter
        :submitting="isSubmitting"
        :disabled="!isValid"
        :submit-text="t('common.create')"
        @cancel="close"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { FileText, Info } from 'lucide-vue-next';
import { BaseDialog, DialogFooter, FormField, FormInput, FormTextarea } from '@/components/common';
import { NAME_REGEX } from '@/utils/validationUtils';
import type { PromptCreate } from '@/types/catalog';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
  agentName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, agentName: string, data: PromptCreate): void;
}>();

// 表单状态
const form = reactive<PromptCreate>({
  name: '',
  content: '',
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
    errors.name = t('errors.promptNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.promptNameInvalid');
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
    const data: PromptCreate = {
      name: form.name,
      content: form.content || '',
    };
    
    emit('submit', props.catalogId, props.agentName, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  form.name = '';
  form.content = '';
  errors.name = '';
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});
</script>
