"""Tests for the local file search tool."""

from __future__ import annotations

from pathlib import Path

from agent_engine.tools import build_builtin_tools, create_file_search_tool


class TestFileSearchTool:
    def test_file_search_matches_filenames_under_base_path(self, tmp_path: Path):
        agent_dir = tmp_path / "agent"
        docs_dir = agent_dir / "docs"
        nested_dir = docs_dir / "nested"
        nested_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "api-guide.md").write_text("guide", encoding="utf-8")
        (nested_dir / "guide-notes.txt").write_text("notes", encoding="utf-8")
        (nested_dir / "overview.md").write_text("overview", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir))
        result = tool._run("guide", search_path="docs")

        assert tool.name == "file_search"
        assert "Found 2 matching files" in result
        assert "`./docs/api-guide.md`" in result
        assert "`./docs/nested/guide-notes.txt`" in result
        assert "overview.md" not in result

    def test_build_builtin_tools_includes_file_search(self, tmp_path: Path):
        tools = build_builtin_tools(agent_path=str(tmp_path / "agent"), task_root=str(tmp_path / ".task"))
        tool_names = [tool.name for tool in tools]

        assert "file_search" in tool_names
        assert "local_file_keyword_search" not in tool_names
