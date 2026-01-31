"""
全局常量定义

定义系统中使用的文件名、目录名等常量，确保全局一致性。

树形结构定义：
├── Catalog (Namespace)
│   ├── config.yaml                     # Catalog 配置文件
│   ├── agents/{agent_name}/            # Agent 智能体目录
│   │   └── agent_spec.yaml                  # Agent 配置文件
│   └── schemas/{schema_name}/          # Schema 逻辑库目录
│       ├── schema.yaml                 # Schema 配置文件
│       ├── models/                     # 模型定义目录
│       ├── tables/                     # 表映射目录
│       ├── functions/                  # 自定义函数目录
│       └── volumes/                    # 文档存储目录
"""

# ============================================================
# 配置文件名常量
# ============================================================

# Catalog 层配置文件
CATALOG_CONFIG_FILE = "config.yaml"

# Agent 层配置文件
AGENT_CONFIG_FILE = "agent_spec.yaml"

# Schema 层配置文件
SCHEMA_CONFIG_FILE = "schema.yaml"

# 资产文件扩展名
ASSET_FILE_SUFFIX = ".yaml"


# ============================================================
# 目录名称常量
# ============================================================

# Catalog 下的一级目录
AGENTS_DIR = "agents"       # Agent 目录
SCHEMAS_DIR = "schemas"     # Schema 目录

# Schema 下的资产目录（按资产类型分类）
TABLES_DIR = "tables"       # 表映射目录
VOLUMES_DIR = "volumes"     # 文档存储目录
FUNCTIONS_DIR = "functions" # 自定义函数目录
MODELS_DIR = "models"       # 模型定义目录
NOTES_DIR = "notes"         # 笔记目录


# ============================================================
# 资产类型映射
# ============================================================

# 资产类型字符串 -> 目录名
ASSET_TYPE_TO_DIR = {
    "table": TABLES_DIR,
    "volume": VOLUMES_DIR,
    "function": FUNCTIONS_DIR,
    "model": MODELS_DIR,
    "agent": AGENTS_DIR,
    "note": NOTES_DIR,
}

# 目录名 -> 资产类型字符串
DIR_TO_ASSET_TYPE = {v: k for k, v in ASSET_TYPE_TO_DIR.items()}
