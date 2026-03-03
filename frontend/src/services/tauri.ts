/**
 * Tauri 命令调用服务
 * 与 Rust 后端通信
 */

import type {
  BusinessUnit,
  BusinessUnitCreate,
  BusinessUnitUpdate,
  BusinessUnitTreeNode,
  AssetBundle,
  AssetBundleCreate,
  AssetBundleUpdate,
  SyncResult,
  Agent,
  AgentCreate,
  AgentUpdate,
  DeleteResponse,
  Prompt,
  PromptCreate,
} from "@/types/catalog";

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
export function isTauriEnv(): boolean {
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

// ============ 基础应用命令 ============

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

// ============ 设置相关命令 ============

/**
 * 设置是否在退出时保持后端运行
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
 */
export async function saveAppSettings(settings: FrontendSettings): Promise<void> {
  const invoke = await getTauriInvoke();
  const backendSettings = toBackendSettings(settings);
  return invoke("save_app_settings", { newSettings: backendSettings });
}

/**
 * 默认设置
 */
export const defaultSettings: FrontendSettings = {
  keepBackendRunning: true,
  language: 'zh-CN',
  enableLocalModel: false,
  localModel: '',
  localModelEndpoint: 'http://localhost:11434',
};

// ============ BusinessUnit API ============

export const tauriBusinessUnitApi = {
  /**
   * 获取所有 BusinessUnit
   */
  list: async (): Promise<BusinessUnit[]> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_list");
  },

  /**
   * 获取单个 BusinessUnit
   */
  get: async (businessUnitId: string): Promise<BusinessUnit> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_get", { businessUnitId });
  },

  /**
   * 获取 BusinessUnit 配置文件内容
   */
  getConfig: async (businessUnitId: string): Promise<{ content: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_get_config", { businessUnitId });
  },

  /**
   * 创建 BusinessUnit
   */
  create: async (data: BusinessUnitCreate): Promise<BusinessUnit> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_create", { data });
  },

  /**
   * 更新 BusinessUnit
   */
  update: async (businessUnitId: string, data: BusinessUnitUpdate): Promise<BusinessUnit> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_update", { businessUnitId, data });
  },

  /**
   * 删除 BusinessUnit
   */
  delete: async (businessUnitId: string): Promise<DeleteResponse> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_delete", { businessUnitId });
  },

  /**
   * 获取 BusinessUnit 导航树
   */
  getTree: async (): Promise<BusinessUnitTreeNode[]> => {
    const invoke = await getTauriInvoke();
    return invoke("business_unit_get_tree");
  },
};

// ============ AssetBundle API ============

export const tauriAssetBundleApi = {
  /**
   * 获取 BusinessUnit 下的所有 AssetBundle
   */
  list: async (businessUnitId: string): Promise<AssetBundle[]> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_list", { businessUnitId });
  },

  /**
   * 获取单个 AssetBundle 详情
   */
  get: async (businessUnitId: string, bundleName: string): Promise<AssetBundle> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_get", { businessUnitId, bundleName });
  },

  /**
   * 获取 AssetBundle 配置文件内容
   */
  getConfig: async (businessUnitId: string, bundleName: string): Promise<{ content: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_get_config", { businessUnitId, bundleName });
  },

  /**
   * 创建 AssetBundle
   */
  create: async (businessUnitId: string, data: AssetBundleCreate): Promise<AssetBundle> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_create", { businessUnitId, data });
  },

  /**
   * 更新 AssetBundle
   */
  update: async (businessUnitId: string, bundleName: string, data: AssetBundleUpdate): Promise<AssetBundle> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_update", { businessUnitId, bundleName, data });
  },

  /**
   * 删除 AssetBundle
   */
  delete: async (businessUnitId: string, bundleName: string): Promise<DeleteResponse> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_delete", { businessUnitId, bundleName });
  },

  /**
   * 同步 AssetBundle 元数据
   */
  sync: async (businessUnitId: string, bundleName: string): Promise<SyncResult> => {
    const invoke = await getTauriInvoke();
    return invoke("asset_bundle_sync", { businessUnitId, bundleName });
  },
};

// ============ Agent API ============

export const tauriAgentApi = {
  /**
   * 获取 BusinessUnit 下的所有 Agent
   */
  list: async (businessUnitId: string): Promise<Agent[]> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_list", { businessUnitId });
  },

  /**
   * 获取单个 Agent 详情
   */
  get: async (businessUnitId: string, agentName: string): Promise<Agent> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_get", { businessUnitId, agentName });
  },

  /**
   * 获取 Agent 配置文件内容
   */
  getConfig: async (businessUnitId: string, agentName: string): Promise<{ content: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_get_config", { businessUnitId, agentName });
  },

  /**
   * 创建 Agent
   */
  create: async (businessUnitId: string, data: AgentCreate): Promise<Agent> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_create", { businessUnitId, data });
  },

  /**
   * 更新 Agent
   */
  update: async (businessUnitId: string, agentName: string, data: AgentUpdate): Promise<Agent> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_update", { businessUnitId, agentName, data });
  },

  /**
   * 删除 Agent
   */
  delete: async (businessUnitId: string, agentName: string): Promise<DeleteResponse> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_delete", { businessUnitId, agentName });
  },

  /**
   * 获取 Agent 所有 Prompts
   */
  listPrompts: async (businessUnitId: string, agentName: string): Promise<Prompt[]> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_list_prompts", { businessUnitId, agentName });
  },

  /**
   * 创建 Agent Prompt
   */
  createPrompt: async (businessUnitId: string, agentName: string, data: PromptCreate): Promise<{ message: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_create_prompt", { businessUnitId, agentName, data });
  },

  /**
   * 获取 Agent Skill 内容
   */
  getSkill: async (businessUnitId: string, agentName: string, skillName: string): Promise<{ name: string; content: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_get_skill", { businessUnitId, agentName, skillName });
  },

  /**
   * 创建/更新 Agent Skill
   */
  createSkill: async (businessUnitId: string, agentName: string, skillName: string, content: string): Promise<{ message: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_create_skill", { businessUnitId, agentName, skillName, content });
  },

  /**
   * 获取 Agent 所有 Skills 名称
   */
  listSkills: async (businessUnitId: string, agentName: string): Promise<string[]> => {
    const invoke = await getTauriInvoke();
    return invoke("agent_list_skills", { businessUnitId, agentName });
  },
};

// ============ 健康检查 API ============

export const tauriHealthApi = {
  /**
   * API 健康检查
   */
  check: async (): Promise<{ status: string; message?: string; version?: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("api_health_check");
  },

  /**
   * 就绪检查
   */
  ready: async (): Promise<{ status: string }> => {
    const invoke = await getTauriInvoke();
    return invoke("ready_check");
  },

  /**
   * 获取支持的语言列表
   */
  getLocales: async (): Promise<{
    locales: Array<{ code: string; name: string; nativeName: string }>;
    default: string;
  }> => {
    const invoke = await getTauriInvoke();
    return invoke("get_supported_locales");
  },
};

// ============ 默认导出 ============

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
  // API 模块
  businessUnit: tauriBusinessUnitApi,
  assetBundle: tauriAssetBundleApi,
  agent: tauriAgentApi,
  health: tauriHealthApi,
};
