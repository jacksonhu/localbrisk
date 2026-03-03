<!-- 
  AssetBundleDialog - 创建/编辑 AssetBundle 弹窗（合并版）
  - 创建模式：新建 AssetBundle，选择类型（Local/External）
  - 编辑模式：修改 AssetBundle 描述和连接配置（仅 External 类型可改连接）
  
  类型说明：
  - Local：本地类型，不需要外部数据库连接
  - External：外部类型，必须配置外部数据库连接
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="isEditMode ? t('businessUnit.editAssetBundle') : t('businessUnit.createAssetBundle')"
    :icon="Database"
    width="lg"
    max-height="screen"
    @close="close"
  >
    <!-- 表单内容 -->
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- 说明文字（仅创建模式显示） -->
      <p v-if="!isEditMode" class="text-sm text-muted-foreground -mt-2">
        {{ t('businessUnit.assetBundleDescription') }}
      </p>

      <!-- AssetBundle 名称 -->
      <FormField
        :label="t('businessUnit.assetBundleName')"
        :error="errors.name"
        :hint="isEditMode ? t('businessUnit.assetBundleNameReadonly') : t('businessUnit.assetBundleNameHint')"
        :required="!isEditMode"
      >
        <FormInput
          v-model="form.name"
          :placeholder="t('businessUnit.assetBundleNameHint')"
          :disabled="isEditMode"
          @input="validateName"
        />
      </FormField>

      <!-- AssetBundle 类型（仅创建模式显示） -->
      <FormField
        v-if="!isEditMode"
        :label="t('businessUnit.bundleType')"
        :hint="t('businessUnit.bundleTypeHint')"
        required
      >
        <div class="flex gap-4">
          <label
            class="flex-1 flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-all"
            :class="form.bundle_type === 'local' 
              ? 'border-primary bg-primary/5 ring-2 ring-primary/20' 
              : 'border-border hover:border-muted-foreground/50'"
          >
            <input
              type="radio"
              v-model="form.bundle_type"
              value="local"
              class="sr-only"
            />
            <div class="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
              <HardDrive class="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div class="flex-1">
              <div class="font-medium">{{ t('businessUnit.bundleTypeLocal') }}</div>
              <div class="text-xs text-muted-foreground mt-0.5">{{ t('businessUnit.bundleTypeLocalDesc') }}</div>
            </div>
            <div v-if="form.bundle_type === 'local'" class="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
              <Check class="w-3 h-3 text-primary-foreground" />
            </div>
          </label>

          <label
            class="flex-1 flex items-center gap-3 p-4 border rounded-lg cursor-pointer transition-all"
            :class="form.bundle_type === 'external' 
              ? 'border-primary bg-primary/5 ring-2 ring-primary/20' 
              : 'border-border hover:border-muted-foreground/50'"
          >
            <input
              type="radio"
              v-model="form.bundle_type"
              value="external"
              class="sr-only"
            />
            <div class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <PlugZap class="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div class="flex-1">
              <div class="font-medium">{{ t('businessUnit.bundleTypeExternal') }}</div>
              <div class="text-xs text-muted-foreground mt-0.5">{{ t('businessUnit.bundleTypeExternalDesc') }}</div>
            </div>
            <div v-if="form.bundle_type === 'external'" class="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
              <Check class="w-3 h-3 text-primary-foreground" />
            </div>
          </label>
        </div>
      </FormField>

      <!-- 编辑模式显示类型标签 -->
      <div v-if="isEditMode" class="flex items-center gap-2">
        <span class="text-sm font-medium text-muted-foreground">{{ t('businessUnit.bundleType') }}:</span>
        <span 
          :class="form.bundle_type === 'local' 
            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
            : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'"
          class="px-2 py-0.5 text-xs rounded flex items-center gap-1"
        >
          <HardDrive v-if="form.bundle_type === 'local'" class="w-3 h-3" />
          <PlugZap v-else class="w-3 h-3" />
          {{ form.bundle_type === 'local' ? t('businessUnit.bundleTypeLocal') : t('businessUnit.bundleTypeExternal') }}
        </span>
        <span class="text-xs text-muted-foreground ml-2">{{ t('businessUnit.bundleTypeReadonly') }}</span>
      </div>

      <!-- 描述 -->
      <FormField
        :label="t('common.description')"
        optional
      >
        <FormTextarea
          v-model="form.description"
          :rows="2"
          :placeholder="t('detail.addDescription')"
        />
      </FormField>

      <!-- 数据库连接配置（仅 External 类型显示） -->
      <div v-if="form.bundle_type === 'external'" class="space-y-3">
        <div class="flex items-center gap-2">
          <label class="block text-sm font-medium text-foreground">
            {{ t('businessUnit.databaseConnection') }}
          </label>
          <span class="text-xs text-red-500">*</span>
        </div>

        <!-- 连接配置 -->
        <div class="p-4 bg-muted/30 rounded-lg border border-border space-y-3">
          <!-- 连接头部 -->
          <div class="flex items-center gap-2">
            <Database class="w-4 h-4 text-primary" />
            <span class="text-sm font-medium text-foreground">
              {{ t('businessUnit.connectionConfig') }}
            </span>
          </div>

          <!-- 数据库类型和名称 -->
          <div class="grid grid-cols-2 gap-3">
            <FormField :label="t('businessUnit.dbType')" label-size="xs" required>
              <FormSelect
                v-model="connection.type"
                :options="dbTypeOptions"
                @change="onDbTypeChange"
              />
            </FormField>

            <FormField :label="t('businessUnit.dbName')" label-size="xs" required :error="errors.db_name">
              <FormInput
                v-model="connection.db_name"
                placeholder="my_database"
                size="sm"
                @input="validateConnection"
              />
            </FormField>
          </div>

          <!-- 主机和端口 (仅非本地数据库显示) -->
          <div v-if="!isLocalDbType" class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <FormField :label="t('businessUnit.host')" label-size="xs" required :error="errors.host">
                <FormInput
                  v-model="connection.host"
                  placeholder="127.0.0.1"
                  size="sm"
                  @input="validateConnection"
                />
              </FormField>
            </div>
            <FormField :label="t('businessUnit.port')" label-size="xs" required :error="errors.port">
              <FormInput
                v-model.number="connection.port"
                type="number"
                :placeholder="getDefaultPort(connection.type)"
                size="sm"
                @input="validateConnection"
              />
            </FormField>
          </div>

          <!-- 用户名和密码 (仅非本地数据库显示) -->
          <div v-if="!isLocalDbType" class="grid grid-cols-2 gap-3">
            <FormField :label="t('businessUnit.username')" label-size="xs">
              <FormInput
                v-model="connection.username"
                placeholder="root"
                size="sm"
              />
            </FormField>
            <FormField :label="t('businessUnit.password')" label-size="xs">
              <FormInput
                v-model="connection.password"
                type="password"
                :placeholder="isEditMode && assetBundle?.connection ? '••••••••' : ''"
                size="sm"
              />
            </FormField>
          </div>

          <!-- 提示信息 -->
          <div class="flex items-start gap-2 pt-1 text-xs text-muted-foreground">
            <Info class="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{{ t('businessUnit.connectionHint') }}</span>
          </div>
        </div>
      </div>

      <!-- Local 类型提示 -->
      <div v-else-if="!isEditMode" class="p-4 border border-dashed border-border rounded-lg text-center">
        <HardDrive class="w-8 h-8 mx-auto text-green-500/50 mb-2" />
        <p class="text-sm text-muted-foreground">{{ t('businessUnit.localBundleHint') }}</p>
      </div>
    </form>
    
    <!-- 底部按钮 -->
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
import { Database, HardDrive, PlugZap, Info, Check } from 'lucide-vue-next';
import { BaseDialog, DialogFooter, FormField, FormInput, FormTextarea, FormSelect } from '@/components/common';
import { NAME_REGEX } from '@/utils/validationUtils';
import type { AssetBundle, AssetBundleCreate, AssetBundleUpdate, ConnectionConfig, ConnectionType, AssetBundleType } from '@/types/catalog';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  businessUnitId: string;
  assetBundle?: AssetBundle | null;  // 编辑模式时传入现有 AssetBundle
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'create', businessUnitId: string, data: AssetBundleCreate): void;
  (e: 'update', businessUnitId: string, bundleName: string, data: AssetBundleUpdate): void;
}>();

// 是否是编辑模式
const isEditMode = computed(() => !!props.assetBundle);

// 表单状态
const form = reactive<{ name: string; owner: string; description: string; bundle_type: AssetBundleType }>({
  name: '',
  owner: '',
  description: '',
  bundle_type: 'local',
});

// 连接配置
const connection = reactive<{
  type: ConnectionType;
  host: string;
  port: number;
  db_name: string;
  username: string;
  password: string;
}>({
  type: 'mysql',
  host: '127.0.0.1',
  port: 3306,
  db_name: '',
  username: '',
  password: '',
});

// 错误状态
const errors = reactive({
  name: '',
  db_name: '',
  host: '',
  port: '',
});

// 提交状态
const isSubmitting = ref(false);

// 数据库类型选项
const dbTypeOptions = [
  { value: 'mysql', label: 'MySQL' },
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'sqlite', label: 'SQLite' },
  { value: 'duckdb', label: 'DuckDB' },
];

// 是否是本地数据库类型
const isLocalDbType = computed(() => {
  return connection.type === 'sqlite' || connection.type === 'duckdb';
});

// 获取默认端口
function getDefaultPort(type: ConnectionType): string {
  const ports: Record<ConnectionType, string> = {
    mysql: '3306',
    postgresql: '5432',
    sqlite: '',
    duckdb: '',
  };
  return ports[type] || '';
}

// 数据库类型变化时更新端口
function onDbTypeChange() {
  const defaultPort = getDefaultPort(connection.type);
  if (defaultPort) {
    connection.port = parseInt(defaultPort);
  }
}

// 验证名称（仅创建模式需要）
function validateName() {
  if (isEditMode.value) return true;
  
  if (!form.name) {
    errors.name = t('errors.assetBundleNameRequired');
    return false;
  }
  if (!NAME_REGEX.test(form.name)) {
    errors.name = t('errors.assetBundleNameInvalid');
    return false;
  }
  errors.name = '';
  return true;
}

// 验证连接配置（仅 External 类型需要）
function validateConnection(): boolean {
  if (form.bundle_type !== 'external') {
    return true;
  }
  
  let valid = true;
  
  // 数据库名称是必填的
  if (!connection.db_name) {
    errors.db_name = t('errors.dbNameRequired');
    valid = false;
  } else {
    errors.db_name = '';
  }
  
  // 对于非本地数据库，主机和端口是必填的
  if (!isLocalDbType.value) {
    if (!connection.host) {
      errors.host = t('errors.hostRequired');
      valid = false;
    } else {
      errors.host = '';
    }
    
    if (!connection.port) {
      errors.port = t('errors.portRequired');
      valid = false;
    } else {
      errors.port = '';
    }
  }
  
  return valid;
}

// 表单是否有效
const isValid = computed(() => {
  if (isEditMode.value) {
    // 编辑模式：External 类型需要验证连接配置
    if (form.bundle_type === 'external') {
      return connection.db_name && (isLocalDbType.value || (connection.host && connection.port));
    }
    return true;
  }
  // 创建模式
  const nameValid = form.name && NAME_REGEX.test(form.name);
  if (form.bundle_type === 'local') {
    return nameValid;
  }
  // External 类型必须有有效的连接配置
  const connValid = connection.db_name && (isLocalDbType.value || (connection.host && connection.port));
  return nameValid && connValid;
});

// 关闭弹窗
function close() {
  emit('close');
}

// 构建连接配置对象
function buildConnectionConfig(): ConnectionConfig | undefined {
  if (form.bundle_type !== 'external') {
    return undefined;
  }
  
  const connConfig: ConnectionConfig = {
    type: connection.type,
    port: connection.port,
    db_name: connection.db_name,
  };
  
  // 仅为非本地数据库添加额外字段
  if (!isLocalDbType.value) {
    connConfig.host = connection.host;
    if (connection.username) connConfig.username = connection.username;
    if (connection.password) connConfig.password = connection.password;
  }
  
  return connConfig;
}

// 提交表单
async function handleSubmit() {
  if (isSubmitting.value) return;
  
  if (isEditMode.value) {
    // 编辑模式
    if (!props.assetBundle) return;
    
    isSubmitting.value = true;
    try {
      const data: AssetBundleUpdate = {};
      
      // 描述变化
      if (form.description !== (props.assetBundle.description || '')) {
        data.description = form.description || undefined;
      }
      
      // 连接配置变化（仅 External 类型）
      if (form.bundle_type === 'external') {
        const newConnection = buildConnectionConfig();
        const hasConnectionChanged = JSON.stringify(newConnection) !== JSON.stringify(props.assetBundle.connection);
        if (hasConnectionChanged) {
          data.connection = newConnection;
        }
      }
      
      emit('update', props.businessUnitId, props.assetBundle.name, data);
    } finally {
      isSubmitting.value = false;
    }
  } else {
    // 创建模式
    if (!validateName()) return;
    if (form.bundle_type === 'external' && !validateConnection()) return;

    isSubmitting.value = true;
    try {
      const data: AssetBundleCreate = {
        name: form.name,
        bundle_type: form.bundle_type,
      };
      
      if (form.owner) {
        data.owner = form.owner;
      }
      if (form.description) {
        data.description = form.description;
      }
      
      // External 类型添加连接配置
      if (form.bundle_type === 'external') {
        data.connection = buildConnectionConfig();
      }
      
      emit('create', props.businessUnitId, data);
    } finally {
      isSubmitting.value = false;
    }
  }
}

// 重置表单
function resetForm() {
  if (props.assetBundle) {
    // 编辑模式：从现有 AssetBundle 加载数据
    form.name = props.assetBundle.name;
    form.description = props.assetBundle.description || '';
    form.owner = props.assetBundle.owner || '';
    form.bundle_type = props.assetBundle.bundle_type || 'local';
    
    // 加载连接配置（仅 External 类型）
    if (props.assetBundle.bundle_type === 'external' && props.assetBundle.connection) {
      connection.type = props.assetBundle.connection.type;
      connection.host = props.assetBundle.connection.host || '127.0.0.1';
      connection.port = props.assetBundle.connection.port || 3306;
      connection.db_name = props.assetBundle.connection.db_name || '';
      connection.username = props.assetBundle.connection.username || '';
      connection.password = ''; // 密码不回显
    } else {
      connection.type = 'mysql';
      connection.host = '127.0.0.1';
      connection.port = 3306;
      connection.db_name = '';
      connection.username = '';
      connection.password = '';
    }
  } else {
    // 创建模式：重置为空
    form.name = '';
    form.owner = '';
    form.description = '';
    form.bundle_type = 'local';
    connection.type = 'mysql';
    connection.host = '127.0.0.1';
    connection.port = 3306;
    connection.db_name = '';
    connection.username = '';
    connection.password = '';
  }
  // 清除错误
  errors.name = '';
  errors.db_name = '';
  errors.host = '';
  errors.port = '';
}

// 监听弹窗打开/关闭
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    resetForm();
  }
});

// 监听 assetBundle 变化（编辑模式）
watch(() => props.assetBundle, () => {
  if (props.isOpen) {
    resetForm();
  }
}, { deep: true });
</script>
