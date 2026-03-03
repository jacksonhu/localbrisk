"""
Agent 执行引擎模块

基于 LangChain DeepAgents SDK 实现的智能代理引擎，支持：
- 从 agent_spec.yaml 加载 Agent 配置
- 加载 skills、prompts、models 目录配置
- 支持多个 system prompt 拼接
- FilesystemBackend 文件系统后端

主要模块：
- deepagents_engine: DeepAgents SDK 集成的核心引擎
- agent_loader: Agent 配置加载和解析

依赖说明：
- agent_loader: 仅需要 pyyaml，可独立使用
- deepagents_engine: 需要 langchain-core, langchain-openai, deepagents
"""

# Agent 配置加载器 (无 langchain 依赖)
from .agent_loader import (
    AgentConfig,
    AgentConfigLoader,
    ModelInfo,
    PromptInfo,
    SkillInfo,
    get_agent_config_loader,
    load_agent_config,
)

# DeepAgents 引擎 (有依赖，延迟导入)
from .deepagents_engine import (
    DeepAgentsEngine,
    AgentBuildContext,
    get_deepagents_engine,
    check_dependencies,
)

__all__ = [
    # 配置加载器 (无依赖)
    "AgentConfig",
    "AgentConfigLoader",
    "ModelInfo",
    "PromptInfo",
    "SkillInfo",
    "get_agent_config_loader",
    "load_agent_config",
    # DeepAgents 引擎
    "DeepAgentsEngine",
    "AgentBuildContext",
    "get_deepagents_engine",
    "check_dependencies",
]
