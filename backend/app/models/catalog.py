"""
Catalog 数据模型
定义 Catalog、Schema、Table 等核心数据结构
支持基于文件系统的混合 Catalog 实现

树形结构定义：
├── Catalog (Namespace)
│   ├── agents/{agent_name}/           # Agent 智能体目录
│   │   ├── agent.yaml                 # Agent 配置（提示词策略、Skills 列表）
│   │   ├── prompts/                   # 提示词模板目录
│   │   └── skills/                    # Skills 文件目录
│   └── schemas/{schema_name}/         # Schema 逻辑库目录
│       ├── schema.yaml                # Schema 配置（资产发现规则）
│       ├── models/                    # 模型定义目录
│       ├── tables/                    # 表映射目录
│       ├── functions/                 # 自定义函数目录
│       └── volumes/                   # 文档存储目录

物理存储映射：
- Catalog 层: App_Data/Catalogs/{catalog_name}/
  - 包含 config.yaml：定义连接池（Connection）和 Catalog 元数据
- Agent 层: Catalog 目录下的 agents/{agent_name}/ 文件夹
  - 包含 agent.yaml：定义提示词策略和引用的 Skills 列表
- Schema 层: Catalog 目录下的 schemas/{schema_name}/ 文件夹
  - 包含 schema.yaml：定义资产发现规则（是否同步远程表）
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConnectionType(str, Enum):
    """数据库连接类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"


class SchemaSource(str, Enum):
    """Schema 来源类型"""
    LOCAL = "local"           # 本地文件系统创建
    CONNECTION = "connection"  # 外部数据库连接同步


class AssetType(str, Enum):
    """资产类型"""
    TABLE = "table"
    VOLUME = "volume"
    AGENT = "agent"
    NOTE = "note"


class VolumeType(str, Enum):
    """Volume 存储类型"""
    LOCAL = "local"    # 本地文件夹
    S3 = "s3"          # S3 对象存储


class ModelType(str, Enum):
    """模型类型"""
    LOCAL = "local"        # 本地模型
    ENDPOINT = "endpoint"  # API 端点


class LocalModelProvider(str, Enum):
    """本地模型提供商（开源模型类型）"""
    QIANWEN = "qianwen"        # 通义千问
    DEEPSEEK = "deepseek"      # DeepSeek
    LLAMA = "llama"            # Llama
    MISTRAL = "mistral"        # Mistral
    CHATGLM = "chatglm"        # ChatGLM
    BAICHUAN = "baichuan"      # 百川
    INTERNLM = "internlm"      # InternLM
    QWEN2 = "qwen2"            # Qwen2
    OTHER = "other"            # 其他


class LocalModelSource(str, Enum):
    """本地模型来源"""
    VOLUME = "volume"          # 引用 Catalog.Schema.Volume
    HUGGINGFACE = "huggingface"  # HuggingFace


class EndpointProvider(str, Enum):
    """API 端点提供商"""
    OPENAI = "openai"          # OpenAI
    CLAUDE = "claude"          # Anthropic Claude
    QIANWEN = "qianwen"        # 阿里云通义千问
    QIANFAN = "qianfan"        # 百度千帆
    GEMINI = "gemini"          # Google Gemini
    DEEPSEEK = "deepseek"      # DeepSeek API
    ZHIPU = "zhipu"            # 智谱 AI
    MOONSHOT = "moonshot"      # Moonshot AI
    OTHER = "other"            # 其他


# ==================== Connection 相关模型 ====================

class ConnectionConfig(BaseModel):
    """数据库连接配置"""
    type: ConnectionType
    host: str = "127.0.0.1"
    port: int
    db_name: str
    username: Optional[str] = None
    password: Optional[str] = None
    sync_schema: bool = True  # 是否同步 Schema
    
    class Config:
        use_enum_values = True


# ==================== Catalog Config 相关模型 ====================

class CatalogConfig(BaseModel):
    """
    Catalog 配置文件模型 (config.json)
    每个 Catalog 文件夹内的配置文件
    """
    catalog_id: str
    display_name: str
    connections: List[ConnectionConfig] = Field(default_factory=list)
    allow_custom_schema: bool = True  # 是否允许用户手动创建 Schema
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== Schema 相关模型 ====================

class SchemaCreate(BaseModel):
    """创建 Schema 的请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    owner: Optional[str] = None
    description: Optional[str] = None


class SchemaUpdate(BaseModel):
    """更新 Schema 的请求模型"""
    description: Optional[str] = None


class Schema(BaseModel):
    """Schema 数据模型"""
    id: str
    name: str
    catalog_id: str
    owner: str
    description: Optional[str] = None
    source: SchemaSource = SchemaSource.LOCAL  # 来源类型
    connection_name: Optional[str] = None  # 如果是外部连接，记录连接名
    readonly: bool = False  # 外部连接的 Schema 通常是只读的
    path: Optional[str] = None  # 文件系统路径
    created_at: datetime
    
    class Config:
        use_enum_values = True


# ==================== Catalog 相关模型 ====================

class CatalogCreate(BaseModel):
    """创建 Catalog 的请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    allow_custom_schema: bool = True
    connections: List[ConnectionConfig] = Field(default_factory=list)


class CatalogUpdate(BaseModel):
    """更新 Catalog 的请求模型"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    allow_custom_schema: Optional[bool] = None
    connections: Optional[List[ConnectionConfig]] = None


class Catalog(BaseModel):
    """Catalog 数据模型"""
    id: str
    name: str  # 文件夹名称
    display_name: str  # 显示名称
    owner: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    path: str  # 文件系统路径
    has_connections: bool = False  # 是否配置了外部连接
    allow_custom_schema: bool = True
    created_at: datetime
    updated_at: datetime
    schemas: List[Schema] = Field(default_factory=list)
    agents: List["Agent"] = Field(default_factory=list)  # Catalog 下的 Agent 列表
    connections: List[ConnectionConfig] = Field(default_factory=list)  # 连接配置


# ==================== Asset 相关模型 ====================

class AssetCreate(BaseModel):
    """创建 Asset 的请求模型（通用）"""
    name: str = Field(..., min_length=1, max_length=100)
    asset_type: AssetType
    description: Optional[str] = None
    # Volume 特有字段
    volume_type: Optional[str] = Field(default="local", pattern="^(local|s3)$")
    storage_location: Optional[str] = None  # 本地存储路径（仅 local 类型）
    # S3 对象存储配置（仅 s3 类型）
    s3_endpoint: Optional[str] = None       # S3 服务端点
    s3_bucket: Optional[str] = None         # Bucket 名称
    s3_access_key: Optional[str] = None     # Access Key
    s3_secret_key: Optional[str] = None     # Secret Key
    # Table 特有字段（预留）
    format: Optional[str] = Field(default=None, pattern="^(parquet|csv|json|delta)$")
    # Function 特有字段（预留）
    language: Optional[str] = None  # 函数语言，如 python, sql
    # Model 特有字段（预留）
    model_type: Optional[str] = None  # 模型类型
    
    class Config:
        use_enum_values = True


class Asset(BaseModel):
    """通用资产模型"""
    id: str
    name: str
    schema_id: str
    asset_type: AssetType
    path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class Table(BaseModel):
    """Table 数据模型"""
    id: str
    name: str
    schema_id: str
    path: str
    format: str = Field(pattern="^(parquet|csv|json|delta)$")
    columns: List[dict] = Field(default_factory=list)
    source: SchemaSource = SchemaSource.LOCAL
    readonly: bool = False


class Volume(BaseModel):
    """Volume 数据模型 - 用于存放 PDF 等文件"""
    id: str
    name: str
    schema_id: str
    path: str
    volume_type: str = Field(default="local", pattern="^(local|s3)$")
    storage_location: Optional[str] = None  # 本地存储路径
    # S3 配置
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    file_count: int = 0


class AgentCreate(BaseModel):
    """创建 Agent 的请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None  # Agent 的系统提示词
    model_reference: Optional[str] = None  # 引用的模型，格式：schema_name.model_name


class AgentUpdate(BaseModel):
    """更新 Agent 的请求模型"""
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_reference: Optional[str] = None  # 引用的模型
    enabled_skills: Optional[List[str]] = None  # 已启用的 skills 列表
    enabled_prompts: Optional[List[str]] = None  # 已启用的 prompts 列表


class Agent(BaseModel):
    """Agent 数据模型 - Catalog 下的一级子项，与 Schema 同级"""
    id: str
    name: str
    catalog_id: str  # 所属 Catalog
    description: Optional[str] = None
    path: str  # Agent 文件夹路径
    system_prompt: Optional[str] = None  # Agent 的系统提示词
    model_reference: Optional[str] = None  # 引用的模型，格式：schema_name.model_name
    skills: List[str] = Field(default_factory=list)  # skills 文件列表
    prompts: List[str] = Field(default_factory=list)  # prompts (markdown) 文件列表
    enabled_skills: List[str] = Field(default_factory=list)  # 已启用的 skills 列表
    enabled_prompts: List[str] = Field(default_factory=list)  # 已启用的 prompts 列表
    created_at: datetime
    updated_at: Optional[datetime] = None


class Note(BaseModel):
    """Note 数据模型"""
    id: str
    name: str
    schema_id: str
    content: str
    file_path: str
    created_at: datetime
    updated_at: datetime


# ==================== Prompt 相关模型 ====================

class PromptCreate(BaseModel):
    """创建 Prompt 的请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    content: str = ""


class PromptUpdate(BaseModel):
    """更新 Prompt 的请求模型"""
    content: Optional[str] = None


class Prompt(BaseModel):
    """Prompt 数据模型 - Agent 下的子资源"""
    name: str
    content: str
    enabled: bool = False  # 是否在 agent.yaml 的 enabled_prompts 中
    path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== Model 相关模型 ====================

class ModelCreate(BaseModel):
    """创建 Model 的请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    model_type: ModelType  # local 或 endpoint
    
    # 本地模型特有字段
    local_provider: Optional[LocalModelProvider] = None  # 开源模型类型
    local_source: Optional[LocalModelSource] = None  # 模型来源（volume 或 huggingface）
    volume_reference: Optional[str] = None  # catalog.schema.volume 引用路径
    huggingface_repo: Optional[str] = None  # HuggingFace 仓库 ID
    huggingface_filename: Optional[str] = None  # 模型文件名
    
    # API 端点特有字段
    endpoint_provider: Optional[EndpointProvider] = None  # API 提供商
    api_base_url: Optional[str] = None  # API 基础 URL
    api_key: Optional[str] = None  # API Key
    model_id: Optional[str] = None  # 模型 ID（如 gpt-4, claude-3-opus 等）
    
    class Config:
        use_enum_values = True


class ModelUpdate(BaseModel):
    """更新 Model 的请求模型"""
    description: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_id: Optional[str] = None


class Model(BaseModel):
    """Model 数据模型 - Schema 下的资产类型"""
    id: str
    name: str
    schema_id: str  # 所属 Schema
    description: Optional[str] = None
    model_type: ModelType  # local 或 endpoint
    
    # 本地模型字段
    local_provider: Optional[str] = None
    local_source: Optional[str] = None
    volume_reference: Optional[str] = None
    huggingface_repo: Optional[str] = None
    huggingface_filename: Optional[str] = None
    
    # API 端点字段
    endpoint_provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None  # 存储时会加密
    model_id: Optional[str] = None
    
    path: str  # Model 配置文件路径
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# ==================== 树形结构响应模型 ====================

class CatalogTreeNode(BaseModel):
    """Catalog 导航树节点"""
    id: str
    name: str
    display_name: str
    node_type: str  # catalog, schema, table, volume, agent, note
    children: List["CatalogTreeNode"] = Field(default_factory=list)
    icon: Optional[str] = None
    readonly: bool = False
    source: Optional[str] = None  # local 或 connection 名称
    metadata: Dict[str, Any] = Field(default_factory=dict)


# 支持自引用
CatalogTreeNode.model_rebuild()