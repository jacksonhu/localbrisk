"""
Models 模块初始化
"""

from app.models.catalog import (
    # 基础模型
    BaseInfo,
    BaseInfoCreate,
    BaseInfoUpdate,
    EntityType,
    # Catalog 相关
    Catalog,
    CatalogCreate,
    CatalogUpdate,
    CatalogTreeNode,
    # Schema 相关
    Schema,
    SchemaCreate,
    SchemaUpdate,
    SchemaType,
    # 连接相关
    ConnectionConfig,
    ConnectionType,
    # Asset 相关
    Asset,
    AssetCreate,
    AssetType,
    VolumeType,
    # Agent 相关
    Agent,
    AgentCreate,
    AgentUpdate,
    AgentLLMConfig,
    AgentInstruction,
    AgentRouting,
    AgentCapabilities,
    AgentGovernance,
    AgentPromptTemplate,
    AgentNativeSkill,
    AgentMCPTool,
    AgentHumanInTheLoop,
    # Model 相关
    Model,
    ModelCreate,
    ModelUpdate,
    ModelType,
    LocalModelProvider,
    LocalModelSource,
    EndpointProvider,
    # Prompt 相关
    Prompt,
    PromptCreate,
    PromptUpdate,
)

__all__ = [
    # 基础模型
    "BaseInfo",
    "BaseInfoCreate",
    "BaseInfoUpdate",
    "EntityType",
    # Catalog 相关
    "Catalog",
    "CatalogCreate",
    "CatalogUpdate",
    "CatalogTreeNode",
    # Schema 相关
    "Schema",
    "SchemaCreate",
    "SchemaUpdate",
    "SchemaType",
    # 连接相关
    "ConnectionConfig",
    "ConnectionType",
    # Asset 相关
    "Asset",
    "AssetCreate",
    "AssetType",
    "VolumeType",
    # Agent 相关
    "Agent",
    "AgentCreate",
    "AgentUpdate",
    "AgentLLMConfig",
    "AgentInstruction",
    "AgentRouting",
    "AgentCapabilities",
    "AgentGovernance",
    "AgentPromptTemplate",
    "AgentNativeSkill",
    "AgentMCPTool",
    "AgentHumanInTheLoop",
    # Model 相关
    "Model",
    "ModelCreate",
    "ModelUpdate",
    "ModelType",
    "LocalModelProvider",
    "LocalModelSource",
    "EndpointProvider",
    # Prompt 相关
    "Prompt",
    "PromptCreate",
    "PromptUpdate",
]
