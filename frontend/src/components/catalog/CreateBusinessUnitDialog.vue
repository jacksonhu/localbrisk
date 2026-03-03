<!--
  CreateBusinessUnitDialog - 创建/编辑 Business Unit 弹窗
  使用 BaseDialog 和公共表单组件
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="isEditMode ? t('businessUnit.editBusinessUnit') : t('businessUnit.createBusinessUnit')"
    :icon="Folder"
    width="md"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- 说明文字（仅创建模式显示） -->
      <p v-if="!isEditMode" class="text-sm text-muted-foreground -mt-2">
        {{ t('businessUnit.businessUnitDescription') }}
      </p>

      <!-- Business Unit 名称 -->
      <FormField
        :label="t('businessUnit.businessUnitName')"
        :error="errors.name"
        :hint="isEditMode ? t('businessUnit.businessUnitNameReadonly') : t('businessUnit.businessUnitNameHint')"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('businessUnit.businessUnitNameHint')"
          :disabled="isEditMode"
          :error="!!errors.name"
          @input="validateName"
        />
      </FormField>

      <!-- 显示名称 -->
      <FormField
        :label="t('businessUnit.businessUnitDisplayName')"
        optional
      >
        <FormInput
          v-model="form.display_name"
          :placeholder="t('businessUnit.businessUnitDisplayNameHint')"
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
import type { BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate } from '@/types/catalog';
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
  businessUnit?: BusinessUnit | null;
}>();

// 是否是编辑模式
const isEditMode = computed(() => !!props.businessUnit);

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', data: BusinessUnitCreate): void;
  (e: 'update', businessUnitId: string, data: BusinessUnitUpdate): void;
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
    errors.name = t('errors.businessUnitNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.businessUnitNameInvalid');
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
    if (isEditMode.value && props.businessUnit) {
      // 编辑模式 - 发送更新请求
      const updateData: BusinessUnitUpdate = {};
      
      if (form.display_name !== props.businessUnit.display_name) {
        updateData.display_name = form.display_name || undefined;
      }
      if (form.description !== (props.businessUnit.description || '')) {
        updateData.description = form.description || undefined;
      }
      
      emit('update', props.businessUnit.id, updateData);
    } else {
      // 创建模式
      const data: BusinessUnitCreate = {
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
  if (props.businessUnit) {
    form.name = props.businessUnit.name;
    form.display_name = props.businessUnit.display_name || '';
    form.description = props.businessUnit.description || '';
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
