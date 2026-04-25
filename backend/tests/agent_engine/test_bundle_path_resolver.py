"""Tests for the BundlePathResolver module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_engine.tools.bundle_path_resolver import BundlePathResolver, ResolvedPath


def _make_bundle(
    tmp_path: Path,
    bundle_name: str = "test_bundle",
    bundle_type: str = "local",
    volumes: list | None = None,
) -> dict:
    """创建一个模拟的 bundle 配置 dict 和对应的目录结构。"""
    bundle_dir = tmp_path / "asset_bundles" / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    return {
        "bundle_name": bundle_name,
        "bundle_type": bundle_type,
        "bundle_path": str(bundle_dir),
        "mount_path": f"/{bundle_name}",
        "volumes": volumes or [],
    }


def _make_local_volume(
    tmp_path: Path,
    volume_name: str = "my_files",
    storage_location: str | None = None,
    create_dir: bool = True,
) -> dict:
    """创建一个模拟的 local volume 配置 dict 和对应的目录。"""
    if storage_location is None:
        vol_dir = tmp_path / "volumes" / volume_name
        if create_dir:
            vol_dir.mkdir(parents=True, exist_ok=True)
        storage_location = str(vol_dir)
    return {
        "name": volume_name,
        "volume_type": "local",
        "file_path": str(tmp_path / f"{volume_name}.yaml"),
        "storage_location": storage_location,
    }


class TestBundlePathResolverBasic:
    """基础功能测试。"""

    def test_is_bundle_path_returns_false_when_no_bundles(self):
        resolver = BundlePathResolver(asset_bundles=[])
        assert resolver.is_bundle_path("@some_bundle") is False

    def test_is_bundle_path_returns_false_for_non_at_path(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path)
        resolver = BundlePathResolver(asset_bundles=[bundle])
        assert resolver.is_bundle_path("some/path") is False
        assert resolver.is_bundle_path("") is False

    def test_is_bundle_path_returns_true_for_at_path(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path)
        resolver = BundlePathResolver(asset_bundles=[bundle])
        assert resolver.is_bundle_path("@test_bundle") is True
        assert resolver.is_bundle_path("@anything") is True

    def test_has_bundles_property(self, tmp_path: Path):
        assert BundlePathResolver(asset_bundles=[]).has_bundles is False
        assert BundlePathResolver(asset_bundles=None).has_bundles is False
        bundle = _make_bundle(tmp_path)
        assert BundlePathResolver(asset_bundles=[bundle]).has_bundles is True


class TestResolveBundlePath:
    """测试 @bundle_name 解析到 bundle_path。"""

    def test_resolve_bundle_name_only(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, bundle_name="myasset")
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset")
        assert result.success is True
        assert result.physical_path == Path(bundle["bundle_path"]).resolve()
        assert result.display_prefix == "@myasset"
        assert result.bundle_name == "myasset"

    def test_resolve_bundle_with_subdir(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, bundle_name="myasset")
        sub_dir = Path(bundle["bundle_path"]) / "tables"
        sub_dir.mkdir(parents=True, exist_ok=True)

        resolver = BundlePathResolver(asset_bundles=[bundle])
        result = resolver.resolve("@myasset/tables")

        assert result.success is True
        assert result.physical_path == sub_dir.resolve()
        assert result.display_prefix == "@myasset/tables"

    def test_resolve_nonexistent_bundle_returns_error(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, bundle_name="existing")
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@nonexistent")
        assert result.success is False
        assert "not found" in result.error_message.lower()
        assert "`existing`" in result.error_message

    def test_resolve_empty_bundle_name_returns_error(self):
        resolver = BundlePathResolver(asset_bundles=[])
        result = resolver.resolve("@")
        assert result.success is False
        assert "empty" in result.error_message.lower()

    def test_resolve_non_at_path_returns_error(self):
        resolver = BundlePathResolver(asset_bundles=[])
        result = resolver.resolve("some/path")
        assert result.success is False
        assert "does not start with" in result.error_message.lower()


class TestResolveVolumePath:
    """测试 @bundle_name/volume_name 解析到 volume 的 storage_location。"""

    def test_resolve_local_volume(self, tmp_path: Path):
        volume = _make_local_volume(tmp_path, volume_name="data_files")
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/data_files")
        assert result.success is True
        assert result.physical_path == Path(volume["storage_location"]).resolve()
        assert result.display_prefix == "@myasset/data_files"
        assert result.bundle_name == "myasset"
        assert result.volume_name == "data_files"

    def test_resolve_local_volume_with_subpath(self, tmp_path: Path):
        volume = _make_local_volume(tmp_path, volume_name="data_files")
        sub_dir = Path(volume["storage_location"]) / "reports"
        sub_dir.mkdir(parents=True, exist_ok=True)

        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/data_files/reports")
        assert result.success is True
        assert result.physical_path == sub_dir.resolve()
        assert result.display_prefix == "@myasset/data_files/reports"

    def test_resolve_non_local_volume_returns_error(self, tmp_path: Path):
        volume = {
            "name": "s3_vol",
            "volume_type": "s3",
            "file_path": str(tmp_path / "s3_vol.yaml"),
        }
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/s3_vol")
        assert result.success is False
        assert "does not support local file operations" in result.error_message

    def test_resolve_volume_missing_storage_location(self, tmp_path: Path):
        volume = {
            "name": "empty_vol",
            "volume_type": "local",
            "file_path": str(tmp_path / "empty_vol.yaml"),
            "storage_location": "",
        }
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/empty_vol")
        assert result.success is False
        assert "no storage_location" in result.error_message.lower()

    def test_resolve_volume_storage_location_not_exists(self, tmp_path: Path):
        volume = _make_local_volume(
            tmp_path,
            volume_name="missing_vol",
            storage_location=str(tmp_path / "nonexistent_dir"),
            create_dir=False,
        )
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/missing_vol")
        assert result.success is False
        assert "does not exist" in result.error_message

    def test_resolve_nonexistent_volume_falls_back_to_subdir(self, tmp_path: Path):
        """当 volume 不存在时，回退到 bundle_path 下的子目录。"""
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[])
        tables_dir = Path(bundle["bundle_path"]) / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        resolver = BundlePathResolver(asset_bundles=[bundle])
        result = resolver.resolve("@myasset/tables")

        assert result.success is True
        assert result.physical_path == tables_dir.resolve()
        assert result.volume_name == ""


class TestPathSafety:
    """路径安全校验测试。"""

    def test_path_traversal_in_bundle_subdir_blocked(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, bundle_name="myasset")
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/../../etc/passwd")
        assert result.success is False
        assert "escapes" in result.error_message.lower()

    def test_path_traversal_in_volume_subpath_blocked(self, tmp_path: Path):
        volume = _make_local_volume(tmp_path, volume_name="data")
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        result = resolver.resolve("@myasset/data/../../etc/passwd")
        assert result.success is False
        assert "escapes" in result.error_message.lower()


class TestAvailableBundlesDescription:
    """测试 available_bundles_description 方法。"""

    def test_empty_bundles_returns_empty_string(self):
        resolver = BundlePathResolver(asset_bundles=[])
        assert resolver.available_bundles_description() == ""

    def test_description_lists_bundle_names_and_types(self, tmp_path: Path):
        bundle1 = _make_bundle(tmp_path, bundle_name="alpha", bundle_type="local")
        bundle2 = _make_bundle(tmp_path, bundle_name="beta", bundle_type="external")
        resolver = BundlePathResolver(asset_bundles=[bundle1, bundle2])

        desc = resolver.available_bundles_description()
        assert "@alpha" in desc
        assert "@beta" in desc
        assert "local" in desc
        assert "external" in desc

    def test_description_includes_volume_names(self, tmp_path: Path):
        volume = _make_local_volume(tmp_path, volume_name="my_data")
        bundle = _make_bundle(tmp_path, bundle_name="myasset", volumes=[volume])
        resolver = BundlePathResolver(asset_bundles=[bundle])

        desc = resolver.available_bundles_description()
        assert "@myasset" in desc
        assert "my_data" in desc


class TestNormalizeBundleInput:
    """测试 dataclass 和 dict 输入的标准化。"""

    def test_accepts_dict_input(self, tmp_path: Path):
        bundle = _make_bundle(tmp_path, bundle_name="dict_bundle")
        resolver = BundlePathResolver(asset_bundles=[bundle])
        assert resolver.has_bundles is True

        result = resolver.resolve("@dict_bundle")
        assert result.success is True

    def test_accepts_dataclass_input(self, tmp_path: Path):
        from dataclasses import dataclass, field
        from typing import Any, Dict, List

        @dataclass
        class FakeConfig:
            bundle_name: str = ""
            bundle_type: str = "local"
            bundle_path: str = ""
            mount_path: str = ""
            volumes: List[Dict[str, Any]] = field(default_factory=list)

        bundle_dir = tmp_path / "asset_bundles" / "dc_bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        config = FakeConfig(
            bundle_name="dc_bundle",
            bundle_type="local",
            bundle_path=str(bundle_dir),
            mount_path="/dc_bundle",
        )
        resolver = BundlePathResolver(asset_bundles=[config])
        assert resolver.has_bundles is True

        result = resolver.resolve("@dc_bundle")
        assert result.success is True

    def test_skips_invalid_bundle(self):
        resolver = BundlePathResolver(asset_bundles=[None, {}, {"bundle_name": ""}])
        assert resolver.has_bundles is False
