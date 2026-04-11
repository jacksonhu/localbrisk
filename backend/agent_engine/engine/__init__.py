"""Agent execution engine exports.

Primary runtime:
- ``openai_agents_engine``: OpenAI Agents SDK runtime assembly and session-aware wrapper.

Supporting modules:
- ``agent_loader``: filesystem-backed agent config inspection helpers.
- ``agent_context_loader``: normalized runtime definition loader shared by engines.

Legacy modules remain available only for staged cleanup and test migration.
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

# DeepAgents runtime (legacy path)
from .deepagents_engine import (
    DeepAgentsEngine,
    AgentBuildContext,
    check_dependencies,
    get_deepagents_engine,
)

# OpenAI Agents runtime (new path)
from .openai_agents_engine import (
    OpenAIAgentRuntime,
    OpenAIAgentsEngine,
    check_openai_agents_dependencies,
    get_openai_agents_engine,
)

__all__ = [
    # Config loader (no runtime dependency)
    "AgentConfig",
    "AgentConfigLoader",
    "ModelInfo",
    "PromptInfo",
    "SkillInfo",
    "get_agent_config_loader",
    "load_agent_config",
    # Shared context
    "AgentBuildContext",
    # DeepAgents runtime
    "DeepAgentsEngine",
    "get_deepagents_engine",
    "check_dependencies",
    # OpenAI Agents runtime
    "OpenAIAgentRuntime",
    "OpenAIAgentsEngine",
    "get_openai_agents_engine",
    "check_openai_agents_dependencies",
]
