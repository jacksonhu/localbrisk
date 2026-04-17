"""Tests for the unified local file read/write tools."""

from __future__ import annotations

from pathlib import Path

from agent_engine.tools import (
    FileReadTool,
    FileWriteTool,
    build_builtin_tools,
    create_file_read_tool,
    create_file_write_tool,
)


class TestFileOperaterTools:
    def test_file_read_supports_text_range(self, tmp_path: Path):
        agent_dir = tmp_path / "agent"
        docs_dir = agent_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        target_file = docs_dir / "config.yaml"
        target_file.write_text("name: demo\nmode: fast\nretries: 3\nenabled: true\n", encoding="utf-8")

        tool = create_file_read_tool(base_path=str(agent_dir))
        result = tool._run("docs/config.yaml", start_line=2, end_line=3)

        assert "**File**: `config.yaml`" in result
        assert "**Selected lines**: 2-3 / 4" in result
        assert "mode: fast" in result
        assert "retries: 3" in result
        assert "name: demo" not in result
        assert "enabled: true" not in result

    def test_file_write_replaces_text_range(self, tmp_path: Path):
        agent_dir = tmp_path / "agent"
        target_file = agent_dir / "notes.md"
        agent_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text("line-1\nline-2\nline-3\nline-4\n", encoding="utf-8")

        tool = create_file_write_tool(base_path=str(agent_dir))
        result = tool._run("notes.md", "updated-2\nupdated-3", start_line=2, end_line=3)

        assert "Updated file" in result
        assert "Replaced lines: 2-3" in result
        assert target_file.read_text(encoding="utf-8") == "line-1\nupdated-2\nupdated-3\nline-4\n"

    def test_build_builtin_tools_includes_file_read_and_write(self, tmp_path: Path):
        tools = build_builtin_tools(agent_path=str(tmp_path / "agent"), task_root=str(tmp_path / ".task"))
        tool_names = [tool.name for tool in tools]

        assert "file_read" in tool_names
        assert "file_write" in tool_names

    def test_file_tools_expose_path_argument_only(self):
        read_schema = create_file_read_tool().args_schema.model_json_schema()
        write_schema = create_file_write_tool().args_schema.model_json_schema()

        assert "path" in read_schema["properties"]
        assert "file_path" not in read_schema["properties"]
        assert "path" in write_schema["properties"]
        assert "file_path" not in write_schema["properties"]
