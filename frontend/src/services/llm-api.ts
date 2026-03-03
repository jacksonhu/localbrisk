/**
 * LLM 配置 API 服务
 * 从后端获取 LLM 提供商和模型配置
 */

import type { Component } from 'vue';

const API_BASE_URL = "http://127.0.0.1:8765";

/**
 * 通用请求方法
 */
async function request<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * 提供商选项接口
 */
export interface ProviderOption {
  value: string;
  label: string;
  provider_type: string;
  default_url: string;
  icon: string | null;
  auth_type: string;
  rate_limit: number | null;
  timeout: number;
  description: string | null;
}

/**
 * 模型选项接口
 */
export interface ModelOption {
  value: string;
  label: string;
  context_length: number | null;
  max_tokens: number | null;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  supports_vision: boolean;
}

/**
 * 提供商摘要接口
 */
export interface ProviderSummary {
  endpoint_count: number;
  local_count: number;
  total_models: number;
  providers: {
    endpoint: string[];
    local: string[];
  };
}

/**
 * LLM API 服务
 */
export const llmApi = {
  /**
   * 获取 API 端点提供商列表
   */
  getEndpointProviders: (): Promise<ProviderOption[]> =>
    request<ProviderOption[]>("/api/llm/providers/endpoint"),

  /**
   * 获取本地模型提供商列表
   */
  getLocalProviders: (): Promise<ProviderOption[]> =>
    request<ProviderOption[]>("/api/llm/providers/local"),

  /**
   * 获取所有提供商列表
   */
  getAllProviders: (): Promise<ProviderOption[]> =>
    request<ProviderOption[]>("/api/llm/providers"),

  /**
   * 获取指定提供商信息
   */
  getProvider: (providerId: string): Promise<ProviderOption> =>
    request<ProviderOption>(`/api/llm/providers/${providerId}`),

  /**
   * 获取提供商的模型列表
   */
  getProviderModels: (providerId: string): Promise<ModelOption[]> =>
    request<ModelOption[]>(`/api/llm/providers/${providerId}/models`),

  /**
   * 获取提供商默认 API URL
   */
  getProviderDefaultUrl: async (providerId: string): Promise<string> => {
    const result = await request<{ default_url: string }>(`/api/llm/providers/${providerId}/default-url`);
    return result.default_url;
  },

  /**
   * 获取指定模型信息
   */
  getModel: (providerId: string, modelId: string): Promise<ModelOption> =>
    request<ModelOption>(`/api/llm/providers/${providerId}/models/${modelId}`),

  /**
   * 获取提供商摘要信息
   */
  getSummary: (): Promise<ProviderSummary> =>
    request<ProviderSummary>("/api/llm/summary"),

  /**
   * 搜索提供商
   */
  searchProviders: (query: string): Promise<ProviderOption[]> =>
    request<ProviderOption[]>(`/api/llm/search/providers?q=${encodeURIComponent(query)}`),

  /**
   * 搜索模型
   */
  searchModels: (query: string): Promise<Array<{ provider_id: string; model: ModelOption }>> =>
    request<Array<{ provider_id: string; model: ModelOption }>>(`/api/llm/search/models?q=${encodeURIComponent(query)}`),
};

export default llmApi;
