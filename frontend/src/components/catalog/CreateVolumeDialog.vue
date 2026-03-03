<!--
  CreateVolumeDialog - 创建 Volume 弹窗
  支持本地存储和 S3 存储两种模式
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="t('asset.createVolume')"
    :icon="HardDrive"
    width="lg"
    max-height="screen"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Volume 名称 -->
      <FormField
        :label="t('asset.volumeName')"
        :error="errors.name"
        :hint="t('asset.volumeNameHint')"
        required
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('asset.volumeNameHint')"
          :error="!!errors.name"
          @input="validateName"
        />
      </FormField>

      <!-- Volume 类型 -->
      <FormField :label="t('asset.volumeType')">
        <div class="flex gap-4">
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="form.volume_type"
              type="radio"
              value="local"
              class="w-4 h-4 text-primary"
            />
            <div class="flex items-center gap-1.5">
              <FolderOpen class="w-4 h-4 text-muted-foreground" />
              <span class="text-sm">{{ t('asset.volumeTypeLocal') }}</span>
            </div>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="form.volume_type"
              type="radio"
              value="s3"
              class="w-4 h-4 text-primary"
            />
            <div class="flex items-center gap-1.5">
              <Cloud class="w-4 h-4 text-muted-foreground" />
              <span class="text-sm">{{ t('asset.volumeTypeS3') }}</span>
            </div>
          </label>
        </div>
        <p class="text-xs text-muted-foreground mt-2">
          {{ form.volume_type === 'local' ? t('asset.volumeTypeLocalDesc') : t('asset.volumeTypeS3Desc') }}
        </p>
      </FormField>

      <!-- 本地存储路径（仅 local 类型） -->
      <FormField
        v-if="form.volume_type === 'local'"
        :label="t('asset.storageLocation')"
        :error="errors.storage_location"
        :hint="t('asset.storageLocationHint')"
        required
      >
        <div class="flex gap-2">
          <FormInput
            v-model="form.storage_location"
            :placeholder="t('asset.storageLocationHint')"
            :error="!!errors.storage_location"
            class="flex-1"
            @input="validateStorageLocation"
          />
          <button
            type="button"
            @click="handleSelectFolder"
            :disabled="!isTauriEnv"
            :title="!isTauriEnv ? t('asset.folderPickerDisabled') : ''"
            class="px-3 py-2 text-sm border border-input rounded-lg transition-colors flex items-center gap-2"
            :class="isTauriEnv ? 'hover:bg-muted' : 'opacity-50 cursor-not-allowed'"
          >
            <FolderOpen class="w-4 h-4" />
            {{ t('asset.selectFolder') }}
          </button>
        </div>
      </FormField>

      <!-- S3 配置（仅 s3 类型） -->
      <template v-if="form.volume_type === 's3'">
        <!-- S3 Endpoint -->
        <FormField
          :label="t('asset.s3Endpoint')"
          :error="errors.s3_endpoint"
          :hint="t('asset.s3EndpointHint')"
          required
        >
          <FormInput
            v-model="form.s3_endpoint"
            :placeholder="t('asset.s3EndpointHint')"
            :error="!!errors.s3_endpoint"
            @input="validateS3Fields"
          />
        </FormField>

        <!-- S3 Bucket -->
        <FormField
          :label="t('asset.s3Bucket')"
          :error="errors.s3_bucket"
          required
        >
          <FormInput
            v-model="form.s3_bucket"
            :placeholder="t('asset.s3BucketHint')"
            :error="!!errors.s3_bucket"
            @input="validateS3Fields"
          />
        </FormField>

        <!-- S3 Access Key -->
        <FormField
          :label="t('asset.s3AccessKey')"
          :error="errors.s3_access_key"
          required
        >
          <FormInput
            v-model="form.s3_access_key"
            :placeholder="t('asset.s3AccessKeyHint')"
            :error="!!errors.s3_access_key"
            class="font-mono"
            @input="validateS3Fields"
          />
        </FormField>

        <!-- S3 Secret Key -->
        <FormField
          :label="t('asset.s3SecretKey')"
          :error="errors.s3_secret_key"
          required
        >
          <div class="relative">
            <FormInput
              v-model="form.s3_secret_key"
              :type="showSecretKey ? 'text' : 'password'"
              :placeholder="t('asset.s3SecretKeyHint')"
              :error="!!errors.s3_secret_key"
              class="font-mono pr-10"
              @input="validateS3Fields"
            />
            <button
              type="button"
              @click="showSecretKey = !showSecretKey"
              class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
            >
              <Eye v-if="!showSecretKey" class="w-4 h-4" />
              <EyeOff v-else class="w-4 h-4" />
            </button>
          </div>
        </FormField>
      </template>

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
        @cancel="close"
        @submit="handleSubmit"
      />
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { FolderOpen, Cloud, Eye, EyeOff, HardDrive } from 'lucide-vue-next';
import type { AssetCreate, VolumeType } from '@/types/catalog';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';
import FormTextarea from '@/components/common/FormTextarea.vue';

const { t } = useI18n();

// 检测是否在 Tauri 环境中
const isTauriEnv = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

// Props
const props = defineProps<{
  isOpen: boolean;
  businessUnitId: string;
  bundleName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', businessUnitId: string, bundleName: string, data: AssetCreate): void;
}>();

// 表单状态
const form = reactive({
  name: '',
  volume_type: 'local' as VolumeType,
  storage_location: '',
  s3_endpoint: '',
  s3_bucket: '',
  s3_access_key: '',
  s3_secret_key: '',
  description: '',
});

// 错误状态
const errors = reactive({
  name: '',
  storage_location: '',
  s3_endpoint: '',
  s3_bucket: '',
  s3_access_key: '',
  s3_secret_key: '',
});

// 提交状态
const isSubmitting = ref(false);
const showSecretKey = ref(false);

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.volumeNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.volumeNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 验证存储路径
function validateStorageLocation() {
  if (form.volume_type === 'local' && !form.storage_location) {
    errors.storage_location = t('errors.storageLocationRequired');
    return false;
  }
  errors.storage_location = '';
  return true;
}

// 验证 S3 字段
function validateS3Fields() {
  let valid = true;
  
  if (form.volume_type === 's3') {
    if (!form.s3_endpoint) {
      errors.s3_endpoint = t('errors.s3EndpointRequired');
      valid = false;
    } else {
      errors.s3_endpoint = '';
    }
    
    if (!form.s3_bucket) {
      errors.s3_bucket = t('errors.s3BucketRequired');
      valid = false;
    } else {
      errors.s3_bucket = '';
    }
    
    if (!form.s3_access_key) {
      errors.s3_access_key = t('errors.s3AccessKeyRequired');
      valid = false;
    } else {
      errors.s3_access_key = '';
    }
    
    if (!form.s3_secret_key) {
      errors.s3_secret_key = t('errors.s3SecretKeyRequired');
      valid = false;
    } else {
      errors.s3_secret_key = '';
    }
  }
  
  return valid;
}

// 表单是否有效
const isValid = computed(() => {
  if (!form.name || !NAME_REGEX.test(form.name)) {
    return false;
  }
  
  if (form.volume_type === 'local') {
    if (!form.storage_location) {
      return false;
    }
  } else if (form.volume_type === 's3') {
    if (!form.s3_endpoint || !form.s3_bucket || !form.s3_access_key || !form.s3_secret_key) {
      return false;
    }
  }
  
  return true;
});

// 选择文件夹
async function handleSelectFolder() {
  if (!isTauriEnv) {
    console.warn('Folder picker is only available in Tauri app. Please enter the path manually.');
    return;
  }
  
  try {
    const { open } = await import('@tauri-apps/plugin-dialog');
    const selected = await open({
      directory: true,
      multiple: false,
      title: t('asset.selectFolder'),
    });
    
    if (selected) {
      form.storage_location = selected as string;
      validateStorageLocation();
    }
  } catch (e) {
    console.error('Failed to select folder:', e);
  }
}

// 关闭弹窗
function close() {
  emit('close');
}

// 提交表单
async function handleSubmit() {
  const nameValid = validateName();
  const locationValid = form.volume_type === 'local' ? validateStorageLocation() : true;
  const s3Valid = form.volume_type === 's3' ? validateS3Fields() : true;
  
  if (!nameValid || !locationValid || !s3Valid || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  
  try {
    const data: AssetCreate = {
      name: form.name,
      asset_type: 'volume',
      volume_type: form.volume_type,
    };
    
    if (form.volume_type === 'local') {
      data.storage_location = form.storage_location;
    } else if (form.volume_type === 's3') {
      data.s3_endpoint = form.s3_endpoint;
      data.s3_bucket = form.s3_bucket;
      data.s3_access_key = form.s3_access_key;
      data.s3_secret_key = form.s3_secret_key;
    }
    
    if (form.description) {
      data.description = form.description;
    }
    
    emit('submit', props.businessUnitId, props.bundleName, data);
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  form.name = '';
  form.volume_type = 'local';
  form.storage_location = '';
  form.s3_endpoint = '';
  form.s3_bucket = '';
  form.s3_access_key = '';
  form.s3_secret_key = '';
  form.description = '';
  errors.name = '';
  errors.storage_location = '';
  errors.s3_endpoint = '';
  errors.s3_bucket = '';
  errors.s3_access_key = '';
  errors.s3_secret_key = '';
  showSecretKey.value = false;
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});
</script>
