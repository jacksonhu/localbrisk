"""
全局常量定义

定义系统中使用的文件名、目录名等常量，确保全局一致性。

树形结构定义：
├── BusinessUnit (业务单元)
│   ├── config.yaml                          # BusinessUnit 配置文件
│   ├── agents/{agent_name}/                 # Agent 智能体目录
│   │   ├── agent_spec.yaml                  # Agent 配置文件
│   │   ├── prompts/                         # 提示词目录
│   │   ├── skills/                          # 技能目录
│   │   ├── models/                          # Model 配置目录
│   │   │   └── {model_name}.yaml
│   │   ├── mcps/                            # MCP 配置目录
│   │   │   └── {mcp_name}.yaml
│   │   └── workroot/                        # 工作记录目录
│   │       └── {session_id}/
│   └── asset_bundles/{bundle_name}/         # 资源包目录
│       ├── bundle.yaml                      # 资源包配置
│       ├── tables/                          # 表映射目录
│       ├── functions/                       # 自定义函数目录
│       └── volumes/                         # 文档存储目录
"""

# ============================================================
# 配置文件名常量
# ============================================================

# BusinessUnit 层配置文件
BUSINESS_UNIT_CONFIG_FILE = "config.yaml"

# Agent 层配置文件
AGENT_CONFIG_FILE = "agent_spec.yaml"

# AssetBundle 层配置文件
ASSET_BUNDLE_CONFIG_FILE = "bundle.yaml"

# 资产文件扩展名
ASSET_FILE_SUFFIX = ".yaml"


# ============================================================
# 目录名称常量
# ============================================================

# BusinessUnit 下的一级目录
AGENTS_DIR = "agents"                    # Agent 目录
ASSET_BUNDLES_DIR = "asset_bundles"      # 资源包目录

# AssetBundle 下的资产目录（按资产类型分类）
TABLES_DIR = "tables"                    # 表映射目录
VOLUMES_DIR = "volumes"                  # 文档存储目录
FUNCTIONS_DIR = "functions"              # 自定义函数目录
NOTES_DIR = "notes"                      # 笔记目录

# Agent 下的子目录
AGENT_PROMPTS_DIR = "prompts"            # 提示词目录
AGENT_SKILLS_DIR = "skills"              # 技能目录
AGENT_MODELS_DIR = "models"              # Model 配置目录
AGENT_MCPS_DIR = "mcps"                  # MCP 配置目录
AGENT_WORKROOT_DIR = "workroot"          # 工作记录目录


# ============================================================
# 资产类型映射
# ============================================================

# AssetBundle 下的资产类型字符串 -> 目录名
BUNDLE_ASSET_TYPE_TO_DIR = {
    "table": TABLES_DIR,
    "volume": VOLUMES_DIR,
    "function": FUNCTIONS_DIR,
    "note": NOTES_DIR,
}

# Agent 下的子资源类型 -> 目录名
AGENT_RESOURCE_TYPE_TO_DIR = {
    "prompt": AGENT_PROMPTS_DIR,
    "skill": AGENT_SKILLS_DIR,
    "model": AGENT_MODELS_DIR,
    "mcp": AGENT_MCPS_DIR,
    "workroot": AGENT_WORKROOT_DIR,
}


# ============================================================
# MCP 类型常量
# ============================================================

MCP_TYPE_PYTHON_FUNCTION = "python_function"
MCP_TYPE_MCP_SERVER = "mcp_server"
MCP_TYPE_REMOTE_API = "remote_api"

MCP_TYPES = [
    MCP_TYPE_PYTHON_FUNCTION,
    MCP_TYPE_MCP_SERVER,
    MCP_TYPE_REMOTE_API,
]


# ============================================================
# 工作会话状态
# ============================================================

WORK_SESSION_STATUS_ACTIVE = "active"
WORK_SESSION_STATUS_COMPLETED = "completed"
WORK_SESSION_STATUS_ARCHIVED = "archived"

WORK_SESSION_STATUSES = [
    WORK_SESSION_STATUS_ACTIVE,
    WORK_SESSION_STATUS_COMPLETED,
    WORK_SESSION_STATUS_ARCHIVED,
]


# ============================================================
# 输出类型常量
# ============================================================

OUTPUT_TYPE_TEXT = "text"
OUTPUT_TYPE_CODE = "code"
OUTPUT_TYPE_IMAGE = "image"
OUTPUT_TYPE_DATA = "data"
OUTPUT_TYPE_FILE = "file"

OUTPUT_TYPES = [
    OUTPUT_TYPE_TEXT,
    OUTPUT_TYPE_CODE,
    OUTPUT_TYPE_IMAGE,
    OUTPUT_TYPE_DATA,
    OUTPUT_TYPE_FILE,
]
