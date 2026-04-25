"""
Business unit data models.
Defines core data structures: BusinessUnit, AssetBundle, Agent, Model, MCP, etc.

Design principles:
1. All entity base attributes are placed under the 'baseinfo' section in YAML files
2. Entity-specific configurations are at the same level as baseinfo

baseinfo standard fields:
- name: Name (unique identifier)
- display_name: Display name
- description: Description
- tags: Tag list
- owner: Owner
- created_at: Creation time
- updated_at: Update time

Directory tree structure:
├── BusinessUnit
│   ├── agents/{agent_name}/
│   │   ├── agent_spec.yaml
│   │   ├── memories/
│   │   ├── skills/
│   │   ├── models/                    # Model config directory
│   │   │   └── {model_name}.yaml
│   │   ├── mcps/                      # MCP config directory
│   │   │   └── {mcp_name}.yaml
│   │   └── output/                    # Work output directory
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


# ==================== Enum Types ====================

class EntityType(str, Enum):
    """Entity type."""
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
    """Database connection type."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"


class AssetBundleType(str, Enum):
    """AssetBundle type."""
    LOCAL = "local"
    EXTERNAL = "external"


class AssetType(str, Enum):
    """Asset type."""
    TABLE = "table"
    VOLUME = "volume"
    AGENT = "agent"
    NOTE = "note"


class VolumeType(str, Enum):
    """Volume storage type."""
    LOCAL = "local"
    S3 = "s3"


class ModelType(str, Enum):
    """Model type."""
    LOCAL = "local"
    ENDPOINT = "endpoint"


class LocalModelProvider(str, Enum):
    """Local model provider."""
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
    """Local model source."""
    VOLUME = "volume"
    HUGGINGFACE = "huggingface"


class EndpointProvider(str, Enum):
    """API endpoint provider."""
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
    """MCP type."""
    PYTHON_FUNCTION = "python_function"    # Python function
    MCP_SERVER = "mcp_server"              # MCP Server
    REMOTE_API = "remote_api"              # Remote API


# ==================== BaseInfo Models ====================

class BaseInfo(BaseModel):
    """
    Base info model - corresponds to the 'baseinfo' section in YAML files.
    Shared base attributes for all entities.
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
    """Request model for creating entity baseinfo."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: Optional[str] = None


class BaseInfoUpdate(BaseModel):
    """Request model for updating entity baseinfo."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ==================== Connection Config ====================

class ConnectionConfig(BaseModel):
    """Database connection configuration."""
    type: ConnectionType
    host: str = "127.0.0.1"
    port: int
    db_name: str
    username: Optional[str] = None
    password: Optional[str] = None
    
    class Config:
        use_enum_values = True


# ==================== AssetBundle Models ====================

class AssetBundleCreate(BaseInfoCreate):
    """Create AssetBundle request."""
    bundle_type: str = Field(default="local", pattern="^(local|external)$")
    connection: Optional[ConnectionConfig] = None


class AssetBundleUpdate(BaseInfoUpdate):
    """Update AssetBundle request."""
    connection: Optional[ConnectionConfig] = None


class AssetBundle(BaseModel):
    """AssetBundle data model."""
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


# ==================== BusinessUnit Models ====================

class BusinessUnitCreate(BaseInfoCreate):
    """Create BusinessUnit request."""
    pass


class BusinessUnitUpdate(BaseInfoUpdate):
    """Update BusinessUnit request."""
    pass


class BusinessUnit(BaseModel):
    """BusinessUnit data model."""
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


# ==================== Asset Models ====================

class AssetCreate(BaseInfoCreate):
    """Create Asset request."""
    asset_type: AssetType
    # Volume fields
    volume_type: Optional[str] = Field(default="local", pattern="^(local|s3)$")
    storage_location: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    # Table fields
    format: Optional[str] = Field(default=None, pattern="^(parquet|csv|json|delta)$")
    
    class Config:
        use_enum_values = True


class Asset(BaseModel):
    """Generic asset model."""
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


# ==================== MCP Models ====================

class MCPPythonFunctionConfig(BaseModel):
    """Python function MCP configuration."""
    function_file: str                    # Python file path (relative to mcps directory)
    function_name: str                    # Function name
    parameters: Dict[str, Any] = Field(default_factory=dict)  # Parameter configuration


class MCPServerConfig(BaseModel):
    """MCP Server configuration."""
    server_command: str                   # Start command
    server_args: List[str] = Field(default_factory=list)      # Start arguments
    env: Dict[str, str] = Field(default_factory=dict)         # Environment variables
    tools: List[str] = Field(default_factory=list)            # Available tools list


class MCPRemoteAPIConfig(BaseModel):
    """Remote API MCP configuration."""
    api_url: str                          # API base URL
    api_key: Optional[str] = None         # API key
    headers: Dict[str, str] = Field(default_factory=dict)     # Custom request headers
    endpoints: List[Dict[str, Any]] = Field(default_factory=list)  # Endpoint configuration


class MCPCreate(BaseInfoCreate):
    """Create MCP request."""
    mcp_type: MCPType
    enabled: bool = True
    # Python function config
    python_config: Optional[MCPPythonFunctionConfig] = None
    # MCP Server config
    server_config: Optional[MCPServerConfig] = None
    # Remote API config
    api_config: Optional[MCPRemoteAPIConfig] = None
    
    class Config:
        use_enum_values = True


class MCPUpdate(BaseInfoUpdate):
    """Update MCP request."""
    enabled: Optional[bool] = None
    python_config: Optional[MCPPythonFunctionConfig] = None
    server_config: Optional[MCPServerConfig] = None
    api_config: Optional[MCPRemoteAPIConfig] = None


class MCP(BaseModel):
    """MCP data model."""
    id: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    agent_id: str                         # Owning Agent
    entity_type: EntityType = EntityType.MCP
    mcp_type: MCPType
    enabled: bool = True
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Configuration
    python_config: Optional[MCPPythonFunctionConfig] = None
    server_config: Optional[MCPServerConfig] = None
    api_config: Optional[MCPRemoteAPIConfig] = None
    
    class Config:
        use_enum_values = True


# ==================== Agent Models ====================

class AgentLLMConfig(BaseModel):
    """Agent LLM runtime configuration."""
    llm_model: Optional[str] = None       # References a Model name under this Agent


class AgentCreate(BaseInfoCreate):
    """Create Agent request."""
    pass


class AgentUpdate(BaseInfoUpdate):
    """Update Agent request.

    Supports partial updates of:
    - ``instruction``: free-form system prompt template string.
    - ``llm_config``: active model selection for the runtime.
    - ``skills``: enabled native skill names (subset of the ``skills/`` directory).
    """
    instruction: Optional[str] = None
    llm_config: Optional[AgentLLMConfig] = None
    skills: Optional[List[str]] = None


class Agent(BaseModel):
    """Agent data model."""
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

    # System prompt template (rendered at runtime with {{agent_name}}, {{agent_path}}, {{now}})
    instruction: Optional[str] = None
    # Active LLM model configuration
    llm_config: Optional[AgentLLMConfig] = None

    # Enabled native skills (subset of available_skills, persisted in agent_spec.yaml)
    skills: List[str] = Field(default_factory=list)
    # Directory scan results (available but not necessarily enabled)
    available_skills: List[str] = Field(default_factory=list)
    memories: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    mcps: List[str] = Field(default_factory=list)


# ==================== Memory Models ====================

class MemoryCreate(BaseInfoCreate):
    """Create Memory request."""
    content: str = ""


class MemoryUpdate(BaseInfoUpdate):
    """Update Memory request."""
    content: Optional[str] = None


class Memory(BaseModel):
    """Memory data model."""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    entity_type: EntityType = EntityType.PROMPT
    content: str
    path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== Model Models ====================

class ModelCreate(BaseInfoCreate):
    """Create Model request."""
    model_type: ModelType
    enabled: bool = False
    # Local model fields
    local_provider: Optional[LocalModelProvider] = None
    local_source: Optional[LocalModelSource] = None
    volume_reference: Optional[str] = None
    huggingface_repo: Optional[str] = None
    huggingface_filename: Optional[str] = None
    # API endpoint fields
    endpoint_provider: Optional[EndpointProvider] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    # Runtime parameters
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Temperature parameter, range 0.0 to 2.0")
    
    class Config:
        use_enum_values = True


class ModelUpdate(BaseInfoUpdate):
    """Update Model request."""
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Temperature parameter, range 0.0 to 2.0")


class Model(BaseModel):
    """Model data model - belongs to Agent."""
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
    # Local model fields
    local_provider: Optional[str] = None
    local_source: Optional[str] = None
    volume_reference: Optional[str] = None
    huggingface_repo: Optional[str] = None
    huggingface_filename: Optional[str] = None
    # API endpoint fields
    endpoint_provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    # Runtime parameters
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Temperature parameter, range 0.0 to 2.0")
    
    class Config:
        use_enum_values = True


# ==================== Output Models ====================

class WorkSession(BaseModel):
    """Work session."""
    id: str
    name: str
    agent_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "active"                # active, completed, archived
    summary: Optional[str] = None
    outputs: List[str] = Field(default_factory=list)  # Output file list


class WorkOutput(BaseModel):
    """Work output."""
    id: str
    session_id: str
    name: str
    output_type: str                      # text, code, image, data, file
    content: Optional[str] = None
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== Navigation Tree Models ====================

class BusinessUnitTreeNode(BaseModel):
    """Navigation tree node (BusinessUnit tree)."""
    id: str
    name: str
    display_name: str
    node_type: str                        # business_unit, asset_bundle, agent, model, mcp, etc.
    children: List["BusinessUnitTreeNode"] = Field(default_factory=list)
    icon: Optional[str] = None
    bundle_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


BusinessUnitTreeNode.model_rebuild()
