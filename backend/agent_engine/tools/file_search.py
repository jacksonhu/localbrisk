"""Keyword-based local file search tool.

When ``search_path`` is the default value ``'.'`` **and** asset bundles are
configured, the tool scans **both** the agent working directory and every
local asset bundle root – giving the agent comprehensive visibility without
requiring an explicit ``@`` prefix.

When the user specifies a concrete relative/absolute path or uses the ``@``
prefix to target a specific bundle, only that single directory tree is searched.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Sequence, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from .bundle_path_resolver import BundlePathResolver

logger = logging.getLogger(__name__)

_BASE_SEARCH_PATH_DESC = (
    "Directory to search, relative to the configured base directory or an absolute path"
)
_BUNDLE_SEARCH_PATH_DESC = (
    "Directory to search. Defaults to '.' which scans the agent directory "
    "AND all asset bundle directories. Use '@bundle_name' to search a specific "
    "asset bundle directory, '@bundle_name/volume_name' to search a volume's "
    "storage location, or a relative/absolute path for the agent directory only."
)


class FileSearchInput(BaseModel):
    keyword: str = Field(description="Keyword used to match file names (case-insensitive)")
    search_path: str = Field(
        default=".",
        description=_BASE_SEARCH_PATH_DESC,
    )
    max_results: int = Field(default=50, description="Maximum number of results to return, range: 1-200")


class _BundleFileSearchInput(BaseModel):
    """Input schema used when asset bundles are present."""

    keyword: str = Field(description="Keyword used to match file names (case-insensitive)")
    search_path: str = Field(
        default=".",
        description=_BUNDLE_SEARCH_PATH_DESC,
    )
    max_results: int = Field(default=50, description="Maximum number of results to return, range: 1-200")


_BASE_DESCRIPTION = (
    "Search file names by keyword in the local filesystem. "
    "Relative paths are resolved from the configured base directory."
)


class FileSearchTool(BaseTool):
    name: str = "file_search"
    description: str = _BASE_DESCRIPTION
    args_schema: Type[BaseModel] = FileSearchInput

    _base_path: Optional[str] = None
    _bundle_resolver: Optional[BundlePathResolver] = None
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

    # ──────────────────── core search logic ────────────────────

    def _search(self, keyword: str, search_path: str, max_results: int) -> str:
        needle = (keyword or "").strip().lower()
        if not needle:
            return "❌ keyword cannot be empty"

        max_results = max(1, min(int(max_results), 200))
        normalized = (search_path or ".").strip() or "."

        # Route: explicit @bundle path → single bundle search.
        if self._bundle_resolver is not None and self._bundle_resolver.is_bundle_path(normalized):
            return self._search_single_bundle(needle, normalized, max_results)

        # Route: default path '.' with bundles → multi-root search (agent dir + all bundles).
        if normalized == "." and self._bundle_resolver is not None and self._bundle_resolver.has_bundles:
            return self._search_multi_root(needle, max_results)

        # Route: explicit relative/absolute path → single directory search.
        return self._search_single_dir(needle, normalized, max_results)

    # ─────────────── single directory search (original) ───────────────

    def _search_single_dir(self, needle: str, search_path: str, max_results: int) -> str:
        """Search a single directory tree (relative or absolute)."""
        root = self._resolve_search_path(search_path)
        display_root = self._display_path(root)

        if not root.exists():
            return f"❌ search path not found: {search_path}"
        if not root.is_dir():
            return f"❌ search path is not a directory: {search_path}"

        matched = self._walk_dir(needle, root, max_results, display_fn=self._display_path)
        return self._format_results(needle, matched, display_root)

    # ─────────────── single bundle search (@ prefix) ───────────────

    def _search_single_bundle(self, needle: str, raw_path: str, max_results: int) -> str:
        """Search within one resolved bundle directory."""
        resolved = self._bundle_resolver.resolve(raw_path)  # type: ignore[union-attr]
        if not resolved.success:
            return f"❌ {resolved.error_message}"
        root = resolved.physical_path
        display_root = resolved.display_prefix

        if not root.exists():
            return f"❌ search path not found: {raw_path}"
        if not root.is_dir():
            return f"❌ search path is not a directory: {raw_path}"

        matched = self._walk_dir(
            needle, root, max_results,
            display_fn=lambda p: self._display_bundle_path(p, root, display_root),
        )
        return self._format_results(needle, matched, display_root, resolved_hint=str(root))

    # ─────────────── multi-root search (agent + all bundles) ───────────────

    def _search_multi_root(self, needle: str, max_results: int) -> str:
        """Search the agent working directory and every local bundle/volume root."""
        agent_root = self._get_base_dir()
        matched: List[str] = []
        # Track unique bundle names for the summary line (avoid verbose repetition).
        seen_bundle_names: List[str] = []
        seen_bundle_set: set[str] = set()

        # 1. Search agent directory first.
        if agent_root.is_dir():
            matched.extend(self._walk_dir(needle, agent_root, max_results, display_fn=self._display_path))

        # 2. Search each bundle / volume root (skip if quota already filled).
        for display_name, root_path in self._bundle_resolver.get_all_local_roots():  # type: ignore[union-attr]
            if len(matched) >= max_results:
                break
            remaining = max_results - len(matched)
            display_prefix = f"@{display_name}"
            # Only record the top-level bundle name in the summary.
            top_bundle = display_name.split("/", 1)[0]
            if top_bundle not in seen_bundle_set:
                seen_bundle_set.add(top_bundle)
                seen_bundle_names.append(f"@{top_bundle}")
            bundle_hits = self._walk_dir(
                needle, root_path, remaining,
                display_fn=lambda p, _r=root_path, _d=display_prefix: self._display_bundle_path(p, _r, _d),
            )
            matched.extend(bundle_hits)

        display_root = " + ".join(["."] + seen_bundle_names)
        return self._format_results(needle, matched, display_root)

    # ─────────────── walk & format helpers ───────────────

    def _walk_dir(
        self,
        needle: str,
        root: Path,
        max_results: int,
        *,
        display_fn: Any,
    ) -> List[str]:
        """Walk a directory tree and collect matching display paths."""
        matched: List[str] = []
        for current_root, dir_names, file_names in os.walk(root):
            dir_names[:] = sorted(name for name in dir_names if not self._should_skip_dir(name))
            for file_name in sorted(file_names):
                if needle not in file_name.lower():
                    continue
                file_path = Path(current_root) / file_name
                matched.append(display_fn(file_path))
                if len(matched) >= max_results:
                    return matched
        return matched

    @staticmethod
    def _format_results(
        keyword: str,
        matched: List[str],
        display_root: str,
        resolved_hint: Optional[str] = None,
    ) -> str:
        """Build the final human-readable result string."""
        if not matched:
            return (
                f"No files containing keyword `{keyword}` were found "
                f"(search path: `{display_root}`)."
            )

        summary = f"Found {len(matched)} matching files (keyword: `{keyword}`, search path: `{display_root}`)"
        if resolved_hint:
            summary += f" [resolved: `{resolved_hint}`]"
        summary += ":"
        lines = [summary]
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

    @staticmethod
    def _display_bundle_path(file_path: Path, search_root: Path, display_prefix: str) -> str:
        """将 bundle 搜索结果中的文件路径以 @ 前缀格式展示。"""
        resolved = file_path.resolve()
        try:
            relative = resolved.relative_to(search_root)
            rel_str = relative.as_posix()
            if rel_str == ".":
                return display_prefix
            return f"{display_prefix}/{rel_str}"
        except ValueError:
            return str(resolved)

    def _should_skip_dir(self, dir_name: str) -> bool:
        return dir_name.startswith(".") or dir_name in self._IGNORED_DIR_NAMES


def create_file_search_tool(
    base_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
) -> FileSearchTool:
    """Create a file_search tool with optional asset bundle support."""
    resolver = BundlePathResolver(asset_bundles) if asset_bundles else None
    has_bundles = resolver is not None and resolver.has_bundles

    # 动态构建 description
    desc = _BASE_DESCRIPTION
    if has_bundles:
        desc += resolver.available_bundles_description()  # type: ignore[union-attr]

    # 选择合适的 args_schema
    schema = _BundleFileSearchInput if has_bundles else FileSearchInput

    tool = FileSearchTool(description=desc, args_schema=schema)
    tool._base_path = base_path
    tool._bundle_resolver = resolver
    return tool
