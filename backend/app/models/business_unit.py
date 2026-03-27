"""
业务单元数据模型
定义 BusinessUnit、AssetBundle、Agent、Model、MCP 等核心数据结构

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
├── BusinessUnit (业务单元)
│   ├── agents/{agent_name}/
│   │   ├── agent_spec.yaml
│   │   ├── prompts/
│   │   ├── skills/
│   │   ├── models/                    # Model 配置目录
│   │   │   └── {model_name}.yaml
│   │   ├── mcps/                      # MCP 配置目录
│   │   │   └── {mcp_name}.yaml
│   │   └── output/                  # 工作记录目录
│   │       └── {session_id}/
│   └── asset_bundles/{bundle_name}/
│       ├── bundle.yaml
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
    BUSINESS_UNIT = "business_unit"
    ASSET_BUNDLE = "asset_bundle"
    AGENT = "agent"
    TABLE = "table"
    VOLUME = "volume"
    MODEL = "model"
    PROMPT = "prompt"
    SKILL = "skill"
    NOTE = "note"
    FUNCTION = "function"
    MCP = "mcp"
    OUTPUT = "output"


class ConnectionType(str, Enum):
    """数据库连接类型"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"


class AssetBundleType(str, Enum):
    """AssetBundle 类型"""
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


class MCPType(str, Enum):
    """MCP 类型"""
    PYTHON_FUNCTION = "python_function"    # Python 函数
    MCP_SERVER = "mcp_server"              # MCP Server
    REMOTE_API = "remote_api"              # 远程 API


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


# ==================== AssetBundle 模型 ====================

class AssetBundleCreate(BaseInfoCreate):
    """创建 AssetBundle 请求"""
    bundle_type: str = Field(default="local", pattern="^(local|external)$")
    connection: Optional[ConnectionConfig] = None


class AssetBundleUpdate(BaseInfoUpdate):
    """更新 AssetBundle 请求"""
    connection: Optional[ConnectionConfig] = None


class AssetBundle(BaseModel):
    """AssetBundle 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    business_unit_id: str
    entity_type: EntityType = EntityType.ASSET_BUNDLE
    bundle_type: str = "local"
    connection: Optional[ConnectionConfig] = None
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# ==================== BusinessUnit 模型 ====================

class BusinessUnitCreate(BaseInfoCreate):
    """创建 BusinessUnit 请求"""
    pass


class BusinessUnitUpdate(BaseInfoUpdate):
    """更新 BusinessUnit 请求"""
    pass


class BusinessUnit(BaseModel):
    """BusinessUnit 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    entity_type: EntityType = EntityType.BUSINESS_UNIT
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    asset_bundles: List[AssetBundle] = Field(default_factory=list)
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
    bundle_id: str
    asset_type: AssetType
    entity_type: EntityType = EntityType.TABLE
    path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


# ==================== MCP 模型 ====================

class MCPPythonFunctionConfig(BaseModel):
    """Python 函数 MCP 配置"""
    function_file: str                    # Python 文件路径（相对于 mcps 目录）
    function_name: str                    # 函数名
    parameters: Dict[str, Any] = Field(default_factory=dict)  # 参数配置


class MCPServerConfig(BaseModel):
    """MCP Server 配置"""
    server_command: str                   # 启动命令
    server_args: List[str] = Field(default_factory=list)      # 启动参数
    env: Dict[str, str] = Field(default_factory=dict)         # 环境变量
    tools: List[str] = Field(default_factory=list)            # 可用工具列表


class MCPRemoteAPIConfig(BaseModel):
    """远程 API MCP 配置"""
    api_url: str                          # API 基础 URL
    api_key: Optional[str] = None         # API 密钥
    headers: Dict[str, str] = Field(default_factory=dict)     # 自定义请求头
    endpoints: List[Dict[str, Any]] = Field(default_factory=list)  # 端点配置


class MCPCreate(BaseInfoCreate):
    """创建 MCP 请求"""
    mcp_type: MCPType
    enabled: bool = True
    # Python 函数配置
    python_config: Optional[MCPPythonFunctionConfig] = None
    # MCP Server 配置
    server_config: Optional[MCPServerConfig] = None
    # 远程 API 配置
    api_config: Optional[MCPRemoteAPIConfig] = None
    
    class Config:
        use_enum_values = True


class MCPUpdate(BaseInfoUpdate):
    """更新 MCP 请求"""
    enabled: Optional[bool] = None
    python_config: Optional[MCPPythonFunctionConfig] = None
    server_config: Optional[MCPServerConfig] = None
    api_config: Optional[MCPRemoteAPIConfig] = None


class MCP(BaseModel):
    """MCP 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_id: str                         # 所属 Agent
    entity_type: EntityType = EntityType.MCP
    mcp_type: MCPType
    enabled: bool = True
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 配置
    python_config: Optional[MCPPythonFunctionConfig] = None
    server_config: Optional[MCPServerConfig] = None
    api_config: Optional[MCPRemoteAPIConfig] = None
    
    class Config:
        use_enum_values = True


# ==================== Agent 模型 ====================

class AgentLLMConfig(BaseModel):
    """Agent LLM 运行配置"""
    llm_model: Optional[str] = None       # 引用 Agent 下的 Model 名称


class AgentCreate(BaseInfoCreate):
    """创建 Agent 请求"""
    pass


class AgentUpdate(BaseInfoUpdate):
    """更新 Agent 请求"""
    llm_config: Optional[AgentLLMConfig] = None


class Agent(BaseModel):
    """Agent 数据模型"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "admin"
    business_unit_id: str
    entity_type: EntityType = EntityType.AGENT
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Agent 特有配置
    llm_config: Optional[AgentLLMConfig] = None
    # 目录扫描结果
    skills: List[str] = Field(default_factory=list)
    memories: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    mcps: List[str] = Field(default_factory=list)
    active_model: Optional[str] = None

    @property
    def prompts(self) -> List[str]:
        """兼容旧代码：prompts 等价于 memories（仅内部访问）"""
        return self.memories


# ==================== Memory 模型 ====================

class MemoryCreate(BaseInfoCreate):
    """创建 Memory 请求"""
    content: str = ""


class MemoryUpdate(BaseInfoUpdate):
    """更新 Memory 请求"""
    content: Optional[str] = None


class Memory(BaseModel):
    """Memory 数据模型"""
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
    enabled: bool = False
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
    # 运行时参数
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="温度参数，范围 0.0 到 2.0")
    
    class Config:
        use_enum_values = True


class ModelUpdate(BaseInfoUpdate):
    """更新 Model 请求"""
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="温度参数，范围 0.0 到 2.0")


class Model(BaseModel):
    """Model 数据模型 - 属于 Agent"""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_id: str
    entity_type: EntityType = EntityType.MODEL
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_type: ModelType
    enabled: bool = False
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
    # 运行时参数
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="温度参数，范围 0.0 到 2.0")
    
    class Config:
        use_enum_values = True


# ==================== Output 模型 ====================

class WorkSession(BaseModel):
    """工作会话"""
    id: str
    name: str
    agent_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "active"                # active, completed, archived
    summary: Optional[str] = None
    outputs: List[str] = Field(default_factory=list)  # 输出文件列表


class WorkOutput(BaseModel):
    """工作输出"""
    id: str
    session_id: str
    name: str
    output_type: str                      # text, code, image, data, file
    content: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== 导航树模型 ====================

class BusinessUnitTreeNode(BaseModel):
    """导航树节点 (BusinessUnit 树)"""
    id: str
    name: str
    display_name: str
    node_type: str                        # business_unit, asset_bundle, agent, model, mcp, etc.
    children: List["BusinessUnitTreeNode"] = Field(default_factory=list)
    icon: Optional[str] = None
    bundle_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


BusinessUnitTreeNode.model_rebuild()
