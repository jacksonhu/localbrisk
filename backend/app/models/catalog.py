"""
Catalog 数据模型
定义 Catalog、Schema、Asset、Agent、Model 等核心数据结构

设计原则：
1. 所有实体的基础属性统一放在 yaml 文件的 baseinfo 节下
2. 各实体特有配置与 baseinfo 同级

baseinfo 标准字段：
- name: 名称（唯一标识）
- display_name: 展示名称
- description: 描述
- tags: 标签列表
- owner: 所有者
- created_at: 创建时间
- updated_at: 更新时间

树形结构：
├── Catalog (Namespace)
│   ├── agents/{agent_name}/
│   │   ├── agent_spec.yaml
│   │   ├── prompts/
│   │   └── skills/
│   └── schemas/{schema_name}/
│       ├── schema.yaml
│       ├── models/
│       ├── tables/
│       ├── functions/
│       └── volumes/
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==================== 枚举类型 ====================

class EntityType(str, Enum):
    """实体类型"""
    CATALOG = "catalog"
    SCHEMA = "schema"
    AGENT = "agent"
    TABLE = "table"
    VOLUME = "volume"
    MODEL = "model"
    PROMPT = "prompt"
    SKILL = "skill"
    NOTE = "note"
    FUNCTION = "function"


class ConnectionType(str, Enum):
    """数据库连接类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"


class SchemaType(str, Enum):
    """Schema 类型"""
    LOCAL = "local"
    EXTERNAL = "external"


class AssetType(str, Enum):
    """资产类型"""
    TABLE = "table"
    VOLUME = "volume"
    AGENT = "agent"
    NOTE = "note"


class VolumeType(str, Enum):
    """Volume 存储类型"""
    LOCAL = "local"
    S3 = "s3"


class ModelType(str, Enum):
    """模型类型"""
    LOCAL = "local"
    ENDPOINT = "endpoint"


class LocalModelProvider(str, Enum):
    """本地模型提供商"""
    QIANWEN = "qianwen"
    DEEPSEEK = "deepseek"
    LLAMA = "llama"
    MISTRAL = "mistral"
    CHATGLM = "chatglm"
    BAICHUAN = "baichuan"
    INTERNLM = "internlm"
    QWEN2 = "qwen2"
    OTHER = "other"


class LocalModelSource(str, Enum):
    """本地模型来源"""
    VOLUME = "volume"
    HUGGINGFACE = "huggingface"


class EndpointProvider(str, Enum):
    """API 端点提供商"""
    OPENAI = "openai"
    CLAUDE = "claude"
    QIANWEN = "qianwen"
    QIANFAN = "qianfan"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    OTHER = "other"


# ==================== BaseInfo 模型 ====================

class BaseInfo(BaseModel):
    """
    基础信息模型 - 对应 yaml 文件中的 baseinfo 节
    所有实体共享的基础属性
    """
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class BaseInfoCreate(BaseModel):
    """创建实体时的 baseinfo 请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None


class BaseInfoUpdate(BaseModel):
    """更新实体时的 baseinfo 请求模型"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ==================== Connection 配置 ====================

class ConnectionConfig(BaseModel):
    """数据库连接配置"""
    type: ConnectionType
    host: str = "127.0.0.1"
    port: int
    db_name: str
    username: Optional[str] = None
    password: Optional[str] = None
    
    class Config:
        use_enum_values = True


# ==================== Schema 模型 ====================

class SchemaCreate(BaseInfoCreate):
    """创建 Schema 请求"""
    schema_type: str = Field(default="local", pattern="^(local|external)$")
    connection: Optional[ConnectionConfig] = None


class SchemaUpdate(BaseInfoUpdate):
    """更新 Schema 请求"""
    connection: Optional[ConnectionConfig] = None


class Schema(BaseModel):
    """Schema 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    catalog_id: str
    entity_type: EntityType = EntityType.SCHEMA
    schema_type: str = "local"
    connection: Optional[ConnectionConfig] = None
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# ==================== Catalog 模型 ====================

class CatalogCreate(BaseInfoCreate):
    """创建 Catalog 请求"""
    pass


class CatalogUpdate(BaseInfoUpdate):
    """更新 Catalog 请求"""
    pass


class Catalog(BaseModel):
    """Catalog 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    entity_type: EntityType = EntityType.CATALOG
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    schemas: List[Schema] = Field(default_factory=list)
    agents: List["Agent"] = Field(default_factory=list)


# ==================== Asset 模型 ====================

class AssetCreate(BaseInfoCreate):
    """创建 Asset 请求"""
    asset_type: AssetType
    # Volume 字段
    volume_type: Optional[str] = Field(default="local", pattern="^(local|s3)$")
    storage_location: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    # Table 字段
    format: Optional[str] = Field(default=None, pattern="^(parquet|csv|json|delta)$")
    
    class Config:
        use_enum_values = True


class Asset(BaseModel):
    """通用资产模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    schema_id: str
    asset_type: AssetType
    entity_type: EntityType = EntityType.TABLE
    path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# ==================== Agent 模型 ====================

class AgentPromptTemplate(BaseModel):
    """用户提示词模板"""
    name: str


class AgentLLMConfig(BaseModel):
    """Agent LLM 运行配置"""
    llm_model: Optional[str] = None
    temperature: Optional[float] = Field(default=0.2, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=2000, ge=1)
    response_format: Optional[str] = Field(default="text", pattern="^(text|json_object)$")


class AgentInstruction(BaseModel):
    """Agent 指令配置（提示词矩阵）"""
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    user_prompt_templates: List[AgentPromptTemplate] = Field(default_factory=list)


class AgentRouting(BaseModel):
    """Agent 路由配置"""
    trigger_keywords: List[str] = Field(default_factory=list)
    required_context_keys: List[str] = Field(default_factory=list)
    next_possible_agents: List[str] = Field(default_factory=list)


class AgentNativeSkill(BaseModel):
    """原生技能"""
    name: str


class AgentMCPTool(BaseModel):
    """MCP 工具配置"""
    server_id: str
    tools: List[str] = Field(default_factory=list)


class AgentCapabilities(BaseModel):
    """Agent 能力配置"""
    native_skills: List[AgentNativeSkill] = Field(default_factory=list)
    mcp_tools: List[AgentMCPTool] = Field(default_factory=list)


class AgentHumanInTheLoop(BaseModel):
    """人机协作配置"""
    trigger: Optional[str] = None


class AgentGovernance(BaseModel):
    """Agent 治理配置"""
    human_in_the_loop: Optional[AgentHumanInTheLoop] = None
    termination_criteria: Optional[str] = None


class AgentCreate(BaseInfoCreate):
    """创建 Agent 请求"""
    pass


class AgentUpdate(BaseInfoUpdate):
    """更新 Agent 请求"""
    llm_config: Optional[AgentLLMConfig] = None
    instruction: Optional[AgentInstruction] = None
    routing: Optional[AgentRouting] = None
    capabilities: Optional[AgentCapabilities] = None
    governance: Optional[AgentGovernance] = None


class Agent(BaseModel):
    """Agent 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    catalog_id: str
    entity_type: EntityType = EntityType.AGENT
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Agent 特有配置
    llm_config: Optional[AgentLLMConfig] = None
    instruction: Optional[AgentInstruction] = None
    routing: Optional[AgentRouting] = None
    capabilities: Optional[AgentCapabilities] = None
    governance: Optional[AgentGovernance] = None
    # 目录扫描结果
    skills: List[str] = Field(default_factory=list)
    prompts: List[str] = Field(default_factory=list)


# ==================== Prompt 模型 ====================

class PromptCreate(BaseInfoCreate):
    """创建 Prompt 请求"""
    content: str = ""


class PromptUpdate(BaseInfoUpdate):
    """更新 Prompt 请求"""
    content: Optional[str] = None


class Prompt(BaseModel):
    """Prompt 数据模型"""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entity_type: EntityType = EntityType.PROMPT
    content: str
    enabled: bool = False
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== Model 模型 ====================

class ModelCreate(BaseInfoCreate):
    """创建 Model 请求"""
    model_type: ModelType
    # 本地模型字段
    local_provider: Optional[LocalModelProvider] = None
    local_source: Optional[LocalModelSource] = None
    volume_reference: Optional[str] = None
    huggingface_repo: Optional[str] = None
    huggingface_filename: Optional[str] = None
    # API 端点字段
    endpoint_provider: Optional[EndpointProvider] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


class ModelUpdate(BaseInfoUpdate):
    """更新 Model 请求"""
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_id: Optional[str] = None


class Model(BaseModel):
    """Model 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    schema_id: str
    entity_type: EntityType = EntityType.MODEL
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_type: ModelType
    # 本地模型字段
    local_provider: Optional[str] = None
    local_source: Optional[str] = None
    volume_reference: Optional[str] = None
    huggingface_repo: Optional[str] = None
    huggingface_filename: Optional[str] = None
    # API 端点字段
    endpoint_provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    
    class Config:
        use_enum_values = True


# ==================== 导航树模型 ====================

class CatalogTreeNode(BaseModel):
    """Catalog 导航树节点"""
    id: str
    name: str
    display_name: str
    node_type: str
    children: List["CatalogTreeNode"] = Field(default_factory=list)
    icon: Optional[str] = None
    schema_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


CatalogTreeNode.model_rebuild()
