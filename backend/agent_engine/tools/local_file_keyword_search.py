"""Keyword-based local file search tool (backed by virtual filesystem backend)."""

from __future__ import annotations

import asyncio
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class LocalFileKeywordSearchInput(BaseModel):
    keyword: str = Field(description="Keyword used to match file names (case-insensitive)")
    search_path: str = Field(default="/", description="Search start path (virtual path)")
    max_results: int = Field(default=50, description="Maximum number of results to return, range: 1-200")


class LocalFileKeywordSearchTool(BaseTool):
    name: str = "local_file_keyword_search"
    description: str = (
        "Search file names by keyword in the virtual filesystem. "
        "Recursively traverses subdirectories via backend.ls_info() and returns virtual paths."
    )
    args_schema: Type[BaseModel] = LocalFileKeywordSearchInput

    _backend: Any = None
    _IGNORED_PREFIXES: tuple[str, ...] = (
        "/.nofollow",
        "/.resolve",
        "/.vol",
        "/Applications",
        "/Library",
        "/System",
        "/Users",
        "/Volumes",
        "/bin",
        "/cores",
        "/dev",
        "/etc",
        "/home",
        "/large_tool_results",
        "/memories",
        "/opt",
        "/private",
        "/sbin",
        "/skills",
        "/tmp",
        "/usr",
        "/var",
        "/output/.chathistory",
        "/output/.checkpoints",
        "/output/.task",
        "/output/venv",
    )

    def _run(self, keyword: str, search_path: str = "/", max_results: int = 50) -> str:
        return self._search(keyword=keyword, search_path=search_path, max_results=max_results)

    async def _arun(self, keyword: str, search_path: str = "/", max_results: int = 50) -> str:
        return await asyncio.to_thread(self._search, keyword, search_path, max_results)

    @staticmethod
    def _normalize_path(path: str) -> str:
        path = (path or "/").strip()
        if not path.startswith("/"):
            path = f"/{path}"
        if path != "/":
            path = path.rstrip("/")
        return path or "/"

    @staticmethod
    def _unwrap_ls_info_result(result: Any) -> list[Any]:
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("items", "entries", "children", "data", "files"):
                value = result.get(key)
                if isinstance(value, list):
                    return value
        return []

    @staticmethod
    def _entry_is_dir(entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        if isinstance(entry.get("is_dir"), bool):
            return entry["is_dir"]
        if isinstance(entry.get("isDir"), bool):
            return entry["isDir"]
        if isinstance(entry.get("is_directory"), bool):
            return entry["is_directory"]
        et = str(entry.get("type", "")).lower()
        return et in {"dir", "directory", "folder"}

    def _is_ignored_path(self, path: str) -> bool:
        normalized = self._normalize_path(path)
        for prefix in self._IGNORED_PREFIXES:
            if normalized == prefix or normalized.startswith(f"{prefix}/"):
                return True
        return False

    def _search(self, keyword: str, search_path: str, max_results: int) -> str:
        keyword = (keyword or "").strip()
        if not keyword:
            return "❌ keyword cannot be empty"

        if self._backend is None:
            return "❌ backend is not injected; virtual filesystem search is unavailable"

        max_results = max(1, min(int(max_results), 200))
        root = self._normalize_path(search_path)
        needle = keyword.lower()

        matched: list[str] = []
        stack: list[str] = [root]
        visited: set[str] = set()

        while stack and len(matched) < max_results:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if self._is_ignored_path(current):
                continue

            try:
                entries = self._unwrap_ls_info_result(self._backend.ls_info(current))
            except Exception as e:
                return f"❌ directory traversal failed: {current}\nerror: {e}"

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                child_path = entry.get("path")
                if not child_path:
                    continue

                child_path = self._normalize_path(child_path)
                if self._is_ignored_path(child_path):
                    continue

                is_dir = self._entry_is_dir(entry)
                if is_dir:
                    stack.append(child_path)
                    continue

                if needle in child_path.lower():
                    matched.append(child_path)
                    if len(matched) >= max_results:
                        break

        if not matched:
            return f"No files containing keyword `{keyword}` were found (path: {root})"

        lines = [f"Found {len(matched)} matching files (keyword: `{keyword}`, search path: `{root}`):"]
        for idx, path in enumerate(matched, start=1):
            lines.append(f"{idx}. `{path}`")
        return "\n".join(lines)


def create_local_file_keyword_search_tool() -> LocalFileKeywordSearchTool:
    return LocalFileKeywordSearchTool()
