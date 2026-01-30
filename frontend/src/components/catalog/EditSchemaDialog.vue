<!-- 
  EditSchemaDialog - 编辑 Schema 弹窗
  使用公共组件重构
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('catalog.editSchema')"
    :icon="Database"
    width="sm"
    @close="close"
  >
    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Schema 名称（只读） -->
      <FormField
        :label="t('catalog.schemaName')"
        :hint="t('catalog.schemaNameReadonly')"
      >
        <FormInput
          :model-value="schema?.name || ''"
          disabled
        />
      </FormField>

      <!-- 描述 -->
      <FormField
        :label="t('common.description')"
        optional
      >
        <FormTextarea
          v-model="form.description"
          :rows="3"
          :placeholder="t('detail.addDescription')"
        />
      </FormField>
    </form>
    
    <!-- 底部按钮 -->
    <template #footer>
      <DialogFooter
        :submitting="isSubmitting"
        :submit-text="t('common.save')"
        @cancel="close"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Database } from 'lucide-vue-next';
import { BaseDialog, DialogFooter, FormField, FormInput, FormTextarea } from '@/components/common';
import type { Schema, SchemaUpdate } from '@/types/catalog';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
  schema: Schema | null;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, schemaName: string, data: SchemaUpdate): void;
}>();

// 表单状态
const form = reactive<SchemaUpdate>({
  description: '',
});

// 提交状态
const isSubmitting = ref(false);

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  if (isSubmitting.value || !props.schema) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    const data: SchemaUpdate = {};
    
    // 只有当描述发生变化时才提交
    if (form.description !== (props.schema.description || '')) {
      data.description = form.description || undefined;
    }
    
    emit('submit', props.catalogId, props.schema.name, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  if (props.schema) {
    form.description = props.schema.description || '';
  } else {
    form.description = '';
  }
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});

// 监听 schema 变化（深度监听）
watch(() => props.schema, () => {
  if (props.isOpen) {
    resetForm();
  }
}, { deep: true, immediate: true });
</script>
