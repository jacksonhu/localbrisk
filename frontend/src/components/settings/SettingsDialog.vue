<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- 背景遮罩 -->
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close"></div>
        
        <!-- 弹窗内容 -->
        <div class="relative bg-card rounded-xl shadow-float-lg w-[500px] max-h-[80vh] overflow-hidden">
          <!-- 标题栏 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="text-lg font-semibold text-foreground">{{ t('settings.title') }}</h2>
            <button
              @click="close"
              class="p-1.5 rounded-lg hover:bg-muted transition-colors"
            >
              <X class="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
          
          <!-- 设置内容 -->
          <div class="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
            <!-- 语言设置 -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-foreground">
                <div class="flex items-center gap-2 mb-2">
                  <Globe class="w-4 h-4 text-muted-foreground" />
                  <span>{{ t('settings.language') }}</span>
                </div>
              </label>
              <select
                v-model="settings.language"
                class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option v-for="locale in supportedLocales" :key="locale.code" :value="locale.code">
                  {{ locale.nativeName }}
                </option>
              </select>
              <p class="text-xs text-muted-foreground">{{ t('settings.languageDescription') }}</p>
            </div>

            <!-- 分隔线 -->
            <div class="border-t border-border"></div>

            <!-- 本地模型设置 -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <Cpu class="w-4 h-4 text-muted-foreground" />
                  <label class="text-sm font-medium text-foreground">{{ t('settings.enableLocalModel') }}</label>
                </div>
                <button
                  @click="settings.enableLocalModel = !settings.enableLocalModel"
                  :class="[
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    settings.enableLocalModel ? 'bg-primary' : 'bg-muted'
                  ]"
                >
                  <span
                    :class="[
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      settings.enableLocalModel ? 'translate-x-6' : 'translate-x-1'
                    ]"
                  />
                </button>
              </div>
              <p class="text-xs text-muted-foreground">
                {{ t('settings.localModelDescription') }}
              </p>

              <!-- 本地模型选择 (仅在启用时显示) -->
              <Transition name="slide">
                <div v-if="settings.enableLocalModel" class="space-y-3 pl-6 border-l-2 border-primary/30">
                  <div class="space-y-2">
                    <label class="block text-sm font-medium text-foreground">
                      {{ t('settings.selectModel') }}
                    </label>
                    <select
                      v-model="settings.localModel"
                      class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">{{ t('settings.selectModelPlaceholder') }}</option>
                      <optgroup :label="t('settings.ollamaModels')">
                        <option v-for="model in ollamaModels" :key="model.name" :value="model.name">
                          {{ model.name }} {{ model.size ? `(${model.size})` : '' }}
                        </option>
                      </optgroup>
                      <optgroup :label="t('settings.otherModels')">
                        <option value="custom">{{ t('settings.customModel') }}</option>
                      </optgroup>
                    </select>
                  </div>

                  <!-- 模型状态提示 -->
                  <div class="flex items-center gap-2 text-xs">
                    <div
                      :class="[
                        'w-2 h-2 rounded-full',
                        modelStatus === 'ready' ? 'bg-green-500' :
                        modelStatus === 'loading' ? 'bg-yellow-500 animate-pulse' :
                        'bg-red-500'
                      ]"
                    ></div>
                    <span class="text-muted-foreground">{{ modelStatusText }}</span>
                  </div>

                  <!-- 刷新模型列表按钮 -->
                  <button
                    @click="refreshModels"
                    :disabled="isLoadingModels"
                    class="flex items-center gap-2 px-3 py-1.5 text-sm text-primary hover:bg-primary/10 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <RefreshCw :class="['w-4 h-4', isLoadingModels && 'animate-spin']" />
                    <span>{{ t('settings.refreshModels') }}</span>
                  </button>
                </div>
              </Transition>
            </div>

            <!-- 分隔线 -->
            <div class="border-t border-border"></div>

            <!-- 后台服务设置 -->
            <div class="space-y-4">
              <div class="flex items-center gap-2 mb-2">
                <Server class="w-4 h-4 text-muted-foreground" />
                <span class="text-sm font-medium text-foreground">{{ t('settings.keepBackendRunning') }}</span>
              </div>
              
              <!-- 选项说明 -->
              <p class="text-xs text-muted-foreground">
                {{ t('settings.keepBackendRunningDescription') }}
              </p>
              
              <!-- 单选选项 -->
              <div class="space-y-2 pl-2">
                <label class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
                  :class="settings.keepBackendRunning ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'"
                >
                  <input
                    type="radio"
                    :value="true"
                    v-model="settings.keepBackendRunning"
                    class="mt-0.5 w-4 h-4 text-primary"
                  />
                  <div class="flex-1">
                    <span class="text-sm font-medium text-foreground">{{ t('common.yes') }}</span>
                    <p class="text-xs text-muted-foreground mt-1">{{ t('settings.keepBackendRunningYes') }}</p>
                  </div>
                </label>
                
                <label class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
                  :class="!settings.keepBackendRunning ? 'border-primary bg-primary/5' : 'border-input hover:bg-muted/50'"
                >
                  <input
                    type="radio"
                    :value="false"
                    v-model="settings.keepBackendRunning"
                    class="mt-0.5 w-4 h-4 text-primary"
                  />
                  <div class="flex-1">
                    <span class="text-sm font-medium text-foreground">{{ t('common.no') }}</span>
                    <p class="text-xs text-muted-foreground mt-1">{{ t('settings.keepBackendRunningNo') }}</p>
                  </div>
                </label>
              </div>
            </div>

            <!-- 分隔线 -->
            <div class="border-t border-border"></div>

            <!-- 高级设置 -->
            <div class="space-y-2">
              <div class="flex items-center gap-2 mb-2">
                <Settings2 class="w-4 h-4 text-muted-foreground" />
                <span class="text-sm font-medium text-foreground">{{ t('settings.advanced') }}</span>
              </div>
              
              <!-- 本地模型服务地址 -->
              <div class="space-y-2">
                <label class="block text-xs text-muted-foreground">
                  {{ t('settings.localModelEndpoint') }}
                </label>
                <input
                  v-model="settings.localModelEndpoint"
                  type="text"
                  placeholder="http://localhost:11434"
                  class="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>
          
          <!-- 底部按钮 -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
            <button
              @click="resetSettings"
              class="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              {{ t('settings.resetDefault') }}
            </button>
            <button
              @click="close"
              class="px-4 py-2 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="saveSettings"
              class="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              {{ t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { X, Globe, Cpu, RefreshCw, Settings2, Server } from 'lucide-vue-next';
import { SUPPORTED_LOCALES, type SupportedLocale } from '@/i18n';
import tauriService, { defaultSettings } from '@/services/tauri';

const { t } = useI18n();

// Props
const props = defineProps<{
  isOpen: boolean;
}>();

// Emits
const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'save', settings: AppSettings): void;
}>();

// 支持的语言列表
const supportedLocales = SUPPORTED_LOCALES;

// 设置类型定义（前端使用）
interface AppSettings {
  language: SupportedLocale;
  enableLocalModel: boolean;
  localModel: string;
  localModelEndpoint: string;
  keepBackendRunning: boolean;
}

// 本地模型信息
interface LocalModel {
  name: string;
  size?: string;
  modified?: string;
}

// 响应式设置
const settings = reactive<AppSettings>({
  language: defaultSettings.language as SupportedLocale,
  enableLocalModel: defaultSettings.enableLocalModel,
  localModel: defaultSettings.localModel,
  localModelEndpoint: defaultSettings.localModelEndpoint,
  keepBackendRunning: defaultSettings.keepBackendRunning,
});

// Ollama 模型列表
const ollamaModels = ref<LocalModel[]>([]);
const isLoadingModels = ref(false);
const isLoadingSettings = ref(false);

// 模型状态
const modelStatus = ref<'ready' | 'loading' | 'error' | 'none'>('none');

const modelStatusText = computed(() => {
  switch (modelStatus.value) {
    case 'ready':
      return t('settings.modelStatus.ready');
    case 'loading':
      return t('settings.modelStatus.loading');
    case 'error':
      return t('settings.modelStatus.error');
    default:
      return t('settings.modelStatus.none');
  }
});

// 加载已保存的设置
async function loadSettings() {
  isLoadingSettings.value = true;
  try {
    // 优先从 Tauri 后端读取统一配置
    if (tauriService.isTauriEnv()) {
      try {
        const tauriSettings = await tauriService.getAppSettings();
        settings.language = tauriSettings.language as SupportedLocale;
        settings.enableLocalModel = tauriSettings.enableLocalModel;
        settings.localModel = tauriSettings.localModel;
        settings.localModelEndpoint = tauriSettings.localModelEndpoint;
        settings.keepBackendRunning = tauriSettings.keepBackendRunning;
        console.log('[Settings] 从 Tauri 配置文件加载设置:', tauriSettings);
        return;
      } catch (e) {
        console.warn('[Settings] 无法从 Tauri 读取设置，尝试迁移 localStorage:', e);
      }
    }
    
    // 回退：从 localStorage 读取（用于非 Tauri 环境或首次迁移）
    const stored = localStorage.getItem('localbrisk-settings');
    if (stored) {
      const parsed = JSON.parse(stored);
      settings.language = parsed.language || defaultSettings.language;
      settings.enableLocalModel = parsed.enableLocalModel ?? defaultSettings.enableLocalModel;
      settings.localModel = parsed.localModel || defaultSettings.localModel;
      settings.localModelEndpoint = parsed.localModelEndpoint || defaultSettings.localModelEndpoint;
      settings.keepBackendRunning = parsed.keepBackendRunning ?? defaultSettings.keepBackendRunning;
      
      // 如果在 Tauri 环境中，将 localStorage 配置迁移到配置文件
      if (tauriService.isTauriEnv()) {
        try {
          await tauriService.saveAppSettings({
            language: settings.language,
            enableLocalModel: settings.enableLocalModel,
            localModel: settings.localModel,
            localModelEndpoint: settings.localModelEndpoint,
            keepBackendRunning: settings.keepBackendRunning,
          });
          console.log('[Settings] 已将 localStorage 配置迁移到配置文件');
          // 迁移成功后可以选择清除 localStorage
          // localStorage.removeItem('localbrisk-settings');
        } catch (e) {
          console.warn('[Settings] 迁移配置失败:', e);
        }
      }
    }
  } catch (error) {
    console.error(t('errors.loadSettingsFailed'), error);
  } finally {
    isLoadingSettings.value = false;
  }
}

// 保存设置
async function saveSettings() {
  try {
    // 优先保存到 Tauri 配置文件
    if (tauriService.isTauriEnv()) {
      try {
        await tauriService.saveAppSettings({
          language: settings.language,
          enableLocalModel: settings.enableLocalModel,
          localModel: settings.localModel,
          localModelEndpoint: settings.localModelEndpoint,
          keepBackendRunning: settings.keepBackendRunning,
        });
        console.log('[Settings] 设置已保存到配置文件');
      } catch (e) {
        console.error('[Settings] 保存到 Tauri 配置文件失败:', e);
        // 回退到 localStorage
        localStorage.setItem('localbrisk-settings', JSON.stringify(settings));
      }
    } else {
      // 非 Tauri 环境使用 localStorage
      localStorage.setItem('localbrisk-settings', JSON.stringify(settings));
    }
    
    emit('save', { ...settings });
    close();
  } catch (error) {
    console.error(t('errors.saveSettingsFailed'), error);
  }
}

// 重置设置
function resetSettings() {
  settings.language = defaultSettings.language as SupportedLocale;
  settings.enableLocalModel = defaultSettings.enableLocalModel;
  settings.localModel = defaultSettings.localModel;
  settings.localModelEndpoint = defaultSettings.localModelEndpoint;
  settings.keepBackendRunning = defaultSettings.keepBackendRunning;
}

// 关闭弹窗
function close() {
  emit('close');
}

// 刷新模型列表
async function refreshModels() {
  isLoadingModels.value = true;
  modelStatus.value = 'loading';
  
  try {
    // 尝试连接 Ollama 服务
    const response = await fetch(`${settings.localModelEndpoint}/api/tags`, {
      method: 'GET',
    });
    
    if (response.ok) {
      const data = await response.json();
      ollamaModels.value = (data.models || []).map((m: any) => ({
        name: m.name,
        size: formatSize(m.size),
        modified: m.modified_at,
      }));
      modelStatus.value = settings.localModel ? 'ready' : 'none';
    } else {
      throw new Error(t('errors.fetchModelsFailed'));
    }
  } catch (error) {
    console.error(t('errors.fetchModelsFailed'), error);
    ollamaModels.value = [];
    modelStatus.value = 'error';
    
    // 添加一些预设模型供用户参考
    ollamaModels.value = [
      { name: 'llama3.2', size: '2.0 GB' },
      { name: 'llama3.2:1b', size: '1.3 GB' },
      { name: 'qwen2.5', size: '4.7 GB' },
      { name: 'qwen2.5:0.5b', size: '397 MB' },
      { name: 'deepseek-r1:7b', size: '4.7 GB' },
      { name: 'mistral', size: '4.1 GB' },
    ];
  } finally {
    isLoadingModels.value = false;
  }
}

// 格式化文件大小
function formatSize(bytes?: number): string {
  if (!bytes) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

// 监听弹窗打开
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    loadSettings();
    if (settings.enableLocalModel) {
      refreshModels();
    }
  }
});

// 监听本地模型启用状态
watch(() => settings.enableLocalModel, (enabled) => {
  if (enabled && ollamaModels.value.length === 0) {
    refreshModels();
  }
});

// 监听模型选择
watch(() => settings.localModel, (model) => {
  if (model && settings.enableLocalModel) {
    modelStatus.value = 'ready';
  } else {
    modelStatus.value = 'none';
  }
});

onMounted(() => {
  loadSettings();
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

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
