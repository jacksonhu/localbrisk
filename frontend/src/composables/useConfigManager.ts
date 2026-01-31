/**
 * 配置管理 Composable
 * 提供统一的配置文件保存、加载、复制功能
 * 支持 Catalog、Schema、Agent、Model 等实体的 YAML 配置管理
 */

import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { writeTextFile, isTauriEnv } from '@/services/fileService';
import { useToast } from '@/composables/useToast';

/**
 * 配置管理器选项
 */
export interface ConfigManagerOptions {
  /** 配置类型，用于日志和错误提示 */
  type: 'catalog' | 'schema' | 'agent' | 'asset' | 'model';
  
  /** 获取配置文件路径的函数 */
  getConfigPath: () => string | undefined;
  
  /** 加载配置内容的函数（通常从后端 API 获取） */
  loadConfig: () => Promise<string>;
  
  /** 配置保存成功后的回调 */
  onSaved?: () => void | Promise<void>;
  
  /** 是否验证 YAML 格式，默认为 true */
  validateYaml?: boolean;
}

/**
 * 配置管理 Composable
 * 
 * @example
 * ```ts
 * const configManager = useConfigManager({
 *   type: 'catalog',
 *   getConfigPath: () => selectedCatalog.value?.path ? `${selectedCatalog.value.path}/config.yaml` : undefined,
 *   loadConfig: async () => {
 *     const response = await catalogApi.getConfig(catalogId);
 *     return response.content;
 *   },
 *   onSaved: () => {
 *     store.refreshCatalog(catalogId);
 *   }
 * });
 * ```
 */
export function useConfigManager(options: ConfigManagerOptions) {
  const { t } = useI18n();
  const { showSuccess, showError } = useToast();
  
  // 配置内容状态
  const configContent = ref('');
  const originalConfig = ref('');
  const savingConfig = ref(false);
  const loadingConfig = ref(false);
  
  // 计算属性：配置是否被修改
  const configModified = computed(() => 
    configContent.value !== originalConfig.value
  );
  
  /**
   * 加载配置内容
   */
  async function loadConfigContent() {
    loadingConfig.value = true;
    try {
      const content = await options.loadConfig();
      configContent.value = content;
      originalConfig.value = content;
    } catch (error) {
      console.error(`Failed to load ${options.type} config:`, error);
      // 加载失败时清空内容
      configContent.value = '';
      originalConfig.value = '';
    } finally {
      loadingConfig.value = false;
    }
  }
  
  /**
   * 验证 YAML 格式
   * 简单的语法检查，不做完整解析
   */
  function validateYamlSyntax(content: string): boolean {
    // 基础检查：不能为空
    if (!content.trim()) {
      return false;
    }
    
    // 检查基本 YAML 结构
    const lines = content.split('\n');
    for (const line of lines) {
      // 跳过空行和注释
      if (!line.trim() || line.trim().startsWith('#')) {
        continue;
      }
      
      // 检查缩进是否使用 tab（YAML 不允许）
      if (line.match(/^\t/)) {
        return false;
      }
    }
    
    return true;
  }
  
  /**
   * 保存配置到本地文件
   */
  async function saveConfig() {
    if (!configModified.value) return;
    
    // 检查 Tauri 环境
    if (!isTauriEnv()) {
      console.warn('Not in Tauri environment, save operation skipped');
      showError(t('config.notInTauriEnv'));
      return;
    }
    
    savingConfig.value = true;
    try {
      // 验证 YAML 格式（如果启用）
      if (options.validateYaml !== false) {
        if (!validateYamlSyntax(configContent.value)) {
          throw new Error(t('config.invalidYamlFormat'));
        }
      }
      
      // 获取配置文件路径
      const configPath = options.getConfigPath();
      if (!configPath) {
        throw new Error(t('config.invalidPath'));
      }
      
      // 保存到本地文件
      await writeTextFile(configPath, configContent.value);
      
      // 更新原始配置状态
      originalConfig.value = configContent.value;
      
      // 执行保存成功回调
      if (options.onSaved) {
        await options.onSaved();
      }
      
      showSuccess(t('config.saved'));
    } catch (error) {
      console.error(`Failed to save ${options.type} config:`, error);
      const message = error instanceof Error ? error.message : t('config.saveFailed');
      showError(message);
    } finally {
      savingConfig.value = false;
    }
  }
  
  /**
   * 复制配置内容到剪贴板
   */
  async function copyConfig() {
    try {
      await navigator.clipboard.writeText(configContent.value);
      showSuccess(t('config.copied'));
    } catch (error) {
      console.error('Failed to copy config:', error);
      showError(t('config.copyFailed'));
    }
  }
  
  /**
   * 重置配置（恢复到原始状态）
   */
  function resetConfig() {
    configContent.value = originalConfig.value;
  }
  
  /**
   * 更新原始配置（用于外部加载后同步状态）
   */
  function setOriginalConfig(content: string) {
    configContent.value = content;
    originalConfig.value = content;
  }
  
  return {
    // 状态
    configContent,
    originalConfig,
    configModified,
    savingConfig,
    loadingConfig,
    
    // 方法
    loadConfigContent,
    saveConfig,
    copyConfig,
    resetConfig,
    setOriginalConfig,
  };
}

export default useConfigManager;
