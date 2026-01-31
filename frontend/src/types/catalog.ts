/**
 * Catalog 类型定义
 * 基于 API 文档定义
 */

// ============ 枚举类型 ============

/** 实体类型枚举 */
export type EntityType = 
  | "catalog" 
  | "schema" 
  | "agent" 
  | "table" 
  | "volume" 
  | "model" 
  | "prompt" 
  | "skill" 
  | "note" 
  | "function";

/** 数据库连接类型 */
export type ConnectionType = "mysql" | "postgresql" | "sqlite" | "duckdb";

/** Schema 类型 */
export type SchemaType = "local" | "external";

/** 资产类型 */
export type AssetType = "table" | "volume" | "agent" | "note" | "function" | "model";

/** Volume 存储类型 */
export type VolumeType = "local" | "s3";

/** 导航树节点类型 */
export type NodeType = "catalog" | "schema" | "asset_type" | "table" | "volume" | "agent" | "note" | "function" | "model" | "placeholder" | "folder" | "skill" | "prompt";

// ============ 基础实体类型 ============

/**
 * 基础实体接口
 * 所有 Catalog 下的实体都具有这些基础属性
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

/** 外部数据库连接配置 - 现在属于 Schema 级别 */
export interface ConnectionConfig {
  type: ConnectionType;
  host?: string;
  port: number;
  db_name: string;
  username?: string;
  password?: string;
}

// ============ Catalog 相关 ============

/** Catalog 完整信息 */
export interface Catalog extends BaseEntity {
  id: string;
  entity_type?: "catalog";
  owner: string;
  schemas: Schema[];
  agents?: Agent[];  // Catalog 下的 Agent 列表
}

/** 创建 Catalog 请求 */
export interface CatalogCreate extends BaseEntityCreate {
  owner?: string;
}

/** 更新 Catalog 请求 */
export interface CatalogUpdate extends BaseEntityUpdate {}

// ============ Schema 相关 ============

/** Schema 完整信息 */
export interface Schema extends BaseEntity {
  id: string;
  catalog_id: string;
  owner: string;
  entity_type?: "schema";
  schema_type: SchemaType;  // Schema 类型：local 或 external
  connection?: ConnectionConfig;  // 数据库连接配置（External 类型必须有）
  synced_at?: string;  // 最后同步时间（仅 External 类型有）
}

/** 创建 Schema 请求 */
export interface SchemaCreate extends BaseEntityCreate {
  owner?: string;
  schema_type: SchemaType;  // Schema 类型
  connection?: ConnectionConfig;  // External 类型必填
}

/** 更新 Schema 请求 */
export interface SchemaUpdate extends BaseEntityUpdate {
  connection?: ConnectionConfig;  // 仅 External 类型可更新
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
  schema_id: string;
  asset_type: AssetType;
  metadata: AssetMetadata;
}

/** 创建 Asset 请求 */
export interface AssetCreate extends BaseEntityCreate {
  asset_type: AssetType;
  // Volume 特有字段
  volume_type?: VolumeType;
  storage_location?: string;      // 本地存储路径（仅 local 类型）
  // S3 对象存储配置（仅 s3 类型）
  s3_endpoint?: string;           // S3 服务端点
  s3_bucket?: string;             // Bucket 名称
  s3_access_key?: string;         // Access Key
  s3_secret_key?: string;         // Secret Key
  // Table 特有字段（预留）
  format?: "parquet" | "csv" | "json" | "delta";
  // Function 特有字段（预留）
  language?: string;
  // Model 特有字段（预留）
  model_type?: string;
}

// ============ 导航树 ============

/** 导航树节点 */
export interface CatalogTreeNode {
  id: string;
  name: string;
  display_name: string;
  node_type: NodeType;
  children: CatalogTreeNode[];
  icon?: string;
  schema_type?: SchemaType;  // 仅 schema 节点有
  metadata: Record<string, any>;
}

/** 前端树形展示用的项目（兼容旧代码） */
export interface CatalogItem {
  id: string;
  name: string;
  type: NodeType;
  icon?: string;
  expanded?: boolean;
  children?: CatalogItem[];
  metadata?: Record<string, any>;
  schema_type?: SchemaType;  // 仅 schema 节点有
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
  schema_id: string;
  entity_type?: "table";
  format: "parquet" | "csv" | "json" | "delta";
  columns?: Column[];
}

/** Volume 信息 */
export interface Volume extends BaseEntity {
  id: string;
  schema_id: string;
  entity_type?: "volume";
  volume_type: VolumeType;
  storage_location?: string;       // 本地存储路径
  // S3 配置
  s3_endpoint?: string;
  s3_bucket?: string;
  s3_access_key?: string;
  s3_secret_key?: string;
}

/** Agent 元数据 - BMAD Spec 中的 metadata 节 */
export interface AgentMetadata {
  // 注意：不需要 ID 字段，Agent 的唯一性由 Catalog 下的目录路径决定
  display_name?: string;
  description?: string;
}

/** 用户提示词模板 - 对应 prompts/ 目录下的文件 */
export interface AgentPromptTemplate {
  name: string;
}

/** Agent 指令配置 */
export interface AgentInstruction {
  llm_model?: string;  // LLM 模型引用，引用 Schema 下定义的 Model 名称
  system_prompt?: string;
  user_prompt_templates?: AgentPromptTemplate[];  // 提示词模板（对应 prompts/ 目录）
}

/** Agent 路由配置 */
export interface AgentRouting {
  trigger_keywords?: string[];
  required_context_keys?: string[];
  next_possible_agents?: string[];
}

/** 原生技能 - 对应 skills/ 目录下的文件 */
export interface AgentNativeSkill {
  name: string;
}

/** MCP 工具配置 */
export interface AgentMCPTool {
  server_id: string;
  tools?: string[];
}

/** Agent 能力配置 */
export interface AgentCapabilities {
  native_skills?: AgentNativeSkill[];  // 原生技能（对应 skills/ 目录）
  mcp_tools?: AgentMCPTool[];
}

/** 人机协作配置 */
export interface AgentHumanInTheLoop {
  trigger?: string;
}

/** Agent 治理配置 */
export interface AgentGovernance {
  human_in_the_loop?: AgentHumanInTheLoop;
  termination_criteria?: string;
}

/** Agent 信息 - Catalog 下的一级子项（基于 BMAD Standard Spec） */
export interface Agent extends BaseEntity {
  id: string;
  catalog_id: string;
  entity_type?: "agent";
  
  // BMAD Standard Spec 配置节
  agent_metadata?: AgentMetadata;
  instruction?: AgentInstruction;
  routing?: AgentRouting;
  capabilities?: AgentCapabilities;
  governance?: AgentGovernance;
  
  // 兼容旧版字段（快捷访问）
  system_prompt?: string;
  llm_model?: string;  // LLM 模型引用
  
  // skills 和 prompts 文件列表（目录扫描结果）
  skills: string[];
  prompts: string[];
}

/** 创建 Agent 请求 - 简化版，仅需 name */
export interface AgentCreate extends BaseEntityCreate {}

/** 更新 Agent 请求 - 支持完整的 BMAD Spec 配置 */
export interface AgentUpdate extends BaseEntityUpdate {
  // BMAD Standard Spec 配置节
  metadata?: AgentMetadata;
  instruction?: AgentInstruction;
  routing?: AgentRouting;
  capabilities?: AgentCapabilities;
  governance?: AgentGovernance;
  
  // 兼容旧版字段
  system_prompt?: string;
  llm_model?: string;  // LLM 模型引用
}

/** Note 信息 */
export interface Note extends BaseEntity {
  id: string;
  schema_id: string;
  entity_type?: "note";
  content: string;
}

// ============ Model 相关 ============

/** 模型类型 */
export type ModelType = "local" | "endpoint";

/** 本地模型提供商（开源模型类型） */
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

/** Model 信息 - Schema 下的资产类型 */
export interface Model extends BaseEntity {
  id: string;
  schema_id: string;  // 所属 Schema
  entity_type?: "model";
  model_type: ModelType;
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
}

/** 创建 Model 请求 */
export interface ModelCreate extends BaseEntityCreate {
  model_type: ModelType;
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
}

/** 更新 Model 请求 */
export interface ModelUpdate extends BaseEntityUpdate {
  api_key?: string;
  api_base_url?: string;
  model_id?: string;
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

// ============ Prompt 相关 ============

/** Prompt 信息 - Agent 下的子资源 */
export interface Prompt extends BaseEntity {
  entity_type?: "prompt";
  content: string;
  enabled: boolean;  // 是否在 agent_spec.yaml 的 enabled_prompts 中
}

/** 创建 Prompt 请求 */
export interface PromptCreate extends BaseEntityCreate {
  content: string;
}

/** 更新 Prompt 请求 */
export interface PromptUpdate extends BaseEntityUpdate {
  content?: string;
}
