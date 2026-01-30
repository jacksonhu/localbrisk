/**
 * Catalog 类型定义
 * 基于 API 文档定义
 */

// ============ 枚举类型 ============

/** 数据库连接类型 */
export type ConnectionType = "mysql" | "postgresql" | "sqlite" | "duckdb";

/** Schema 来源类型 */
export type SchemaSource = "local" | "connection";

/** 资产类型 */
export type AssetType = "table" | "volume" | "agent" | "note" | "function" | "model";

/** Volume 存储类型 */
export type VolumeType = "local" | "s3";

/** 导航树节点类型 */
export type NodeType = "catalog" | "schema" | "asset_type" | "table" | "volume" | "agent" | "note" | "function" | "model" | "placeholder" | "folder" | "skill" | "prompt";

// ============ 连接配置 ============

/** 外部数据库连接配置 */
export interface ConnectionConfig {
  type: ConnectionType;
  host?: string;
  port: number;
  db_name: string;
  username?: string;
  password?: string;
  sync_schema?: boolean;
}

// ============ Catalog 相关 ============

/** Catalog 完整信息 */
export interface Catalog {
  id: string;
  name: string;
  display_name: string;
  owner: string;
  description?: string;
  tags: string[];
  path: string;
  has_connections: boolean;
  allow_custom_schema: boolean;
  created_at: string;
  updated_at: string;
  schemas: Schema[];
  agents?: Agent[];  // Catalog 下的 Agent 列表
  models?: Model[];  // Catalog 下的 Model 列表
  connections?: ConnectionConfig[];
}

/** 创建 Catalog 请求 */
export interface CatalogCreate {
  name: string;
  display_name?: string;
  owner?: string;
  description?: string;
  allow_custom_schema?: boolean;
  connections?: ConnectionConfig[];
}

/** 更新 Catalog 请求 */
export interface CatalogUpdate {
  display_name?: string;
  description?: string;
  tags?: string[];
  allow_custom_schema?: boolean;
  connections?: ConnectionConfig[];
}

// ============ Schema 相关 ============

/** Schema 完整信息 */
export interface Schema {
  id: string;
  name: string;
  catalog_id: string;
  owner: string;
  description?: string;
  source: SchemaSource;
  connection_name?: string;
  readonly: boolean;
  path?: string;
  created_at: string;
}

/** 创建 Schema 请求 */
export interface SchemaCreate {
  name: string;
  owner?: string;
  description?: string;
}

/** 更新 Schema 请求 */
export interface SchemaUpdate {
  description?: string;
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
export interface Asset {
  id: string;
  name: string;
  schema_id: string;
  asset_type: AssetType;
  path: string;
  metadata: AssetMetadata;
  created_at: string;
  updated_at?: string;
}

/** 创建 Asset 请求 */
export interface AssetCreate {
  name: string;
  asset_type: AssetType;
  description?: string;
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
  readonly: boolean;
  source?: SchemaSource;
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
  readonly?: boolean;
  source?: SchemaSource;
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
export interface Table {
  id: string;
  name: string;
  schema_id: string;
  path: string;
  format: "parquet" | "csv" | "json" | "delta";
  columns?: Column[];
}

/** Volume 信息 */
export interface Volume {
  id: string;
  name: string;
  schema_id: string;
  path: string;
  volume_type: VolumeType;
  storage_location?: string;       // 本地存储路径
  // S3 配置
  s3_endpoint?: string;
  s3_bucket?: string;
  s3_access_key?: string;
  s3_secret_key?: string;
}

/** Agent 信息 - Catalog 下的一级子项 */
export interface Agent {
  id: string;
  name: string;
  catalog_id: string;  // 所属 Catalog
  description?: string;
  path: string;  // Agent 文件夹路径
  system_prompt?: string;  // Agent 的系统提示词
  model_reference?: string;  // 引用的模型，格式：schema_name.model_name
  skills: string[];  // skills 文件列表
  prompts: string[];  // prompts (markdown) 文件列表
  created_at: string;
  updated_at?: string;
}

/** 创建 Agent 请求 */
export interface AgentCreate {
  name: string;
  description?: string;
  system_prompt?: string;
  model_reference?: string;  // 引用的模型
}

/** 更新 Agent 请求 */
export interface AgentUpdate {
  description?: string;
  system_prompt?: string;
  model_reference?: string;  // 引用的模型
}

/** Note 信息 */
export interface Note {
  id: string;
  name: string;
  schema_id: string;
  content: string;
  created_at: string;
  updated_at: string;
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
export interface Model {
  id: string;
  name: string;
  schema_id: string;  // 所属 Schema
  description?: string;
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
  path: string;
  created_at: string;
  updated_at?: string;
}

/** 创建 Model 请求 */
export interface ModelCreate {
  name: string;
  description?: string;
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
export interface ModelUpdate {
  description?: string;
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
