"""Keyword-based local file search tool resolved from one base directory."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class FileSearchInput(BaseModel):
    keyword: str = Field(description="Keyword used to match file names (case-insensitive)")
    search_path: str = Field(
        default=".",
        description="Directory to search, relative to the configured base directory or an absolute path",
    )
    max_results: int = Field(default=50, description="Maximum number of results to return, range: 1-200")


class FileSearchTool(BaseTool):
    name: str = "file_search"
    description: str = (
        "Search file names by keyword in the local filesystem. "
        "Relative paths are resolved from the configured base directory."
    )
    args_schema: Type[BaseModel] = FileSearchInput

    _base_path: Optional[str] = None
    _IGNORED_DIR_NAMES: tuple[str, ...] = (
        ".git",
        ".hg",
        ".svn",
        ".task",
        ".checkpoints",
        ".conversation_history",
        ".large_tool_results",
        "__pycache__",
        "venv",
        "node_modules",
    )

    def _run(self, keyword: str, search_path: str = ".", max_results: int = 50) -> str:
        return self._search(keyword=keyword, search_path=search_path, max_results=max_results)

    async def _arun(self, keyword: str, search_path: str = ".", max_results: int = 50) -> str:
        return await asyncio.to_thread(self._search, keyword, search_path, max_results)

    def _search(self, keyword: str, search_path: str, max_results: int) -> str:
        needle = (keyword or "").strip().lower()
        if not needle:
            return "❌ keyword cannot be empty"

        max_results = max(1, min(int(max_results), 200))
        root = self._resolve_search_path(search_path)
        if not root.exists():
            return f"❌ search path not found: {search_path}"
        if not root.is_dir():
            return f"❌ search path is not a directory: {search_path}"

        matched: list[str] = []
        for current_root, dir_names, file_names in os.walk(root):
            dir_names[:] = sorted(name for name in dir_names if not self._should_skip_dir(name))
            for file_name in sorted(file_names):
                if needle not in file_name.lower():
                    continue
                matched.append(self._display_path(Path(current_root) / file_name))
                if len(matched) >= max_results:
                    break
            if len(matched) >= max_results:
                break

        if not matched:
            return (
                f"No files containing keyword `{keyword}` were found "
                f"(search path: `{self._display_path(root)}`)."
            )

        lines = [
            f"Found {len(matched)} matching files "
            f"(keyword: `{keyword}`, search path: `{self._display_path(root)}`):"
        ]
        for idx, path in enumerate(matched, start=1):
            lines.append(f"{idx}. `{path}`")
        return "\n".join(lines)

    def _resolve_search_path(self, search_path: str) -> Path:
        raw = (search_path or ".").strip() or "."
        candidate = Path(os.path.expanduser(raw))
        if candidate.is_absolute():
            return candidate.resolve()

        base_dir = self._get_base_dir()
        return (base_dir / candidate).resolve()

    def _get_base_dir(self) -> Path:
        if self._base_path:
            return Path(os.path.expanduser(self._base_path)).resolve()
        return Path.cwd().resolve()

    def _display_path(self, path: Path) -> str:
        resolved_path = path.resolve()
        base_dir = self._get_base_dir()
        try:
            relative = resolved_path.relative_to(base_dir)
            return "." if str(relative) == "." else f"./{relative.as_posix()}"
        except ValueError:
            return str(resolved_path)

    def _should_skip_dir(self, dir_name: str) -> bool:
        return dir_name.startswith(".") or dir_name in self._IGNORED_DIR_NAMES


def create_file_search_tool(base_path: Optional[str] = None) -> FileSearchTool:
    tool = FileSearchTool()
    tool._base_path = base_path
    return tool
