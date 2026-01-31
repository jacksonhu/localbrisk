/**
 * LocalBrisk API 服务
 * 与 Python FastAPI 后端通信
 */

import { getLocale } from "@/i18n";
import type {
  Catalog,
  CatalogCreate,
  CatalogUpdate,
  CatalogTreeNode,
  Schema,
  SchemaCreate,
  SchemaUpdate,
  SyncResult,
  Asset,
  AssetCreate,
  Agent,
  AgentCreate,
  AgentUpdate,
  DeleteResponse,
  Prompt,
  PromptCreate,
  PromptUpdate,
} from "@/types/catalog";

const API_BASE_URL = "http://127.0.0.1:8765";

/**
 * 获取当前语言请求头
 */
function getLanguageHeaders(): HeadersInit {
  return {
    "X-Language": getLocale(),
    "Accept-Language": getLocale(),
  };
}

/**
 * 通用请求方法
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders: HeadersInit = {
    "Content-Type": "application/json",
    ...getLanguageHeaders(),
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  // 处理无内容响应
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ status: string; message?: string; version?: string }> {
  return request("/health");
}

/**
 * 就绪检查
 */
export async function readyCheck(): Promise<{ status: string }> {
  return request("/health/ready");
}

/**
 * 获取支持的语言列表
 */
export async function getSupportedLocales(): Promise<{
  locales: Array<{ code: string; name: string; nativeName: string }>;
  default: string;
}> {
  return request("/api/i18n/locales");
}

// ============ Catalog API ============

export const catalogApi = {
  /**
   * 获取所有 Catalog
   */
  list: (): Promise<Catalog[]> => 
    request<Catalog[]>("/api/catalogs"),

  /**
   * 获取单个 Catalog
   */
  get: (catalogId: string): Promise<Catalog> => 
    request<Catalog>(`/api/catalogs/${catalogId}`),

  /**
   * 获取 Catalog 配置文件 (config.yaml) 原始内容
   */
  getConfig: (catalogId: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/catalogs/${catalogId}/config`),

  /**
   * 创建 Catalog
   */
  create: (data: CatalogCreate): Promise<Catalog> =>
    request<Catalog>("/api/catalogs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Catalog
   */
  update: (catalogId: string, data: CatalogUpdate): Promise<Catalog> =>
    request<Catalog>(`/api/catalogs/${catalogId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Catalog
   */
  delete: (catalogId: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/catalogs/${catalogId}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Catalog 导航树
   */
  getTree: (): Promise<CatalogTreeNode[]> =>
    request<CatalogTreeNode[]>("/api/catalogs/tree"),
};

// ============ Schema API ============

// ============ Schema API ============

export const schemaApi = {
  /**
   * 获取 Catalog 下的所有 Schema
   */
  list: (catalogId: string): Promise<Schema[]> =>
    request<Schema[]>(`/api/catalogs/${catalogId}/schemas`),

  /**
   * 获取单个 Schema 详情
   */
  get: (catalogId: string, schemaName: string): Promise<Schema> =>
    request<Schema>(`/api/catalogs/${catalogId}/schemas/${schemaName}`),

  /**
   * 获取 Schema 配置文件 (schema.yaml) 原始内容
   */
  getConfig: (catalogId: string, schemaName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/catalogs/${catalogId}/schemas/${schemaName}/config`),

  /**
   * 创建 Schema
   */
  create: (catalogId: string, data: SchemaCreate): Promise<Schema> =>
    request<Schema>(`/api/catalogs/${catalogId}/schemas`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Schema
   */
  update: (catalogId: string, schemaName: string, data: SchemaUpdate): Promise<Schema> =>
    request<Schema>(`/api/catalogs/${catalogId}/schemas/${schemaName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Schema
   */
  delete: (catalogId: string, schemaName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/catalogs/${catalogId}/schemas/${schemaName}`, {
      method: "DELETE",
    }),

  /**
   * 同步 Schema 元数据（手动触发）
   */
  sync: (catalogId: string, schemaName: string): Promise<SyncResult> =>
    request<SyncResult>(`/api/catalogs/${catalogId}/schemas/${schemaName}/sync`, {
      method: "POST",
    }),
};

// ============ Asset API ============

/** 表数据预览结果 */
export interface TablePreviewResult {
  columns: string[];
  rows: Record<string, any>[];
  total: number;
  limit: number;
  offset: number;
}

export const assetApi = {
  /**
   * 获取 Schema 下的所有 Asset
   */
  list: (catalogId: string, schemaName: string): Promise<Asset[]> =>
    request<Asset[]>(`/api/catalogs/${catalogId}/schemas/${schemaName}/assets`),

  /**
   * 创建新的 Asset
   */
  create: (catalogId: string, schemaName: string, data: AssetCreate): Promise<Asset> =>
    request<Asset>(`/api/catalogs/${catalogId}/schemas/${schemaName}/assets`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Asset
   */
  delete: (catalogId: string, schemaName: string, assetName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/catalogs/${catalogId}/schemas/${schemaName}/assets/${assetName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Asset 配置文件原始内容
   */
  getConfig: (catalogId: string, schemaName: string, assetName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/catalogs/${catalogId}/schemas/${schemaName}/assets/${assetName}/config`),

  /**
   * 预览表数据
   */
  previewTableData: (
    catalogId: string, 
    schemaName: string, 
    tableName: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<TablePreviewResult> =>
    request<TablePreviewResult>(
      `/api/catalogs/${catalogId}/schemas/${schemaName}/tables/${tableName}/preview?limit=${limit}&offset=${offset}`
    ),
};

// ============ Agent API ============

export const agentApi = {
  /**
   * 获取 Catalog 下的所有 Agent
   */
  list: (catalogId: string): Promise<Agent[]> =>
    request<Agent[]>(`/api/catalogs/${catalogId}/agents`),

  /**
   * 获取单个 Agent 详情
   */
  get: (catalogId: string, agentName: string): Promise<Agent> =>
    request<Agent>(`/api/catalogs/${catalogId}/agents/${agentName}`),

  /**
   * 获取 Agent 配置文件 (agent_spec.yaml) 原始内容
   */
  getConfig: (catalogId: string, agentName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/config`),

  /**
   * 创建 Agent
   */
  create: (catalogId: string, data: AgentCreate): Promise<Agent> =>
    request<Agent>(`/api/catalogs/${catalogId}/agents`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Agent
   */
  update: (catalogId: string, agentName: string, data: AgentUpdate): Promise<Agent> =>
    request<Agent>(`/api/catalogs/${catalogId}/agents/${agentName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Agent
   */
  delete: (catalogId: string, agentName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/catalogs/${catalogId}/agents/${agentName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Agent Prompt 内容
   */
  getPrompt: (catalogId: string, agentName: string, promptName: string): Promise<Prompt> =>
    request<Prompt>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts/${promptName}`),

  /**
   * 获取 Agent 所有 Prompts
   */
  listPrompts: (catalogId: string, agentName: string): Promise<Prompt[]> =>
    request<Prompt[]>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts`),

  /**
   * 创建 Agent Prompt
   */
  createPrompt: (catalogId: string, agentName: string, data: PromptCreate): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Agent Prompt
   */
  updatePrompt: (catalogId: string, agentName: string, promptName: string, data: PromptUpdate): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts/${promptName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Agent Prompt
   */
  deletePrompt: (catalogId: string, agentName: string, promptName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts/${promptName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Agent Skill 内容
   */
  getSkill: (catalogId: string, agentName: string, skillName: string): Promise<{ name: string; content: string }> =>
    request<{ name: string; content: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/skills/${skillName}`),

  /**
   * 创建/更新 Agent Skill
   */
  createSkill: (catalogId: string, agentName: string, skillName: string, content: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/skills/${skillName}`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  /**
   * 删除 Agent Skill
   */
  deleteSkill: (catalogId: string, agentName: string, skillName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/skills/${skillName}`, {
      method: "DELETE",
    }),

  /**
   * 切换 Prompt 启用状态
   */
  togglePromptEnabled: (catalogId: string, agentName: string, promptName: string, enabled: boolean): Promise<{ message: string; enabled: boolean }> =>
    request<{ message: string; enabled: boolean }>(`/api/catalogs/${catalogId}/agents/${agentName}/prompts/${promptName}/toggle?enabled=${enabled}`, {
      method: "POST",
    }),

  /**
   * 切换 Skill 启用状态
   */
  toggleSkillEnabled: (catalogId: string, agentName: string, skillName: string, enabled: boolean): Promise<{ message: string; enabled: boolean }> =>
    request<{ message: string; enabled: boolean }>(`/api/catalogs/${catalogId}/agents/${agentName}/skills/${skillName}/toggle?enabled=${enabled}`, {
      method: "POST",
    }),

  /**
   * 从本地 zip 文件路径导入 Skill
   * 本地桌面应用场景，直接传递本地文件路径
   */
  importSkillFromZip: (catalogId: string, agentName: string, zipFilePath: string): Promise<{ success: boolean; skill_name?: string; message: string; path?: string }> =>
    request<{ success: boolean; skill_name?: string; message: string; path?: string }>(`/api/catalogs/${catalogId}/agents/${agentName}/skills/import`, {
      method: "POST",
      body: JSON.stringify({ zip_file_path: zipFilePath }),
    }),
};

// ============ Model API（Schema 级别） ============

import type { Model, ModelCreate, ModelUpdate } from "@/types/catalog";

export const modelApi = {
  /**
   * 获取 Schema 下的所有 Model
   */
  list: (catalogId: string, schemaName: string): Promise<Model[]> =>
    request<Model[]>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models`),

  /**
   * 获取 Model 详情
   */
  get: (catalogId: string, schemaName: string, modelName: string): Promise<Model> =>
    request<Model>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models/${modelName}`),

  /**
   * 获取 Model 配置文件原始内容
   */
  getConfig: (catalogId: string, schemaName: string, modelName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models/${modelName}/config`),

  /**
   * 创建 Model
   */
  create: (catalogId: string, schemaName: string, data: ModelCreate): Promise<Model> =>
    request<Model>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Model
   */
  update: (catalogId: string, schemaName: string, modelName: string, data: ModelUpdate): Promise<Model> =>
    request<Model>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models/${modelName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Model
   */
  delete: (catalogId: string, schemaName: string, modelName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/catalogs/${catalogId}/schemas/${schemaName}/models/${modelName}`, {
      method: "DELETE",
    }),
};

// ============ 默认导出 ============

export default {
  healthCheck,
  readyCheck,
  getSupportedLocales,
  catalog: catalogApi,
  schema: schemaApi,
  asset: assetApi,
  agent: agentApi,
  model: modelApi,
};
