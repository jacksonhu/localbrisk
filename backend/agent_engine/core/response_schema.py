"""
Markdown output protocol (replaces structured JSON response format)

Notes:
- Agent final output is unified as Markdown text.
- This module retains minimal type definitions, avoiding JSON block schema dependency.
"""

from pydantic import BaseModel, Field


class MarkdownResponse(BaseModel):
    """Markdown text response"""

    markdown: str = Field(..., description="Complete Markdown content")


__all__ = [
    "MarkdownResponse",
]
