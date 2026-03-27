"""
Models 模块初始化
定义 BusinessUnit、AssetBundle、Agent、Model、MCP 等核心数据结构
"""

from app.models.business_unit import (
    # 基础模型
    BaseInfo,
    BaseInfoCreate,
    BaseInfoUpdate,
    EntityType,
    # BusinessUnit 相关
    BusinessUnit,
    BusinessUnitCreate,
    BusinessUnitUpdate,
    BusinessUnitTreeNode,
    # AssetBundle 相关
    AssetBundle,
    AssetBundleCreate,
    AssetBundleUpdate,
    AssetBundleType,
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
    # Model 相关
    Model,
    ModelCreate,
    ModelUpdate,
    ModelType,
    LocalModelProvider,
    LocalModelSource,
    EndpointProvider,
    # MCP 相关
    MCP,
    MCPCreate,
    MCPUpdate,
    MCPType,
    MCPPythonFunctionConfig,
    MCPServerConfig,
    MCPRemoteAPIConfig,
    # Output 相关
    WorkSession,
    WorkOutput,
    # Memory 相关
    Memory,
    MemoryCreate,
    MemoryUpdate,
)

__all__ = [
    # 基础模型
    "BaseInfo",
    "BaseInfoCreate",
    "BaseInfoUpdate",
    "EntityType",
    # BusinessUnit 相关
    "BusinessUnit",
    "BusinessUnitCreate",
    "BusinessUnitUpdate",
    "BusinessUnitTreeNode",
    # AssetBundle 相关
    "AssetBundle",
    "AssetBundleCreate",
    "AssetBundleUpdate",
    "AssetBundleType",
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
    # Model 相关
    "Model",
    "ModelCreate",
    "ModelUpdate",
    "ModelType",
    "LocalModelProvider",
    "LocalModelSource",
    "EndpointProvider",
    # MCP 相关
    "MCP",
    "MCPCreate",
    "MCPUpdate",
    "MCPType",
    "MCPPythonFunctionConfig",
    "MCPServerConfig",
    "MCPRemoteAPIConfig",
    # Output 相关
    "WorkSession",
    "WorkOutput",
    # Memory 相关
    "Memory",
    "MemoryCreate",
    "MemoryUpdate",
]
