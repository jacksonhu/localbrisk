<!--
  CreateCatalogDialog - 创建/编辑 Catalog 弹窗
  使用 BaseDialog 和公共表单组件
  Catalog 不再包含 connections 和 allow_custom_schema
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="isEditMode ? t('catalog.editCatalog') : t('catalog.createCatalog')"
    :icon="Folder"
    width="md"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- 说明文字（仅创建模式显示） -->
      <p v-if="!isEditMode" class="text-sm text-muted-foreground -mt-2">
        {{ t('catalog.catalogDescription') }}
      </p>

      <!-- Catalog 名称 -->
      <FormField
        :label="t('catalog.catalogName')"
        :error="errors.name"
        :hint="isEditMode ? t('catalog.catalogNameReadonly') : t('catalog.catalogNameHint')"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('catalog.catalogNameHint')"
          :disabled="isEditMode"
          :error="!!errors.name"
          @input="validateName"
        />
      </FormField>

      <!-- 显示名称 -->
      <FormField
        :label="t('catalog.catalogDisplayName')"
        optional
      >
        <FormInput
          v-model="form.display_name"
          :placeholder="t('catalog.catalogDisplayNameHint')"
        />
      </FormField>

      <!-- 描述 -->
      <FormField
        :label="t('common.description')"
        optional
      >
        <FormTextarea
          v-model="form.description"
          :placeholder="t('detail.addDescription')"
          :rows="3"
        />
      </FormField>
    </form>

    <template #footer>
      <DialogFooter
        :submitting="isSubmitting"
        :disabled="!isValid"
        :submit-text="isEditMode ? t('common.save') : t('common.create')"
        @cancel="close"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Folder } from 'lucide-vue-next';
import type { Catalog, CatalogCreate, CatalogUpdate } from '@/types/catalog';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';
import FormTextarea from '@/components/common/FormTextarea.vue';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalog?: Catalog | null;
}>();

// 是否是编辑模式
const isEditMode = computed(() => !!props.catalog);

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', data: CatalogCreate): void;
  (e: 'update', catalogId: string, data: CatalogUpdate): void;
}>();

// 表单状态
const form = reactive({
  name: '',
  display_name: '',
  description: '',
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
    errors.name = t('errors.catalogNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.catalogNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  if (isEditMode.value) {
    return true;
  }
  return form.name && NAME_REGEX.test(form.name);
});

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  if (isSubmitting.value) {
    return;
  }
  
  if (!isEditMode.value && !validateName()) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    if (isEditMode.value && props.catalog) {
      // 编辑模式 - 发送更新请求
      const updateData: CatalogUpdate = {};
      
      if (form.display_name !== props.catalog.display_name) {
        updateData.display_name = form.display_name || undefined;
      }
      if (form.description !== (props.catalog.description || '')) {
        updateData.description = form.description || undefined;
      }
      
      emit('update', props.catalog.id, updateData);
    } else {
      // 创建模式
      const data: CatalogCreate = {
        name: form.name,
      };
      
      if (form.display_name) {
        data.display_name = form.display_name;
      }
      if (form.description) {
        data.description = form.description;
      }
      
      emit('submit', data);
    }
  } finally {
    isSubmitting.value = false;
  }
}

// 初始化表单（编辑模式时填充数据）
function initForm() {
  if (props.catalog) {
    form.name = props.catalog.name;
    form.display_name = props.catalog.display_name || '';
    form.description = props.catalog.description || '';
  } else {
    form.name = '';
    form.display_name = '';
    form.description = '';
  }
  errors.name = '';
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    initForm();
  }
});
</script>
