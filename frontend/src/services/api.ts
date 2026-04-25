/**
 * LocalBrisk API 服务
 * 与 Python FastAPI 后端通信
 * 
 * 概念说明：
 * - BusinessUnit (业务单元)
 * - AssetBundle (资源包)
 * - Model 从 AssetBundle 移动到 Agent 下
 * - Agent 新增 mcps 目录支持 MCP 配置
 */

import { getLocale } from "@/i18n";
import type {
  // BusinessUnit
  BusinessUnit,
  BusinessUnitCreate,
  BusinessUnitUpdate,
  BusinessUnitTreeNode,
  // AssetBundle
  AssetBundle,
  AssetBundleCreate,
  AssetBundleUpdate,
  SyncResult,
  // Asset
  Asset,
  AssetCreate,
  // Agent
  Agent,
  AgentCreate,
  AgentUpdate,
  // Model (现在在 Agent 下)
  Model,
  ModelCreate,
  ModelUpdate,
  // MCP (新增)
  MCP,
  MCPCreate,
  MCPUpdate,
  // Memory
  Memory,
  MemoryCreate,
  MemoryUpdate,
  // Other
  DeleteResponse,
  OutputFileContent,
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

// ============ BusinessUnit API ============

export const businessUnitApi = {
  /**
   * 获取所有 BusinessUnit
   */
  list: (): Promise<BusinessUnit[]> => 
    request<BusinessUnit[]>("/api/business_units"),

  /**
   * 获取单个 BusinessUnit
   */
  get: (businessUnitId: string): Promise<BusinessUnit> => 
    request<BusinessUnit>(`/api/business_units/${businessUnitId}`),

  /**
   * 获取 BusinessUnit 配置文件 (config.yaml) 原始内容
   */
  getConfig: (businessUnitId: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/business_units/${businessUnitId}/config`),

  /**
   * 创建 BusinessUnit
   */
  create: (data: BusinessUnitCreate): Promise<BusinessUnit> =>
    request<BusinessUnit>("/api/business_units", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 BusinessUnit
   */
  update: (businessUnitId: string, data: BusinessUnitUpdate): Promise<BusinessUnit> =>
    request<BusinessUnit>(`/api/business_units/${businessUnitId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 BusinessUnit
   */
  delete: (businessUnitId: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/business_units/${businessUnitId}`, {
      method: "DELETE",
    }),

  /**
   * 获取 BusinessUnit 导航树
   */
  getTree: (): Promise<BusinessUnitTreeNode[]> =>
    request<BusinessUnitTreeNode[]>("/api/business_units/tree"),

  /**
   * 读取 Agent output 文件内容
   */
  getOutputFileContent: (businessUnitId: string, agentName: string, relativePath: string): Promise<OutputFileContent> =>
    request<OutputFileContent>(
      `/api/business_units/${businessUnitId}/agents/${agentName}/output/file?path=${encodeURIComponent(relativePath)}`
    ),

  /**
   * Save edited Agent output file content
   */
  saveOutputFileContent: (businessUnitId: string, agentName: string, relativePath: string, content: string): Promise<OutputFileContent> =>
    request<OutputFileContent>(
      `/api/business_units/${businessUnitId}/agents/${agentName}/output/file`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: relativePath, content }),
      }
    ),
};

// ============ AssetBundle API ============

export const assetBundleApi = {
  /**
   * 获取 BusinessUnit 下的所有 AssetBundle
   */
  list: (businessUnitId: string): Promise<AssetBundle[]> =>
    request<AssetBundle[]>(`/api/business_units/${businessUnitId}/asset_bundles`),

  /**
   * 获取单个 AssetBundle 详情
   */
  get: (businessUnitId: string, bundleName: string): Promise<AssetBundle> =>
    request<AssetBundle>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}`),

  /**
   * 获取 AssetBundle 配置文件 (bundle.yaml) 原始内容
   */
  getConfig: (businessUnitId: string, bundleName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/config`),

  /**
   * 创建 AssetBundle
   */
  create: (businessUnitId: string, data: AssetBundleCreate): Promise<AssetBundle> =>
    request<AssetBundle>(`/api/business_units/${businessUnitId}/asset_bundles`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 AssetBundle
   */
  update: (businessUnitId: string, bundleName: string, data: AssetBundleUpdate): Promise<AssetBundle> =>
    request<AssetBundle>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 AssetBundle
   */
  delete: (businessUnitId: string, bundleName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}`, {
      method: "DELETE",
    }),

  /**
   * 同步 AssetBundle 元数据（手动触发）
   */
  sync: (businessUnitId: string, bundleName: string): Promise<SyncResult> =>
    request<SyncResult>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/sync`, {
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
   * 获取 AssetBundle 下的所有 Asset
   */
  list: (businessUnitId: string, bundleName: string): Promise<Asset[]> =>
    request<Asset[]>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/assets`),

  /**
   * 创建新的 Asset
   */
  create: (businessUnitId: string, bundleName: string, data: AssetCreate): Promise<Asset> =>
    request<Asset>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/assets`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Asset
   */
  delete: (businessUnitId: string, bundleName: string, assetName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/assets/${assetName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Asset 配置文件原始内容
   */
  getConfig: (businessUnitId: string, bundleName: string, assetName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/assets/${assetName}/config`),

  /**
   * 预览表数据
   */
  previewTableData: (
    businessUnitId: string, 
    bundleName: string, 
    tableName: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<TablePreviewResult> =>
    request<TablePreviewResult>(
      `/api/business_units/${businessUnitId}/asset_bundles/${bundleName}/tables/${tableName}/preview?limit=${limit}&offset=${offset}`
    ),
};

// ============ Agent API ============

export const agentApi = {
  /**
   * 获取 BusinessUnit 下的所有 Agent
   */
  list: (businessUnitId: string): Promise<Agent[]> =>
    request<Agent[]>(`/api/business_units/${businessUnitId}/agents`),

  /**
   * 获取单个 Agent 详情
   */
  get: (businessUnitId: string, agentName: string): Promise<Agent> =>
    request<Agent>(`/api/business_units/${businessUnitId}/agents/${agentName}`),

  /**
   * 获取 Agent 配置文件 (agent_spec.yaml) 原始内容
   */
  getConfig: (businessUnitId: string, agentName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/config`),

  /**
   * 创建 Agent
   */
  create: (businessUnitId: string, data: AgentCreate): Promise<Agent> =>
    request<Agent>(`/api/business_units/${businessUnitId}/agents`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Agent
   */
  update: (businessUnitId: string, agentName: string, data: AgentUpdate): Promise<Agent> =>
    request<Agent>(`/api/business_units/${businessUnitId}/agents/${agentName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Agent
   */
  delete: (businessUnitId: string, agentName: string): Promise<DeleteResponse> =>
    request<DeleteResponse>(`/api/business_units/${businessUnitId}/agents/${agentName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Agent Memory 内容
   */
  getMemory: (businessUnitId: string, agentName: string, memoryName: string): Promise<Memory> =>
    request<Memory>(`/api/business_units/${businessUnitId}/agents/${agentName}/memories/${memoryName}`),

  /**
   * 获取 Agent 所有 Prompts
   */
  listMemories: (businessUnitId: string, agentName: string): Promise<Memory[]> =>
    request<Memory[]>(`/api/business_units/${businessUnitId}/agents/${agentName}/memories`),

  /**
   * 创建 Agent Memory
   */
  createMemory: (businessUnitId: string, agentName: string, data: MemoryCreate): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/memories`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Agent Memory
   */
  updateMemory: (businessUnitId: string, agentName: string, memoryName: string, data: MemoryUpdate): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/memories/${memoryName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Agent Memory
   */
  deleteMemory: (businessUnitId: string, agentName: string, memoryName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/memories/${memoryName}`, {
      method: "DELETE",
    }),

  /**
   * 获取 Agent Skill 内容
   */
  getSkill: (businessUnitId: string, agentName: string, skillName: string): Promise<{ name: string; content: string }> =>
    request<{ name: string; content: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/skills/${skillName}`),

  /**
   * 创建/更新 Agent Skill
   */
  createSkill: (businessUnitId: string, agentName: string, skillName: string, content: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/skills/${skillName}`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  /**
   * 删除 Agent Skill
   */
  deleteSkill: (businessUnitId: string, agentName: string, skillName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/skills/${skillName}`, {
      method: "DELETE",
    }),

  /**
   * 从本地 zip 文件路径导入 Skill
   * 本地桌面应用场景，直接传递本地文件路径
   */
  importSkillFromZip: (businessUnitId: string, agentName: string, zipFilePath: string): Promise<{ success: boolean; skill_name?: string; message: string; path?: string }> =>
    request<{ success: boolean; skill_name?: string; message: string; path?: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/skills/import`, {
      method: "POST",
      body: JSON.stringify({ zip_file_path: zipFilePath }),
    }),
};

// ============ Model API（Agent 级别）============

export const modelApi = {
  /**
   * 获取 Agent 下的所有 Model
   */
  list: (businessUnitId: string, agentName: string): Promise<Model[]> =>
    request<Model[]>(`/api/business_units/${businessUnitId}/agents/${agentName}/models`),

  /**
   * 获取 Model 详情
   */
  get: (businessUnitId: string, agentName: string, modelName: string): Promise<Model> =>
    request<Model>(`/api/business_units/${businessUnitId}/agents/${agentName}/models/${modelName}`),

  /**
   * 获取 Model 配置文件原始内容
   */
  getConfig: (businessUnitId: string, agentName: string, modelName: string): Promise<{ content: string }> =>
    request<{ content: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/models/${modelName}/config`),

  /**
   * 创建 Model
   */
  create: (businessUnitId: string, agentName: string, data: ModelCreate): Promise<Model> =>
    request<Model>(`/api/business_units/${businessUnitId}/agents/${agentName}/models`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 Model
   */
  update: (businessUnitId: string, agentName: string, modelName: string, data: ModelUpdate): Promise<Model> =>
    request<Model>(`/api/business_units/${businessUnitId}/agents/${agentName}/models/${modelName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 Model
   */
  delete: (businessUnitId: string, agentName: string, modelName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/models/${modelName}`, {
      method: "DELETE",
    }),

};

// ============ MCP API（Agent 级别）============

export const mcpApi = {
  /**
   * 获取 Agent 下的所有 MCP
   */
  list: (businessUnitId: string, agentName: string): Promise<MCP[]> =>
    request<MCP[]>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps`),

  /**
   * 获取 MCP 详情
   */
  get: (businessUnitId: string, agentName: string, mcpName: string): Promise<MCP> =>
    request<MCP>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps/${mcpName}`),

  /**
   * 创建 MCP
   */
  create: (businessUnitId: string, agentName: string, data: MCPCreate): Promise<MCP> =>
    request<MCP>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 更新 MCP
   */
  update: (businessUnitId: string, agentName: string, mcpName: string, data: MCPUpdate): Promise<MCP> =>
    request<MCP>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps/${mcpName}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /**
   * 删除 MCP
   */
  delete: (businessUnitId: string, agentName: string, mcpName: string): Promise<{ message: string }> =>
    request<{ message: string }>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps/${mcpName}`, {
      method: "DELETE",
    }),

  /**
   * 切换 MCP 启用状态
   */
  toggleEnabled: (businessUnitId: string, agentName: string, mcpName: string, enabled: boolean): Promise<{ message: string; enabled: boolean }> =>
    request<{ message: string; enabled: boolean }>(`/api/business_units/${businessUnitId}/agents/${agentName}/mcps/${mcpName}/toggle?enabled=${enabled}`, {
      method: "POST",
    }),
};

// ============ Agent Runtime API ============

import type {
  ExecuteRequest,
  ExecutionResult,
  StatusResponse,
  ServiceStatusResponse,
} from "@/types/agent-runtime";

export interface ConversationHistoryTurn {
  created_at: string;
  user_input: string;
  messages: Array<Record<string, any>>;
}

export interface ConversationHistoryResponse {
  agent_name: string;
  thread_id: string;
  history_file: string;
  turns: ConversationHistoryTurn[];
}

export const agentRuntimeApi = {
  /**
   * 加载 Agent
   */
  load: (businessUnitId: string, agentName: string): Promise<{ message: string; agent_name: string; business_unit_id: string }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/load`, {
      method: "POST",
    }),

  /**
   * 获取流式执行 SSE URL
   */
  getStreamUrl: (businessUnitId: string, agentName: string): string =>
    `${API_BASE_URL}/api/runtime/${businessUnitId}/agents/${agentName}/execute/stream`,

  /**
   * 获取 Agent 执行状态
   */
  getStatus: (businessUnitId: string, agentName: string): Promise<StatusResponse> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/status`),

  /**
   * 取消 Agent 执行
   */
  cancel: (businessUnitId: string, agentName: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/cancel`, {
      method: "POST",
    }),

  /**
   * 获取 Agent 会话历史
   */
  getConversationHistory: (businessUnitId: string, agentName: string, threadId?: string): Promise<ConversationHistoryResponse> =>
    request(
      `/api/runtime/${businessUnitId}/agents/${agentName}/history${threadId ? `?thread_id=${encodeURIComponent(threadId)}` : ""}`
    ),

  /**
   * 清理 Agent 对话上下文
   */
  clearContext: (businessUnitId: string, agentName: string, threadId?: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/context${threadId ? `?thread_id=${encodeURIComponent(threadId)}` : ""}`, {
      method: "DELETE",
    }),

  /**
   * 卸载 Agent
   */
  unload: (businessUnitId: string, agentName: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/unload`, {
      method: "DELETE",
    }),

  /**
   * 获取执行快照（断线重连）
   */
  getExecutionSnapshot: (businessUnitId: string, agentName: string, executionId: string): Promise<any> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/execution/${executionId}/snapshot`),

  /**
   * 列出已加载的 Agent
   */
  listLoaded: (): Promise<any[]> =>
    request("/api/runtime/agents/loaded"),
};

// ============ Model Runtime API ============

export const modelRuntimeApi = {
  /**
   * 加载 Model（Agent 下的 Model）
   */
  load: (businessUnitId: string, agentName: string, modelName: string): Promise<{ message: string; model_name: string; business_unit_id: string }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/load`, {
      method: "POST",
    }),

  /**
   * 执行 Model（同步）
   */
  execute: (businessUnitId: string, agentName: string, modelName: string, data: ExecuteRequest): Promise<ExecutionResult> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/execute`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * 执行 Model（流式）- 使用 fetch 实现
   */
  executeStream: async function* (
    businessUnitId: string,
    agentName: string,
    modelName: string,
    data: ExecuteRequest
  ): AsyncGenerator<any, void, unknown> {
    const response = await fetch(
      `${API_BASE_URL}/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/execute/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getLanguageHeaders(),
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data;
          } catch {
            // 忽略解析错误
          }
        }
      }
    }
  },

  /**
   * 获取 Model 执行状态
   */
  getStatus: (businessUnitId: string, agentName: string, modelName: string): Promise<StatusResponse> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/status`),

  /**
   * 取消 Model 执行
   */
  cancel: (businessUnitId: string, agentName: string, modelName: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/cancel`, {
      method: "POST",
    }),

  /**
   * 卸载 Model
   */
  unload: (businessUnitId: string, agentName: string, modelName: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/runtime/${businessUnitId}/agents/${agentName}/models/${modelName}/unload`, {
      method: "DELETE",
    }),
};

// ============ Foreman API ============

import type {
  ForemanAgentDirectoryItem,
  ForemanConversationDetail,
  ForemanConversationSummary,
  ForemanMessage,
} from "@/types/foreman";

interface ForemanConversationListResponse {
  conversations: ForemanConversationSummary[];
}

interface ForemanTimelineResponse {
  conversation_id: string;
  messages: ForemanMessage[];
  total: number;
}

export const foremanApi = {
  listAgents: (): Promise<ForemanAgentDirectoryItem[]> =>
    request("/api/foreman/agents"),

  createConversation: (agentIds: string[], title?: string): Promise<ForemanConversationDetail> =>
    request("/api/foreman/conversations", {
      method: "POST",
      body: JSON.stringify({ agent_ids: agentIds, title }),
    }),

  listConversations: (): Promise<ForemanConversationListResponse> =>
    request("/api/foreman/conversations"),

  getConversation: (id: string): Promise<ForemanConversationDetail> =>
    request(`/api/foreman/conversations/${id}`),

  deleteConversation: (id: string): Promise<{ message: string; success: boolean }> =>
    request(`/api/foreman/conversations/${id}`, { method: "DELETE" }),

  addMembers: (id: string, agentIds: string[]): Promise<ForemanConversationDetail> =>
    request(`/api/foreman/conversations/${id}/members`, {
      method: "POST",
      body: JSON.stringify({ agent_ids: agentIds }),
    }),

  getMessages: (id: string, limit = 50, offset = 0): Promise<ForemanTimelineResponse> =>
    request(`/api/foreman/conversations/${id}/messages?limit=${limit}&offset=${offset}`),

  getStreamUrl: (id: string): string =>
    `${API_BASE_URL}/api/foreman/conversations/${id}/messages/stream`,

  clearContext: (id: string): Promise<{ message: string; results: any[] }> =>
    request(`/api/foreman/conversations/${id}/context`, { method: "DELETE" }),
};

// ============ 默认导出 ============

// 导入 LLM API
import { llmApi } from './llm-api';

export default {
  healthCheck,
  readyCheck,
  getSupportedLocales,
  businessUnit: businessUnitApi,
  assetBundle: assetBundleApi,
  asset: assetApi,
  agent: agentApi,
  model: modelApi,
  mcp: mcpApi,
  agentRuntime: agentRuntimeApi,
  modelRuntime: modelRuntimeApi,
  foreman: foremanApi,
  llm: llmApi,
};

// 重新导出 LLM API
export { llmApi } from './llm-api';
export type { ProviderOption, ModelOption, ProviderSummary } from './llm-api';
