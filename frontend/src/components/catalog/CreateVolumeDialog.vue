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
            <h2 class="text-lg font-semibold text-foreground">
              {{ t('asset.createVolume') }}
            </h2>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 表单内容 -->
          <form @submit.prevent="handleSubmit" class="p-6 space-y-5 max-h-[calc(85vh-140px)] overflow-y-auto">
            <!-- Volume 名称 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('asset.volumeName') }}
                <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                :placeholder="t('asset.volumeNameHint')"
                class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                :class="errors.name ? 'border-red-500' : 'border-input'"
                @input="validateName"
              />
              <p v-if="errors.name" class="text-xs text-red-500">{{ errors.name }}</p>
              <p v-else class="text-xs text-muted-foreground">{{ t('asset.volumeNameHint') }}</p>
            </div>

            <!-- Volume 类型 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('asset.volumeType') }}
              </label>
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
              <p class="text-xs text-muted-foreground">
                {{ form.volume_type === 'local' ? t('asset.volumeTypeLocalDesc') : t('asset.volumeTypeS3Desc') }}
              </p>
            </div>

            <!-- 本地存储路径（仅 local 类型） -->
            <div v-if="form.volume_type === 'local'" class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('asset.storageLocation') }}
                <span class="text-red-500">*</span>
              </label>
              <div class="flex gap-2">
                <input
                  v-model="form.storage_location"
                  type="text"
                  :placeholder="t('asset.storageLocationHint')"
                  class="flex-1 px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  :class="errors.storage_location ? 'border-red-500' : 'border-input'"
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
              <p v-if="errors.storage_location" class="text-xs text-red-500">{{ errors.storage_location }}</p>
              <p v-else class="text-xs text-muted-foreground">{{ t('asset.storageLocationHint') }}</p>
            </div>

            <!-- S3 配置（仅 s3 类型） -->
            <template v-if="form.volume_type === 's3'">
              <!-- S3 Endpoint -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('asset.s3Endpoint') }}
                  <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="form.s3_endpoint"
                  type="text"
                  :placeholder="t('asset.s3EndpointHint')"
                  class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  :class="errors.s3_endpoint ? 'border-red-500' : 'border-input'"
                  @input="validateS3Fields"
                />
                <p v-if="errors.s3_endpoint" class="text-xs text-red-500">{{ errors.s3_endpoint }}</p>
                <p v-else class="text-xs text-muted-foreground">{{ t('asset.s3EndpointHint') }}</p>
              </div>

              <!-- S3 Bucket -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('asset.s3Bucket') }}
                  <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="form.s3_bucket"
                  type="text"
                  :placeholder="t('asset.s3BucketHint')"
                  class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  :class="errors.s3_bucket ? 'border-red-500' : 'border-input'"
                  @input="validateS3Fields"
                />
                <p v-if="errors.s3_bucket" class="text-xs text-red-500">{{ errors.s3_bucket }}</p>
              </div>

              <!-- S3 Access Key -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('asset.s3AccessKey') }}
                  <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="form.s3_access_key"
                  type="text"
                  :placeholder="t('asset.s3AccessKeyHint')"
                  class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                  :class="errors.s3_access_key ? 'border-red-500' : 'border-input'"
                  @input="validateS3Fields"
                />
                <p v-if="errors.s3_access_key" class="text-xs text-red-500">{{ errors.s3_access_key }}</p>
              </div>

              <!-- S3 Secret Key -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-foreground">
                  {{ t('asset.s3SecretKey') }}
                  <span class="text-red-500">*</span>
                </label>
                <div class="relative">
                  <input
                    v-model="form.s3_secret_key"
                    :type="showSecretKey ? 'text' : 'password'"
                    :placeholder="t('asset.s3SecretKeyHint')"
                    class="w-full px-3 py-2 pr-10 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                    :class="errors.s3_secret_key ? 'border-red-500' : 'border-input'"
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
                <p v-if="errors.s3_secret_key" class="text-xs text-red-500">{{ errors.s3_secret_key }}</p>
              </div>
            </template>

            <!-- 描述 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('common.description') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <textarea
                v-model="form.description"
                rows="3"
                :placeholder="t('detail.addDescription')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              ></textarea>
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
import { X, Loader2, FolderOpen, Cloud, Eye, EyeOff } from 'lucide-vue-next';
import type { AssetCreate, VolumeType } from '@/types/catalog';

const { t } = useI18n();

// 检测是否在 Tauri 环境中
const isTauriEnv = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

// Props
const props = defineProps<{
  isOpen: boolean;
  catalogId: string;
  schemaName: string;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'submit', catalogId: string, schemaName: string, data: AssetCreate): void;
}>();

// 表单状态
const form = reactive({
  name: '',
  volume_type: 'local' as VolumeType,
  storage_location: '',
  // S3 配置
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

// 显示密钥
const showSecretKey = ref(false);

// 名称验证正则
const nameRegex = /^[a-zA-Z][a-zA-Z0-9_]*$/;

// 验证名称
function validateName() {
  if (!form.name) {
    errors.name = t('errors.volumeNameRequired');
    return false;
  }
  if (!nameRegex.test(form.name)) {
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
  if (!form.name || !nameRegex.test(form.name)) {
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
    // 非 Tauri 环境，提示用户手动输入路径
    console.warn('Folder picker is only available in Tauri app. Please enter the path manually.');
    return;
  }
  
  try {
    // 动态导入 Tauri dialog 插件
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
    
    emit('submit', props.catalogId, props.schemaName, data);
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
