/**
 * Tauri 命令调用服务
 * 与 Rust 后端通信
 */

// 应用设置类型定义（与 Rust 后端保持一致）
export interface AppSettings {
  keep_backend_running: boolean;
  language: string;
  enable_local_model: boolean;
  local_model: string;
  local_model_endpoint: string;
}

// 前端友好的设置类型（使用驼峰命名）
export interface FrontendSettings {
  keepBackendRunning: boolean;
  language: string;
  enableLocalModel: boolean;
  localModel: string;
  localModelEndpoint: string;
}

// 将后端设置转换为前端格式
function toFrontendSettings(settings: AppSettings): FrontendSettings {
  return {
    keepBackendRunning: settings.keep_backend_running,
    language: settings.language,
    enableLocalModel: settings.enable_local_model,
    localModel: settings.local_model,
    localModelEndpoint: settings.local_model_endpoint,
  };
}

// 将前端设置转换为后端格式
function toBackendSettings(settings: FrontendSettings): AppSettings {
  return {
    keep_backend_running: settings.keepBackendRunning,
    language: settings.language,
    enable_local_model: settings.enableLocalModel,
    local_model: settings.localModel,
    local_model_endpoint: settings.localModelEndpoint,
  };
}

// 检查是否在 Tauri 环境中
function isTauriEnv(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

// 动态导入 Tauri API
async function getTauriInvoke() {
  if (!isTauriEnv()) {
    throw new Error('Not in Tauri environment');
  }
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke;
}

/**
 * 获取应用信息
 */
export async function getAppInfo(): Promise<{
  name: string;
  version: string;
  description: string;
}> {
  const invoke = await getTauriInvoke();
  return invoke("get_app_info");
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<string> {
  const invoke = await getTauriInvoke();
  return invoke("health_check");
}

/**
 * 检查后端服务健康状态
 */
export async function checkBackendHealth(): Promise<string> {
  const invoke = await getTauriInvoke();
  return invoke("check_backend_health");
}

/**
 * 等待后端服务就绪
 * @param maxRetries 最大重试次数
 * @param retryInterval 重试间隔（毫秒）
 */
export async function waitForBackend(
  maxRetries: number = 10,
  retryInterval: number = 1000
): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await checkBackendHealth();
      return true;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, retryInterval));
    }
  }
  return false;
}

/**
 * 设置是否在退出时保持后端运行
 * @param keep 是否保持后端运行
 */
export async function setKeepBackendRunning(keep: boolean): Promise<void> {
  const invoke = await getTauriInvoke();
  return invoke("set_keep_backend_running", { keep });
}

/**
 * 获取是否在退出时保持后端运行的设置
 */
export async function getKeepBackendRunning(): Promise<boolean> {
  const invoke = await getTauriInvoke();
  return invoke("get_keep_backend_running");
}

/**
 * 获取所有应用设置
 */
export async function getAppSettings(): Promise<FrontendSettings> {
  const invoke = await getTauriInvoke();
  const settings: AppSettings = await invoke("get_app_settings");
  return toFrontendSettings(settings);
}

/**
 * 保存所有应用设置
 * @param settings 前端格式的设置
 */
export async function saveAppSettings(settings: FrontendSettings): Promise<void> {
  const invoke = await getTauriInvoke();
  const backendSettings = toBackendSettings(settings);
  return invoke("save_app_settings", { settings: backendSettings });
}

/**
 * 默认设置（用于非 Tauri 环境或加载失败时的回退）
 */
export const defaultSettings: FrontendSettings = {
  keepBackendRunning: true,
  language: 'zh-CN',
  enableLocalModel: false,
  localModel: '',
  localModelEndpoint: 'http://localhost:11434',
};

export default {
  isTauriEnv,
  getAppInfo,
  healthCheck,
  checkBackendHealth,
  waitForBackend,
  setKeepBackendRunning,
  getKeepBackendRunning,
  getAppSettings,
  saveAppSettings,
  defaultSettings,
};
