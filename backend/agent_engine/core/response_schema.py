"""
Markdown 输出协议（替代结构化 JSON response format）

说明：
- Agent 最终输出统一为 Markdown 文本。
- 本模块仅保留最小类型定义，避免继续依赖 JSON block schema。
"""

from pydantic import BaseModel, Field


class MarkdownResponse(BaseModel):
    """Markdown 文本响应"""

    markdown: str = Field(..., description="完整 Markdown 内容")


__all__ = [
    "MarkdownResponse",
]
