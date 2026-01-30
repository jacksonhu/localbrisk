<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[560px] max-h-[85vh] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-lg font-semibold text-foreground">
              {{ isEditMode ? t('catalog.editCatalog') : t('catalog.createCatalog') }}
            </h2>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 表单内容 -->
          <form @submit.prevent="handleSubmit" class="p-6 space-y-5 overflow-y-auto max-h-[65vh]">
            <!-- Catalog 名称 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('catalog.catalogName') }}
                <span class="text-red-500">*</span>
              </label>
              <input
                v-model="form.name"
                type="text"
                :placeholder="t('catalog.catalogNameHint')"
                :disabled="isEditMode"
                class="w-full px-3 py-2 bg-background border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-60 disabled:cursor-not-allowed"
                :class="errors.name ? 'border-red-500' : 'border-input'"
                @input="validateName"
              />
              <p v-if="errors.name" class="text-xs text-red-500">{{ errors.name }}</p>
              <p v-else class="text-xs text-muted-foreground">
                {{ isEditMode ? t('catalog.catalogNameReadonly') : t('catalog.catalogNameHint') }}
              </p>
            </div>

            <!-- 显示名称 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('catalog.catalogDisplayName') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <input
                v-model="form.display_name"
                type="text"
                :placeholder="t('catalog.catalogDisplayNameHint')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <!-- 描述 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                {{ t('common.description') }}
                <span class="text-muted-foreground text-xs ml-1">({{ t('common.optional') }})</span>
              </label>
              <textarea
                v-model="form.description"
                rows="2"
                :placeholder="t('detail.addDescription')"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              ></textarea>
            </div>

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
                  <div class="space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.dbType') }} *</label>
                    <select
                      v-model="connection.type"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="mysql">MySQL</option>
                      <option value="postgresql">PostgreSQL</option>
                      <option value="sqlite">SQLite</option>
                      <option value="duckdb">DuckDB</option>
                    </select>
                  </div>

                  <!-- 数据库名称 -->
                  <div class="space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.dbName') }}</label>
                    <input
                      v-model="connection.db_name"
                      type="text"
                      placeholder="my_database"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>

                <!-- 主机和端口 (仅非本地数据库显示) -->
                <div v-if="connection.type !== 'sqlite' && connection.type !== 'duckdb'" class="grid grid-cols-3 gap-3">
                  <div class="col-span-2 space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.host') }} *</label>
                    <input
                      v-model="connection.host"
                      type="text"
                      placeholder="127.0.0.1"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.port') }} *</label>
                    <input
                      v-model.number="connection.port"
                      type="number"
                      :placeholder="getDefaultPort(connection.type)"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>

                <!-- 用户名和密码 (仅非本地数据库显示) -->
                <div v-if="connection.type !== 'sqlite' && connection.type !== 'duckdb'" class="grid grid-cols-2 gap-3">
                  <div class="space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.username') }}</label>
                    <input
                      v-model="connection.username"
                      type="text"
                      placeholder="root"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div class="space-y-1.5">
                    <label class="text-xs text-muted-foreground">{{ t('catalog.password') }}</label>
                    <input
                      v-model="connection.password"
                      type="password"
                      placeholder="••••••••"
                      class="w-full px-2.5 py-1.5 bg-background border border-input rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
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
              {{ isEditMode ? t('common.save') : t('common.create') }}
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
import { X, Loader2, Plus, Trash2, Database } from 'lucide-vue-next';
import type { Catalog, CatalogCreate, CatalogUpdate, ConnectionConfig, ConnectionType } from '@/types/catalog';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
  catalog?: Catalog | null;  // 编辑模式传入已有 catalog
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

// 名称验证正则
const nameRegex = /^[a-zA-Z][a-zA-Z0-9_]*$/;

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
  if (!nameRegex.test(form.name)) {
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
    // 编辑模式只验证连接配置
    return validateConnection();
  }
  return form.name && nameRegex.test(form.name) && validateConnection();
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
