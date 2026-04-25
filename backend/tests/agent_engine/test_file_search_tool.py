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


def _make_bundle_with_files(tmp_path: Path, bundle_name: str = "test_bundle", volume_name: str = "my_files"):
    """创建一个包含文件的 bundle 和 volume 目录结构用于集成测试。"""
    # 创建 bundle 目录和文件
    bundle_dir = tmp_path / "asset_bundles" / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "bundle.yaml").write_text("bundle_type: local", encoding="utf-8")
    tables_dir = bundle_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    (tables_dir / "users.yaml").write_text("name: users", encoding="utf-8")
    (tables_dir / "orders.yaml").write_text("name: orders", encoding="utf-8")

    # 创建 volume 目录和文件
    vol_dir = tmp_path / "volumes" / volume_name
    vol_dir.mkdir(parents=True, exist_ok=True)
    (vol_dir / "report_2024.csv").write_text("data", encoding="utf-8")
    (vol_dir / "report_2025.csv").write_text("data", encoding="utf-8")
    (vol_dir / "summary.txt").write_text("summary", encoding="utf-8")
    sub_dir = vol_dir / "archive"
    sub_dir.mkdir(parents=True, exist_ok=True)
    (sub_dir / "old_report.csv").write_text("old", encoding="utf-8")

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


class TestFileSearchBundleIntegration:
    """FileSearchTool @ prefix and multi-root integration tests."""

    def test_search_bundle_directory(self, tmp_path: Path):
        """Explicit @bundle_name searches the bundle directory only."""
        bundle_config, bundle_dir, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("yaml", search_path="@test_bundle")

        assert "Found" in result
        assert "@test_bundle" in result
        assert "bundle.yaml" in result
        assert "users.yaml" in result
        assert "orders.yaml" in result

    def test_search_volume_directory(self, tmp_path: Path):
        """@bundle_name/volume_name searches the volume storage location."""
        bundle_config, _, vol_dir = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("report", search_path="@test_bundle/my_files")

        assert "Found 3 matching files" in result
        assert "@test_bundle/my_files" in result
        assert "report_2024.csv" in result
        assert "report_2025.csv" in result
        assert "old_report.csv" in result
        assert "summary.txt" not in result

    def test_search_volume_subdirectory(self, tmp_path: Path):
        """@bundle_name/volume_name/sub searches a subdirectory within the volume."""
        bundle_config, _, vol_dir = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("report", search_path="@test_bundle/my_files/archive")

        assert "Found 1 matching files" in result
        assert "old_report.csv" in result

    def test_search_results_display_at_prefix_paths(self, tmp_path: Path):
        """Bundle search results use @bundle_name/... display format."""
        bundle_config, _, vol_dir = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("report", search_path="@test_bundle/my_files")

        assert "`@test_bundle/my_files/archive/old_report.csv`" in result
        assert "`@test_bundle/my_files/report_2024.csv`" in result

    def test_search_results_show_resolved_path(self, tmp_path: Path):
        """Bundle search summary line includes the physical resolved path."""
        bundle_config, _, vol_dir = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("report", search_path="@test_bundle/my_files")

        assert "[resolved:" in result
        assert str(vol_dir.resolve()) in result

    def test_no_bundles_preserves_original_behavior(self, tmp_path: Path):
        """Without bundles, the tool works exactly like before."""
        agent_dir = tmp_path / "agent"
        docs_dir = agent_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "readme.md").write_text("hello", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir))
        result = tool._run("readme")

        assert "Found 1 matching files" in result
        assert "`./docs/readme.md`" in result

    def test_description_changes_with_bundles(self, tmp_path: Path):
        """Tool description adapts when asset_bundles are provided."""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool_no_bundle = create_file_search_tool(base_path=str(agent_dir))
        assert "@" not in tool_no_bundle.description

        bundle_config, _, _ = _make_bundle_with_files(tmp_path)
        tool_with_bundle = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        assert "@test_bundle" in tool_with_bundle.description
        assert "local" in tool_with_bundle.description

    def test_nonexistent_bundle_returns_error(self, tmp_path: Path):
        """Searching a non-existent bundle returns a clear error."""
        bundle_config, _, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("file", search_path="@nonexistent")

        assert "❌" in result
        assert "not found" in result.lower()
        assert "`test_bundle`" in result

    def test_build_builtin_tools_passes_asset_bundles(self, tmp_path: Path):
        """build_builtin_tools wires up asset_bundles so @ paths resolve correctly."""
        bundle_config, bundle_dir, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tools = build_builtin_tools(
            agent_path=str(agent_dir),
            task_root=str(tmp_path / ".task"),
            asset_bundles=[bundle_config],
        )
        file_search_tool = next(t for t in tools if t.name == "file_search")
        result = file_search_tool._run("yaml", search_path="@test_bundle")

        assert "Found" in result
        assert "@test_bundle" in result

    def test_fallback_to_bundle_subdir_when_no_volume_match(self, tmp_path: Path):
        """When no volume matches, falls back to a subdirectory under bundle_path."""
        bundle_config, bundle_dir, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("yaml", search_path="@test_bundle/tables")

        assert "Found 2 matching files" in result
        assert "users.yaml" in result
        assert "orders.yaml" in result


class TestFileSearchDefaultMultiRoot:
    """Default search_path='.' scans agent dir AND all local bundle roots."""

    def test_default_search_includes_agent_and_bundle_files(self, tmp_path: Path):
        """Default '.' search returns results from both agent dir and bundle dir."""
        bundle_config, bundle_dir, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        # Place a yaml file inside the agent dir too.
        (agent_dir / "agent_config.yaml").write_text("agent: true", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("yaml")  # default search_path='.'

        # Agent-side file (displayed relative to agent_dir).
        assert "agent_config.yaml" in result
        # Bundle-side files (displayed with @bundle prefix).
        assert "@test_bundle" in result
        assert "bundle.yaml" in result
        assert "users.yaml" in result
        # Summary should mention both search roots.
        assert ". + @test_bundle" in result

    def test_default_search_with_multiple_bundles(self, tmp_path: Path):
        """Default search scans all registered bundles, not just the first."""
        config_a, _, _ = _make_bundle_with_files(tmp_path / "a", bundle_name="alpha", volume_name="vol_a")
        config_b, _, _ = _make_bundle_with_files(tmp_path / "b", bundle_name="beta", volume_name="vol_b")
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(
            base_path=str(agent_dir),
            asset_bundles=[config_a, config_b],
        )
        result = tool._run("yaml")

        assert "@alpha" in result
        assert "@beta" in result

    def test_default_search_without_bundles_only_scans_agent_dir(self, tmp_path: Path):
        """Without bundles, default '.' only scans the agent directory."""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "config.yaml").write_text("x", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir))
        result = tool._run("yaml")

        assert "Found 1 matching files" in result
        assert "config.yaml" in result
        assert "@" not in result

    def test_explicit_relative_path_does_not_trigger_multi_root(self, tmp_path: Path):
        """An explicit 'docs' path does NOT include bundle files."""
        bundle_config, _, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        docs_dir = agent_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "notes.yaml").write_text("note", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("yaml", search_path="docs")

        # Only the agent-side docs/ directory is scanned.
        assert "notes.yaml" in result
        assert "@test_bundle" not in result

    def test_default_search_respects_max_results_across_roots(self, tmp_path: Path):
        """max_results caps the total across agent dir + bundles."""
        bundle_config, bundle_dir, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        # Create many yaml files in agent dir to fill up quota.
        for i in range(10):
            (agent_dir / f"file_{i}.yaml").write_text("x", encoding="utf-8")

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("yaml", max_results=5)

        # At most 5 items should appear.
        lines = [line for line in result.strip().split("\n") if line.startswith(("1.", "2.", "3.", "4.", "5.", "6."))]
        assert len(lines) <= 5

    def test_default_search_includes_volume_storage_location_files(self, tmp_path: Path):
        """Default '.' search covers volume storage_location directories, not just bundle_path.

        This is the key scenario: users place data files (PDFs, CSVs, images) in
        a local directory, and the volume yaml points ``storage_location`` to it.
        The bundle_path itself only contains yaml definitions. A default keyword
        search must see files in both locations.
        """
        bundle_config, bundle_dir, vol_dir = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        # Search for 'report' – these files are exclusively in vol_dir (storage_location).
        result = tool._run("report")

        assert "report_2024.csv" in result
        assert "report_2025.csv" in result
        assert "old_report.csv" in result
        # Volume files should display as @bundle_name/volume_name/...
        assert "@test_bundle/my_files" in result

    def test_default_search_no_match_shows_all_roots_in_message(self, tmp_path: Path):
        """When nothing matches, the 'not found' message shows all searched roots."""
        bundle_config, _, _ = _make_bundle_with_files(tmp_path)
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        tool = create_file_search_tool(base_path=str(agent_dir), asset_bundles=[bundle_config])
        result = tool._run("zzz_nonexistent_zzz")

        assert "No files containing keyword" in result
        assert ". + @test_bundle" in result
