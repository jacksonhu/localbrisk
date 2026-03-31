"""
Global constants.

Defines file names, directory names, and other constants used throughout the system
to ensure global consistency.

Directory tree structure:
├── BusinessUnit
│   ├── config.yaml                          # BusinessUnit config file
│   ├── agents/{agent_name}/                 # Agent directory
│   │   ├── agent_spec.yaml                  # Agent config file
│   │   ├── memories/                        # Memory/prompt directory
│   │   ├── skills/                          # Skills directory
│   │   ├── models/                          # Model config directory
│   │   │   └── {model_name}.yaml
│   │   ├── mcps/                            # MCP config directory
│   │   │   └── {mcp_name}.yaml
│   │   └── output/                          # Work output directory
│   │       └── {session_id}/
│   └── asset_bundles/{bundle_name}/         # Asset bundle directory
│       ├── bundle.yaml                      # Asset bundle config
│       ├── tables/                          # Table mapping directory
│       ├── functions/                       # Custom function directory
│       └── volumes/                         # Document storage directory
"""

# ============================================================
# Config file name constants
# ============================================================

# BusinessUnit level config file
BUSINESS_UNIT_CONFIG_FILE = "config.yaml"

# Agent level config file
AGENT_CONFIG_FILE = "agent_spec.yaml"

# AssetBundle level config file
ASSET_BUNDLE_CONFIG_FILE = "bundle.yaml"

# Asset file extension
ASSET_FILE_SUFFIX = ".yaml"


# ============================================================
# Directory name constants
# ============================================================

# Top-level directories under BusinessUnit
AGENTS_DIR = "agents"                    # Agent directory
ASSET_BUNDLES_DIR = "asset_bundles"      # Asset bundle directory

# Asset directories under AssetBundle (by asset type)
TABLES_DIR = "tables"                    # Table mapping directory
VOLUMES_DIR = "volumes"                  # Document storage directory
FUNCTIONS_DIR = "functions"              # Custom function directory
NOTES_DIR = "notes"                      # Notes directory

# Subdirectories under Agent
AGENT_MEMORIES_DIR = "memories"          # Memory/prompt directory
AGENT_SKILLS_DIR = "skills"              # Skills directory
AGENT_MODELS_DIR = "models"              # Model config directory
AGENT_MCPS_DIR = "mcps"                  # MCP config directory
AGENT_OUTPUT_DIR = "output"              # Work output directory


# ============================================================
# Asset type mappings
# ============================================================

# AssetBundle asset type string -> directory name
BUNDLE_ASSET_TYPE_TO_DIR = {
    "table": TABLES_DIR,
    "volume": VOLUMES_DIR,
    "function": FUNCTIONS_DIR,
    "note": NOTES_DIR,
}

# Agent sub-resource type -> directory name
AGENT_RESOURCE_TYPE_TO_DIR = {
    "prompt": AGENT_MEMORIES_DIR,
    "skill": AGENT_SKILLS_DIR,
    "model": AGENT_MODELS_DIR,
    "mcp": AGENT_MCPS_DIR,
    "output": AGENT_OUTPUT_DIR,
}


# ============================================================
# MCP type constants
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
# Work session status
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
# Output type constants
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
