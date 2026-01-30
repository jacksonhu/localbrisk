<!--
  CreateCatalogDialog - 创建/编辑 Catalog 弹窗
  使用 BaseDialog 和公共表单组件
-->
<template>
  <BaseDialog
    :is-open="isOpen"
    :title="isEditMode ? t('catalog.editCatalog') : t('catalog.createCatalog')"
    :icon="Database"
    width="xl"
    max-height="screen"
    @close="close"
  >
    <form @submit.prevent="handleSubmit" class="space-y-5">
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
          :rows="2"
        />
      </FormField>

      <!-- 数据库连接配置 -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="block text-sm font-medium text-foreground">
            {{ t('catalog.databaseConnection') }}
            <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
          </label>
          <button
            v-if="!connection"
            type="button"
            @click="addConnection"
            class="flex items-center gap-1 px-2 py-1 text-xs text-primary hover:bg-primary/10 rounded-md transition-colors"
          >
            <Plus class="w-3.5 h-3.5" />
            {{ t('catalog.addConnection') }}
          </button>
        </div>

        <!-- 连接配置 -->
        <div v-if="connection" class="p-4 bg-muted/30 rounded-lg border border-border space-y-3">
          <!-- 连接头部 -->
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-foreground">
              {{ t('catalog.connectionConfig') }}
            </span>
            <button
              type="button"
              @click="removeConnection"
              class="p-1 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>

          <!-- 数据库类型和名称 -->
          <div class="grid grid-cols-2 gap-3">
            <FormField :label="t('catalog.dbType')" label-size="xs" required>
              <FormSelect
                v-model="connection.type"
                :options="dbTypeOptions"
              />
            </FormField>

            <FormField :label="t('catalog.dbName')" label-size="xs">
              <FormInput
                v-model="connection.db_name"
                placeholder="my_database"
                size="sm"
              />
            </FormField>
          </div>

          <!-- 主机和端口 (仅非本地数据库显示) -->
          <div v-if="!isLocalDbType" class="grid grid-cols-3 gap-3">
            <div class="col-span-2">
              <FormField :label="t('catalog.host')" label-size="xs" required>
                <FormInput
                  v-model="connection.host"
                  placeholder="127.0.0.1"
                  size="sm"
                />
              </FormField>
            </div>
            <FormField :label="t('catalog.port')" label-size="xs" required>
              <FormInput
                v-model.number="connection.port"
                type="number"
                :placeholder="getDefaultPort(connection.type)"
                size="sm"
              />
            </FormField>
          </div>

          <!-- 用户名和密码 (仅非本地数据库显示) -->
          <div v-if="!isLocalDbType" class="grid grid-cols-2 gap-3">
            <FormField :label="t('catalog.username')" label-size="xs">
              <FormInput
                v-model="connection.username"
                placeholder="root"
                size="sm"
              />
            </FormField>
            <FormField :label="t('catalog.password')" label-size="xs">
              <FormInput
                v-model="connection.password"
                type="password"
                placeholder="••••••••"
                size="sm"
              />
            </FormField>
          </div>

          <!-- 同步 Schema 选项 -->
          <div class="flex items-center gap-2 pt-1">
            <input
              id="sync-schema"
              v-model="connection.sync_schema"
              type="checkbox"
              class="w-4 h-4 rounded border-input text-primary focus:ring-primary"
            />
            <label for="sync-schema" class="text-xs text-muted-foreground">
              {{ t('catalog.syncSchema') }}
            </label>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-else class="p-4 border border-dashed border-border rounded-lg text-center">
          <Database class="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
          <p class="text-xs text-muted-foreground">{{ t('catalog.noConnections') }}</p>
        </div>
      </div>
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
import { Plus, Trash2, Database } from 'lucide-vue-next';
import type { Catalog, CatalogCreate, CatalogUpdate, ConnectionConfig, ConnectionType } from '@/types/catalog';
import { NAME_REGEX } from '@/utils/validationUtils';
import BaseDialog from '@/components/common/BaseDialog.vue';
import DialogFooter from '@/components/common/DialogFooter.vue';
import FormField from '@/components/common/FormField.vue';
import FormInput from '@/components/common/FormInput.vue';
import FormTextarea from '@/components/common/FormTextarea.vue';
import FormSelect from '@/components/common/FormSelect.vue';

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

// 数据库连接（单个）
const connection = ref<ConnectionConfig | null>(null);

// 错误状态
const errors = reactive({
  name: '',
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
  return connection.value?.type === 'sqlite' || connection.value?.type === 'duckdb';
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

// 添加连接
function addConnection() {
  connection.value = {
    type: 'mysql',
    host: '127.0.0.1',
    port: 3306,
    db_name: '',
    username: '',
    password: '',
    sync_schema: true,
  };
}

// 删除连接
function removeConnection() {
  connection.value = null;
}

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

// 验证连接配置
function validateConnection(): boolean {
  if (!connection.value) {
    return true; // 连接是可选的
  }
  const conn = connection.value;
  // 对于非本地数据库，主机和端口是必填的
  if (conn.type !== 'sqlite' && conn.type !== 'duckdb') {
    if (!conn.host || !conn.port) {
      return false;
    }
  }
  return true;
}

// 表单是否有效
const isValid = computed(() => {
  if (isEditMode.value) {
    return validateConnection();
  }
  return form.name && NAME_REGEX.test(form.name) && validateConnection();
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
  
  if (!validateConnection()) {
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
      
      // 处理连接配置更新
      if (connection.value) {
        const conn = connection.value;
        const config: ConnectionConfig = {
          type: conn.type,
          port: conn.port,
          db_name: conn.db_name || '',
          sync_schema: conn.sync_schema,
        };
        
        // 仅为非本地数据库添加额外字段
        if (conn.type !== 'sqlite' && conn.type !== 'duckdb') {
          config.host = conn.host;
          if (conn.username) config.username = conn.username;
          if (conn.password) config.password = conn.password;
        }
        
        updateData.connections = [config];
      } else {
        // 如果之前有连接配置，现在删除了，则设置为空数组
        if (props.catalog.connections && props.catalog.connections.length > 0) {
          updateData.connections = [];
        }
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
      
      // 添加连接配置
      if (connection.value) {
        const conn = connection.value;
        const config: ConnectionConfig = {
          type: conn.type,
          port: conn.port,
          db_name: conn.db_name || '',
          sync_schema: conn.sync_schema,
        };
        
        // 仅为非本地数据库添加额外字段
        if (conn.type !== 'sqlite' && conn.type !== 'duckdb') {
          config.host = conn.host;
          if (conn.username) config.username = conn.username;
          if (conn.password) config.password = conn.password;
        }
        
        data.connections = [config];
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
    // 加载已有的连接配置
    if (props.catalog.connections && props.catalog.connections.length > 0) {
      const existingConn = props.catalog.connections[0];
      connection.value = {
        type: existingConn.type,
        host: existingConn.host || '127.0.0.1',
        port: existingConn.port,
        db_name: existingConn.db_name || '',
        username: existingConn.username || '',
        password: existingConn.password || '',
        sync_schema: existingConn.sync_schema ?? true,
      };
    } else {
      connection.value = null;
    }
  } else {
    form.name = '';
    form.display_name = '';
    form.description = '';
    connection.value = null;
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
