"""
Agent Execution Engine Module

Smart agent engine based on LangChain DeepAgents SDK, supports:
- Loading Agent config from agent_spec.yaml
- Loading skills, prompts, models directory configs
- Multiple system prompt concatenation
- FilesystemBackend filesystem backend

Main modules:
- deepagents_engine: DeepAgents SDK 集成的核心引擎
- agent_loader: Agent 配置Load和Parse

依赖Notes:
- agent_loader: 仅需要 pyyaml, 可独立使用
- deepagents_engine: 需要 langchain-core, langchain-openai, deepagents
"""

# Agent configuration loader (无 langchain 依赖)
from .agent_loader import (
    AgentConfig,
    AgentConfigLoader,
    ModelInfo,
    PromptInfo,
    SkillInfo,
    get_agent_config_loader,
    load_agent_config,
)

# DeepAgents 引擎 (有依赖, 延迟Import)
from .deepagents_engine import (
    DeepAgentsEngine,
    AgentBuildContext,
    get_deepagents_engine,
    check_dependencies,
)

__all__ = [
    # ConfigLoad器 (无依赖)
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
