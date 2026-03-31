"""内置子 Agent 定义 (统一在父沙箱环境下Execute)."""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


_WEB_CRAWL_SYSTEM_PROMPT = """你是网页抓取与内容总结子助手.
职责:
1) 根据用户意图抓取网页或检索资料；
2) 提炼关键信息并输出结构化总结；
3) 如需产出文件, 写入 /output.
要求:
- 优先复用当前可用工具；
- 不要编造网页内容；
- 当信息不足时明确说明缺口与下一步建议."""

_TEXT2SQL_SYSTEM_PROMPT = """你是 Text2SQL 取数子助手.
职责:
1) 将自然语言需求转为可Execute SQL；
2) Execute查询并返回结果摘要；
3) 需要时输出可复用的 SQL 与字段说明.
要求:
- 优先使用参数化查询, 不拼接不可信输入；
- Table name/字段名/排序字段必须做白名单校验；
- 不Execute破坏性 SQL (DROP/TRUNCATE/DELETE 无审批)."""



def _as_dict_subagent(
    *,
    name: str,
    description: str,
    system_prompt: str,
    tools: Optional[List[Any]] = None,
    model: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build 字典式 SubAgent 定义 (推荐方式)."""
    payload: Dict[str, Any] = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
    }
    if tools is not None:
        payload["tools"] = tools
    if model is not None:
        payload["model"] = model
    return payload


def _as_compiled_subagent_or_fallback(
    *,
    name: str,
    description: str,
    system_prompt: str,
    model: Any,
    tools: List[Any],
    backend: Any,
) -> Any:
    """优先Create CompiledSubAgent, failed则Fall back为字典定义."""
    try:
        from langchain.agents import create_agent
        from deepagents.middleware.subagents import CompiledSubAgent  # type: ignore

        create_kwargs: Dict[str, Any] = {
            "model": model,
            "tools": tools,
            "system_prompt": system_prompt,
            "name": name,
        }

        # 不同 deepagents 版本 create_agent 入参可能不同, 按签名动态注入 backend
        signature = inspect.signature(create_agent)
        if "backend" in signature.parameters:
            create_kwargs["backend"] = backend

        runnable = create_agent(**create_kwargs)
        return CompiledSubAgent(name=name, description=description, runnable=runnable)
    except Exception as e:
        logger.warning("CompiledSubAgent 不可用, Fall back字典定义: %s", e)
        return _as_dict_subagent(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            model=model,
        )


def create_builtin_subagents(
    *,
    parent_model: Any,
    parent_tools: List[Any],
    parent_backend: Any,
) -> List[Any]:
    """Create 内置 3 个子 Agent.

    设计要点:
    - `web_crawl_summary_agent`、`text2sql_agent` 使用字典定义 (最简、自动中间件)；
    - `ppt_summary_agent` 优先使用 CompiledSubAgent (可细粒度控制), 不可用时自动Fall back字典；
    - 三者均复用父级模型/工具/沙箱后端, 保证在同一运行环境中Execute.
    """
    subagents: List[Any] = [
        _as_dict_subagent(
            name="web_crawl_summary_agent",
            description="网页抓取与内容总结",
            system_prompt=_WEB_CRAWL_SYSTEM_PROMPT,
            tools=parent_tools,
            model=parent_model,
        ),
        _as_dict_subagent(
            name="text2sql_agent",
            description="Text2SQL 取数与结果解释",
            system_prompt=_TEXT2SQL_SYSTEM_PROMPT,
            tools=parent_tools,
            model=parent_model,
        ),
    ]

    logger.info("内置 subagents 已生成: %s", [
        sa.get("name") if isinstance(sa, dict) else getattr(sa, "name", "unknown")
        for sa in subagents
    ])
    return subagents


__all__ = ["create_builtin_subagents"]
