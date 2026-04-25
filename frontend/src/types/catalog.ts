/**
 * 业务单元类型定义
 */

// ============ 枚举类型 ============

/** 实体类型枚举 */
export type EntityType = 
  | "business_unit"
  | "asset_bundle"
  | "agent" 
  | "table" 
  | "volume" 
  | "model" 
  | "prompt" 
  | "skill" 
  | "note" 
  | "function"
  | "mcp"
  | "output";

/** 数据库连接类型 */
export type ConnectionType = "mysql" | "postgresql" | "sqlite" | "duckdb";

/** AssetBundle 类型 */
export type AssetBundleType = "local" | "external";

/** 资产类型 */
export type AssetType = "table" | "volume" | "agent" | "note" | "function";

/** Volume 存储类型 */
export type VolumeType = "local" | "s3";

/** 导航树节点类型 */
export type NodeType = 
  | "business_unit"
  | "asset_bundle"
  | "asset_type" 
  | "table" 
  | "volume" 
  | "agent" 
  | "note" 
  | "function" 
  | "model" 
  | "placeholder" 
  | "folder" 
  | "skill" 
  | "prompt"
  | "mcp"
  | "output"
  | "output_file";

/** MCP 类型 */
export type MCPType = "python_function" | "mcp_server" | "remote_api";

/** 工作会话状态 */
export type WorkSessionStatus = "active" | "completed" | "archived";

/** 输出类型 */
export type OutputType = "text" | "code" | "image" | "data" | "file";

// ============ 基础实体类型 ============

/**
 * 基础实体接口
 * 所有业务单元下的实体都具有这些基础属性
 */
export interface BaseEntity {
  /** 名称（唯一标识，用于文件夹/文件名） */
  name: string;
  /** 展示名称（UI 显示用） */
  display_name?: string;
  /** 描述 */
  description?: string;
  /** 标签列表 */
  tags?: string[];
  /** 实体类型 */
  entity_type?: EntityType;
  /** 文件系统路径 */
  path?: string;
  /** 创建时间 */
  created_at?: string;
  /** 更新时间 */
  updated_at?: string;
}

/** 创建实体的基础请求 */
export interface BaseEntityCreate {
  name: string;
  display_name?: string;
  description?: string;
  tags?: string[];
}

/** 更新实体的基础请求 */
export interface BaseEntityUpdate {
  display_name?: string;
  description?: string;
  tags?: string[];
}

// ============ 连接配置 ============

/** 外部数据库连接配置 - 属于 AssetBundle 级别 */
export interface ConnectionConfig {
  type: ConnectionType;
  host?: string;
  port: number;
  db_name: string;
  username?: string;
  password?: string;
}

// ============ BusinessUnit 相关 ============

/** BusinessUnit 完整信息 */
export interface BusinessUnit extends BaseEntity {
  id: string;
  entity_type?: "business_unit";
  owner: string;
  asset_bundles: AssetBundle[];
  agents?: Agent[];
}

/** 创建 BusinessUnit 请求 */
export interface BusinessUnitCreate extends BaseEntityCreate {
  owner?: string;
}

/** 更新 BusinessUnit 请求 */
export interface BusinessUnitUpdate extends BaseEntityUpdate {}

// ============ AssetBundle 相关 ============

/** AssetBundle 完整信息 */
export interface AssetBundle extends BaseEntity {
  id: string;
  business_unit_id: string;
  owner: string;
  entity_type?: "asset_bundle";
  bundle_type: AssetBundleType;
  connection?: ConnectionConfig;
  synced_at?: string;
}

/** 创建 AssetBundle 请求 */
export interface AssetBundleCreate extends BaseEntityCreate {
  owner?: string;
  bundle_type: AssetBundleType;
  connection?: ConnectionConfig;
}

/** 更新 AssetBundle 请求 */
export interface AssetBundleUpdate extends BaseEntityUpdate {
  connection?: ConnectionConfig;
}

// ============ Asset 相关 ============

/** Asset 元数据 */
export interface AssetMetadata {
  is_directory: boolean;
  extension?: string;
  size?: number;
  [key: string]: any;
}

/** Asset 完整信息 */
export interface Asset extends BaseEntity {
  id: string;
  bundle_id: string;
  asset_type: AssetType;
  metadata: AssetMetadata;
}

/** 创建 Asset 请求 */
export interface AssetCreate extends BaseEntityCreate {
  asset_type: AssetType;
  // Volume 特有字段
  volume_type?: VolumeType;
  storage_location?: string;
  s3_endpoint?: string;
  s3_bucket?: string;
  s3_access_key?: string;
  s3_secret_key?: string;
  // Table 特有字段
  format?: "parquet" | "csv" | "json" | "delta";
  // Function 特有字段
  language?: string;
}

// ============ 导航树 ============

/** 导航树节点 */
export interface BusinessUnitTreeNode {
  id: string;
  name: string;
  display_name: string;
  node_type: NodeType;
  children: BusinessUnitTreeNode[];
  icon?: string;
  bundle_type?: AssetBundleType;
  metadata: Record<string, any>;
}

/** 前端树形展示用的项目 */
export interface BusinessUnitItem {
  id: string;
  name: string;
  type: NodeType;
  icon?: string;
  expanded?: boolean;
  children?: BusinessUnitItem[];
  metadata?: Record<string, any>;
  bundle_type?: AssetBundleType;
}

// ============ 辅助类型 ============

/** 表格列定义 */
export interface Column {
  name: string;
  type: string;
  nullable: boolean;
  description?: string;
}

/** Table 详细信息 */
export interface Table extends BaseEntity {
  id: string;
  bundle_id: string;
  entity_type?: "table";
  format: "parquet" | "csv" | "json" | "delta";
  columns?: Column[];
}

/** Volume 信息 */
export interface Volume extends BaseEntity {
  id: string;
  bundle_id: string;
  entity_type?: "volume";
  volume_type: VolumeType;
  storage_location?: string;
  s3_endpoint?: string;
  s3_bucket?: string;
  s3_access_key?: string;
  s3_secret_key?: string;
}

// ============ MCP 相关 ============

/** Python 函数 MCP 配置 */
export interface MCPPythonFunctionConfig {
  function_file: string;
  function_name: string;
  parameters?: Record<string, any>;
}

/** MCP Server 配置 */
export interface MCPServerConfig {
  server_command: string;
  server_args?: string[];
  env?: Record<string, string>;
  tools?: string[];
}

/** 远程 API MCP 配置 */
export interface MCPRemoteAPIConfig {
  api_url: string;
  api_key?: string;
  headers?: Record<string, string>;
  endpoints?: Array<Record<string, any>>;
}

/** MCP 信息 */
export interface MCP extends BaseEntity {
  id: string;
  agent_id: string;
  entity_type?: "mcp";
  mcp_type: MCPType;
  enabled: boolean;
  python_config?: MCPPythonFunctionConfig;
  server_config?: MCPServerConfig;
  api_config?: MCPRemoteAPIConfig;
}

/** 创建 MCP 请求 */
export interface MCPCreate extends BaseEntityCreate {
  mcp_type: MCPType;
  enabled?: boolean;
  python_config?: MCPPythonFunctionConfig;
  server_config?: MCPServerConfig;
  api_config?: MCPRemoteAPIConfig;
}

/** 更新 MCP 请求 */
export interface MCPUpdate extends BaseEntityUpdate {
  enabled?: boolean;
  python_config?: MCPPythonFunctionConfig;
  server_config?: MCPServerConfig;
  api_config?: MCPRemoteAPIConfig;
}

// ============ Agent 相关 ============

/** Agent 元数据 */
export interface AgentMetadata {
  display_name?: string;
  description?: string;
}

/** Agent LLM 配置 */
export interface AgentLLMConfig {
  llm_model?: string;
  temperature?: number;
  max_tokens?: number;
  response_format?: "text" | "json_object";
}

/**
 * Agent 信息
 *
 * 对应后端简化后的 agent_spec.yaml：
 * - instruction: 字符串形式的 system prompt 模板（运行时渲染占位符）
 * - skills: 在 yaml 中已启用的原生技能名称列表
 * - available_skills: 目录扫描得到的全部可用技能
 * - memories: 目录扫描得到的 markdown 文件名列表（运行时全部自动加载）
 * - models: 目录扫描得到的模型配置名称列表
 * - mcps: 目录扫描得到的 MCP 配置名称列表
 * - llm_config.llm_model 是当前激活模型的唯一来源
 */
export interface Agent extends BaseEntity {
  id: string;
  business_unit_id: string;
  entity_type?: "agent";
  owner?: string;

  // 配置节
  instruction?: string;
  llm_config?: AgentLLMConfig;

  // 启用态 + 目录扫描结果
  skills: string[];
  available_skills: string[];
  memories: string[];
  models: string[];
  mcps: string[];
}

/** 创建 Agent 请求 */
export interface AgentCreate extends BaseEntityCreate {}

/**
 * 更新 Agent 请求（支持部分更新）
 * - instruction: 直接修改 system prompt 模板
 * - llm_config.llm_model: 切换激活模型
 * - skills: 启用的原生技能名称列表（后端会与目录扫描结果取交集）
 */
export interface AgentUpdate extends BaseEntityUpdate {
  instruction?: string;
  llm_config?: AgentLLMConfig;
  skills?: string[];
}

// ============ Model 相关 ============

/** 模型类型 */
export type ModelType = "local" | "endpoint";

/** 本地模型提供商 */
export type LocalModelProvider = 
  | "qianwen" 
  | "deepseek" 
  | "llama" 
  | "mistral" 
  | "chatglm" 
  | "baichuan" 
  | "internlm" 
  | "qwen2" 
  | "other";

/** 本地模型来源 */
export type LocalModelSource = "volume" | "huggingface";

/** API 端点提供商 */
export type EndpointProvider = 
  | "openai" 
  | "claude" 
  | "qianwen" 
  | "qianfan" 
  | "gemini" 
  | "deepseek" 
  | "zhipu" 
  | "moonshot" 
  | "other";

/** Model 信息 */
export interface Model extends BaseEntity {
  id: string;
  agent_id: string;
  entity_type?: "model";
  model_type: ModelType;
  enabled: boolean;
  // 本地模型字段
  local_provider?: string;
  local_source?: string;
  volume_reference?: string;
  huggingface_repo?: string;
  huggingface_filename?: string;
  // API 端点字段
  endpoint_provider?: string;
  api_base_url?: string;
  api_key?: string;
  model_id?: string;
  // 运行时参数
  temperature?: number;
}

/** 创建 Model 请求 */
export interface ModelCreate extends BaseEntityCreate {
  model_type: ModelType;
  enabled?: boolean;
  // 本地模型字段
  local_provider?: string;
  local_source?: string;
  volume_reference?: string;
  huggingface_repo?: string;
  huggingface_filename?: string;
  // API 端点字段
  endpoint_provider?: string;
  api_base_url?: string;
  api_key?: string;
  model_id?: string;
  // 运行时参数
  temperature?: number;
}

/** 更新 Model 请求 */
export interface ModelUpdate extends BaseEntityUpdate {
  enabled?: boolean;
  api_key?: string;
  api_base_url?: string;
  model_id?: string;
  temperature?: number;
}

// ============ Output 相关 ============

/** 工作会话 */
export interface WorkSession {
  id: string;
  name: string;
  agent_id: string;
  created_at?: string;
  updated_at?: string;
  status: WorkSessionStatus;
  summary?: string;
  outputs: string[];
}

/** 工作输出 */
export interface WorkOutput {
  id: string;
  session_id: string;
  name: string;
  output_type: OutputType;
  content?: string;
  file_path?: string;
  created_at?: string;
  metadata?: Record<string, any>;
}

/** output 文件内容 */
export interface OutputFileContent {
  path: string;
  relative_path: string;
  content: string;
}

// ============ Memory 相关 ============

/** Memory 信息 */
export interface Memory extends BaseEntity {
  entity_type?: "prompt";
  content: string;
}

/** 创建 Memory 请求 */
export interface MemoryCreate extends BaseEntityCreate {
  content: string;
}

/** 更新 Memory 请求 */
export interface MemoryUpdate extends BaseEntityUpdate {
  content?: string;
}

// ============ Note 相关 ============

/** Note 信息 */
export interface Note extends BaseEntity {
  id: string;
  bundle_id: string;
  entity_type?: "note";
  content: string;
}

// ============ API 响应 ============

/** 删除响应 */
export interface DeleteResponse {
  message: string;
}

/** 错误响应 */
export interface ErrorResponse {
  detail: string;
}

/** 同步结果 */
export interface SyncResult {
  success: boolean;
  schemas_synced: number;
  tables_synced: number;
  columns_synced: number;
  errors: string[];
  warnings: string[];
}
