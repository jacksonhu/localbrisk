"""Helpers for turning configured native skills into OpenAI Agents SDK tools."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence

from .agent_context_loader import SkillConfig

logger = logging.getLogger(__name__)


@dataclass
class OpenAINativeSkillCollection:
    """Built native skill agents and the SDK tools exposed from them."""

    agents: List[Any] = field(default_factory=list)
    tools: List[Any] = field(default_factory=list)


def build_openai_native_skills(
    *,
    agent_cls: Any,
    parent_model: Any,
    parent_model_settings: Any = None,
    parent_tools: Optional[Sequence[Any]] = None,
    skills: Optional[Sequence[SkillConfig]] = None,
) -> OpenAINativeSkillCollection:
    """Build one skill-agent collection and expose each skill via ``Agent.as_tool()``."""
    collection = OpenAINativeSkillCollection()
    if not skills:
        return collection

    shared_tools = list(parent_tools or [])
    for skill in skills:
        skill_agent = _build_skill_agent(
            agent_cls=agent_cls,
            parent_model=parent_model,
            parent_model_settings=parent_model_settings,
            parent_tools=shared_tools,
            skill=skill,
        )
        as_tool = getattr(skill_agent, "as_tool", None)
        if not callable(as_tool):
            raise TypeError(f"Skill agent '{skill.display_name}' does not support as_tool()")

        skill_tool = as_tool(
            tool_name=skill.tool_name,
            tool_description=skill.description,
        )
        collection.agents.append(skill_agent)
        collection.tools.append(skill_tool)
        logger.info("Built native skill tool: skill=%s tool_name=%s", skill.name, skill.tool_name)

    return collection


def _build_skill_agent(
    *,
    agent_cls: Any,
    parent_model: Any,
    parent_model_settings: Any,
    parent_tools: Sequence[Any],
    skill: SkillConfig,
) -> Any:
    """Create one SDK agent that represents a configured native skill."""
    agent_kwargs = {
        "name": skill.display_name,
        "instructions": _build_skill_instructions(skill),
        "model": parent_model,
    }
    if parent_model_settings is not None:
        agent_kwargs["model_settings"] = parent_model_settings
    if parent_tools:
        agent_kwargs["tools"] = list(parent_tools)
    return agent_cls(**agent_kwargs)


def _build_skill_instructions(skill: SkillConfig) -> str:
    """Build the final instructions string for one skill agent."""
    parts = [
        f"You are the native skill agent '{skill.display_name}'.",
        "You are invoked as a tool by another agent.",
        "Solve only the delegated task and return a concise, directly usable result.",
        skill.instructions,
    ]
    return "\n\n".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


__all__ = [
    "OpenAINativeSkillCollection",
    "build_openai_native_skills",
]
