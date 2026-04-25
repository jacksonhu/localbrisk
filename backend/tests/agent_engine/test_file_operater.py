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


def _make_bundle_with_volume(tmp_path: Path, bundle_name: str = "test_bundle", volume_name: str = "my_files"):
    """创建一个包含文件的 bundle 和 volume 目录结构用于测试。"""
    bundle_dir = tmp_path / "asset_bundles" / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    vol_dir = tmp_path / "volumes" / volume_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    (vol_dir / "data.txt").write_text("hello world\nline 2\nline 3\n", encoding="utf-8")
    (vol_dir / "config.yaml").write_text("name: test\nmode: fast\n", encoding="utf-8")

    bundle_config = {
        "bundle_name": bundle_name,
        "bundle_type": "local",
        "bundle_path": str(bundle_dir),
        "mount_path": f"/{bundle_name}",
        "volumes": [
            {
                "name": volume_name,
                "volume_type": "local",
                "file_path": str(tmp_path / f"{volume_name}.yaml"),
                "storage_location": str(vol_dir),
            }
        ],
    }
    return bundle_config, bundle_dir, vol_dir


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


class TestFileReadBundlePath:
    """FileReadTool @ 前缀路径功能测试。"""

    def test_read_file_via_bundle_volume_path(self, tmp_path: Path):
        """使用 @bundle_name/volume_name/file.txt 路径读取文件。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_read_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/data.txt")

        assert "**File**: `data.txt`" in result
        assert "hello world" in result
        assert "line 2" in result

    def test_read_file_via_bundle_volume_path_with_range(self, tmp_path: Path):
        """使用 @ 前缀路径读取文件的指定行范围。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_read_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/data.txt", start_line=2, end_line=2)

        assert "**Selected lines**: 2-2 / 3" in result
        assert "line 2" in result
        assert "hello world" not in result

    def test_read_nonexistent_bundle_returns_error(self, tmp_path: Path):
        """@ 前缀路径中 bundle 不存在时返回错误信息。"""
        bundle_config, _, _ = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_read_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@nonexistent/my_files/data.txt")

        assert "❌" in result
        assert "not found" in result.lower()

    def test_read_nonexistent_file_in_bundle_returns_error(self, tmp_path: Path):
        """@ 前缀路径中文件不存在时返回错误信息。"""
        bundle_config, _, _ = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_read_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/nonexistent.txt")

        assert "❌" in result
        assert "not found" in result.lower()

    def test_read_without_bundles_preserves_behavior(self, tmp_path: Path):
        """无 asset_bundles 时保持原有行为。"""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "readme.md").write_text("# Hello", encoding="utf-8")

        tool = create_file_read_tool(base_path=str(agent_dir))
        result = tool._run("readme.md")

        assert "**File**: `readme.md`" in result
        assert "# Hello" in result


class TestFileWriteBundlePath:
    """FileWriteTool @ 前缀路径功能测试。"""

    def test_write_file_via_bundle_volume_path(self, tmp_path: Path):
        """使用 @bundle_name/volume_name/file.txt 路径写入文件。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_write_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/data.txt", "new content")

        assert "Overwrote file" in result
        assert (vol_dir / "data.txt").read_text(encoding="utf-8") == "new content"

    def test_write_file_range_via_bundle_path(self, tmp_path: Path):
        """使用 @ 前缀路径进行行范围替换。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_write_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/data.txt", "replaced line 2", start_line=2, end_line=2)

        assert "Updated file" in result
        content = (vol_dir / "data.txt").read_text(encoding="utf-8")
        assert "replaced line 2" in content
        assert "hello world" in content
        assert "line 3" in content

    def test_create_new_file_via_bundle_path(self, tmp_path: Path):
        """使用 @ 前缀路径创建新文件。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_write_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@test_bundle/my_files/new_file.txt", "brand new content")

        assert "Created file" in result
        assert (vol_dir / "new_file.txt").read_text(encoding="utf-8") == "brand new content"

    def test_write_nonexistent_bundle_returns_error(self, tmp_path: Path):
        """@ 前缀路径中 bundle 不存在时返回错误信息。"""
        bundle_config, _, _ = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_write_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("@nonexistent/my_files/data.txt", "content")

        assert "❌" in result
        assert "not found" in result.lower()

    def test_build_builtin_tools_passes_asset_bundles_to_file_tools(self, tmp_path: Path):
        """验证 build_builtin_tools 传递 asset_bundles 后 file_read/file_write 能正确解析 @ 路径。"""
        bundle_config, _, vol_dir = _make_bundle_with_volume(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tools = build_builtin_tools(
            agent_path=str(agent_dir),
            task_root=str(tmp_path / ".task"),
            asset_bundles=[bundle_config],
        )
        file_read_tool = next(t for t in tools if t.name == "file_read")
        result = file_read_tool._run("@test_bundle/my_files/data.txt")

        assert "hello world" in result

        file_write_tool = next(t for t in tools if t.name == "file_write")
        result = file_write_tool._run("@test_bundle/my_files/output.txt", "written via bundle path")

        assert "Created file" in result
        assert (vol_dir / "output.txt").read_text(encoding="utf-8") == "written via bundle path"
