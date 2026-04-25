"""Agent execution engine exports.

Primary runtime:
- ``openai_agents_engine``: OpenAI Agents SDK runtime assembly and session wrapper.

Supporting modules:
- ``agent_context_loader``: normalized runtime definition loader shared by the runtime stack.
"""

from .agent_context_loader import AgentBuildContext, AssetBundleBackendConfig, SkillConfig
from .openai_agents_engine import (
    OpenAIAgentRuntime,
    OpenAIAgentsEngine,
    check_openai_agents_dependencies,
    get_openai_agents_engine,
)

__all__ = [
    "AgentBuildContext",
    "AssetBundleBackendConfig",
    "SkillConfig",
    "OpenAIAgentRuntime",
    "OpenAIAgentsEngine",
    "get_openai_agents_engine",
    "check_openai_agents_dependencies",
]
