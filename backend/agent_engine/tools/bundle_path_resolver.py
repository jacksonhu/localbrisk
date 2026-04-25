"""Shared ``@`` prefix path resolver for asset bundle directories.

Provides :class:`BundlePathResolver` which translates ``@bundle_name`` or
``@bundle_name/volume_name`` style paths into physical filesystem paths.
This module is consumed by :mod:`file_search`, :mod:`file_operater` and
potentially other tools that need to resolve asset bundle locations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class ResolvedPath:
    """Result of resolving a ``@`` prefixed path."""

    # 解析后的物理文件系统路径
    physical_path: Path
    # 用于展示的 @ 前缀路径（如 @bundle_name/volume_name/sub/path）
    display_prefix: str
    # 是否解析成功
    success: bool = True
    # 错误信息（仅当 success=False 时有值）
    error_message: str = ""
    # 解析来源的 bundle 名称
    bundle_name: str = ""
    # 解析来源的 volume 名称（如果有）
    volume_name: str = ""


class BundlePathResolver:
    """Resolve ``@`` prefixed paths to physical filesystem paths.

    Supports two forms:
    - ``@bundle_name[/sub/path]`` → resolves to ``bundle_path[/sub/path]``
    - ``@bundle_name/volume_name[/sub/path]`` → resolves to
      ``volume.storage_location[/sub/path]`` (local volumes only)

    Volume names take priority over subdirectory names when there is ambiguity.
    If no matching volume is found, the path segment is treated as a
    subdirectory under ``bundle_path``.
    """

    def __init__(self, asset_bundles: Optional[Sequence[Any]] = None) -> None:
        self._bundles: List[Dict[str, Any]] = []
        for raw in list(asset_bundles or []):
            normalized = self._normalize_bundle(raw)
            if normalized is not None:
                self._bundles.append(normalized)

    # ──────────────────────── 公共 API ────────────────────────

    def is_bundle_path(self, raw_path: str) -> bool:
        """判断路径是否以 ``@`` 前缀开头且有可用的 bundle 配置。"""
        if not self._bundles:
            return False
        return (raw_path or "").strip().startswith("@")

    def resolve(self, raw_path: str) -> ResolvedPath:
        """将 ``@`` 前缀路径解析为物理路径。

        解析优先级：
        1. 提取 bundle_name，匹配已注册的 bundle
        2. 如果路径中有第二段，优先匹配 volume 名称
        3. 如果没有匹配的 volume，回退到 bundle_path 下的子目录
        """
        stripped = (raw_path or "").strip()
        if not stripped.startswith("@"):
            return ResolvedPath(
                physical_path=Path(stripped),
                display_prefix=stripped,
                success=False,
                error_message="Path does not start with '@' prefix.",
            )

        # 去掉 @ 前缀，按 / 分割
        without_prefix = stripped[1:]
        parts = [p for p in without_prefix.split("/") if p]
        if not parts:
            return ResolvedPath(
                physical_path=Path("."),
                display_prefix=stripped,
                success=False,
                error_message="Empty bundle name after '@' prefix.",
            )

        bundle_name = parts[0]
        remaining_parts = parts[1:]

        # 查找匹配的 bundle
        bundle = self._find_bundle(bundle_name)
        if bundle is None:
            available = self._list_bundle_names()
            available_text = ", ".join(f"`{n}`" for n in available) if available else "none"
            return ResolvedPath(
                physical_path=Path("."),
                display_prefix=stripped,
                success=False,
                error_message=(
                    f"Bundle `{bundle_name}` not found. "
                    f"Available bundles: {available_text}"
                ),
                bundle_name=bundle_name,
            )

        bundle_path = Path(os.path.expanduser(bundle["bundle_path"])).resolve()

        # 没有后续路径段，直接返回 bundle_path
        if not remaining_parts:
            return ResolvedPath(
                physical_path=bundle_path,
                display_prefix=f"@{bundle_name}",
                success=True,
                bundle_name=bundle_name,
            )

        # 尝试匹配 volume
        potential_volume_name = remaining_parts[0]
        sub_parts = remaining_parts[1:]
        volume = self._find_volume(bundle, potential_volume_name)

        if volume is not None:
            return self._resolve_volume_path(
                bundle_name=bundle_name,
                volume=volume,
                volume_name=potential_volume_name,
                sub_parts=sub_parts,
            )

        # 没有匹配的 volume，回退到 bundle_path 下的子目录
        sub_path = "/".join(remaining_parts)
        resolved = self._safe_join(bundle_path, sub_path)
        if resolved is None:
            return ResolvedPath(
                physical_path=bundle_path,
                display_prefix=f"@{bundle_name}/{sub_path}",
                success=False,
                error_message=f"Path escapes bundle directory: {sub_path}",
                bundle_name=bundle_name,
            )

        display = f"@{bundle_name}/{sub_path}"
        return ResolvedPath(
            physical_path=resolved,
            display_prefix=display,
            success=True,
            bundle_name=bundle_name,
        )

    def available_bundles_description(self) -> str:
        """生成可用 bundle 列表的描述文本，用于工具 description 拼接。"""
        if not self._bundles:
            return ""

        lines = [
            "",
            "Available asset bundles (use `@bundle_name` prefix to search):",
        ]
        for bundle in sorted(self._bundles, key=lambda b: b["bundle_name"]):
            bundle_name = bundle["bundle_name"]
            bundle_type = bundle.get("bundle_type", "local")
            volume_names = [v["name"] for v in bundle.get("volumes", []) if v.get("name")]
            line = f"  - `@{bundle_name}` ({bundle_type})"
            if volume_names:
                vol_list = ", ".join(f"`{v}`" for v in volume_names)
                line += f" — volumes: {vol_list}"
            lines.append(line)
        return "\n".join(lines)

    @property
    def has_bundles(self) -> bool:
        """Whether any usable bundle configurations exist."""
        return len(self._bundles) > 0

    def get_all_local_roots(self) -> List[tuple[str, Path]]:
        """Return ``(display_prefix, physical_root)`` for every searchable local root.

        For each local bundle this yields:
        1. The bundle root itself — ``("@bundle_name", bundle_path)``.
        2. Every local volume whose ``storage_location`` exists on disk —
           ``("@bundle_name/volume_name", storage_location_path)``.

        Volume ``storage_location`` directories are often *outside* the bundle
        tree (e.g. ``~/Documents/data``), so ``os.walk(bundle_path)`` alone
        would never reach them. Including them here ensures the default
        ``search_path='.'`` scan covers all user data.
        """
        roots: List[tuple[str, Path]] = []
        for bundle in self._bundles:
            if bundle.get("bundle_type", "local") != "local":
                continue
            bundle_name = bundle["bundle_name"]
            bundle_path = Path(os.path.expanduser(bundle["bundle_path"])).resolve()

            # Always include the bundle root (contains tables/, config, etc.).
            if bundle_path.is_dir():
                roots.append((bundle_name, bundle_path))

            # Include each local volume's storage_location as a separate root.
            for volume in bundle.get("volumes", []):
                if not isinstance(volume, dict):
                    continue
                if volume.get("volume_type", "local") != "local":
                    continue
                storage_location = (volume.get("storage_location") or "").strip()
                if not storage_location:
                    continue
                vol_path = Path(os.path.expanduser(storage_location)).resolve()
                if vol_path.is_dir():
                    vol_name = volume.get("name", "")
                    display = f"{bundle_name}/{vol_name}" if vol_name else bundle_name
                    roots.append((display, vol_path))
        return roots

    # ──────────────────────── 内部方法 ────────────────────────

    def _resolve_volume_path(
        self,
        *,
        bundle_name: str,
        volume: Dict[str, Any],
        volume_name: str,
        sub_parts: List[str],
    ) -> ResolvedPath:
        """解析 volume 路径，处理 volume_type 和 storage_location 校验。"""
        volume_type = volume.get("volume_type", "local")
        if volume_type != "local":
            return ResolvedPath(
                physical_path=Path("."),
                display_prefix=f"@{bundle_name}/{volume_name}",
                success=False,
                error_message=(
                    f"Volume `{volume_name}` in bundle `{bundle_name}` "
                    f"has type `{volume_type}` which does not support local file operations."
                ),
                bundle_name=bundle_name,
                volume_name=volume_name,
            )

        storage_location = (volume.get("storage_location") or "").strip()
        if not storage_location:
            return ResolvedPath(
                physical_path=Path("."),
                display_prefix=f"@{bundle_name}/{volume_name}",
                success=False,
                error_message=(
                    f"Volume `{volume_name}` in bundle `{bundle_name}` "
                    f"has no storage_location configured."
                ),
                bundle_name=bundle_name,
                volume_name=volume_name,
            )

        volume_root = Path(os.path.expanduser(storage_location)).resolve()
        if not volume_root.exists():
            return ResolvedPath(
                physical_path=volume_root,
                display_prefix=f"@{bundle_name}/{volume_name}",
                success=False,
                error_message=(
                    f"Storage location for volume `{volume_name}` does not exist: "
                    f"{volume_root}"
                ),
                bundle_name=bundle_name,
                volume_name=volume_name,
            )

        if not sub_parts:
            return ResolvedPath(
                physical_path=volume_root,
                display_prefix=f"@{bundle_name}/{volume_name}",
                success=True,
                bundle_name=bundle_name,
                volume_name=volume_name,
            )

        sub_path = "/".join(sub_parts)
        resolved = self._safe_join(volume_root, sub_path)
        if resolved is None:
            return ResolvedPath(
                physical_path=volume_root,
                display_prefix=f"@{bundle_name}/{volume_name}/{sub_path}",
                success=False,
                error_message=f"Path escapes volume directory: {sub_path}",
                bundle_name=bundle_name,
                volume_name=volume_name,
            )

        return ResolvedPath(
            physical_path=resolved,
            display_prefix=f"@{bundle_name}/{volume_name}/{sub_path}",
            success=True,
            bundle_name=bundle_name,
            volume_name=volume_name,
        )

    def _find_bundle(self, bundle_name: str) -> Optional[Dict[str, Any]]:
        """按名称查找 bundle。"""
        for bundle in self._bundles:
            if bundle["bundle_name"] == bundle_name:
                return bundle
        return None

    def _find_volume(self, bundle: Dict[str, Any], volume_name: str) -> Optional[Dict[str, Any]]:
        """在 bundle 的 volumes 列表中按名称查找 volume。"""
        for volume in bundle.get("volumes", []):
            if not isinstance(volume, dict):
                continue
            if volume.get("name") == volume_name:
                return volume
        return None

    def _list_bundle_names(self) -> List[str]:
        """返回所有已注册的 bundle 名称列表。"""
        return sorted(b["bundle_name"] for b in self._bundles)

    @staticmethod
    def _safe_join(base: Path, sub_path: str) -> Optional[Path]:
        """安全拼接路径，确保结果不逃逸出 base 目录。"""
        resolved = (base / sub_path).resolve()
        try:
            resolved.relative_to(base)
            return resolved
        except ValueError:
            return None

    @staticmethod
    def _normalize_bundle(raw_bundle: Any) -> Optional[Dict[str, Any]]:
        """将 AssetBundleBackendConfig 或 dict 标准化为内部 dict 格式。"""
        if raw_bundle is None:
            return None
        if isinstance(raw_bundle, dict):
            source = raw_bundle
        else:
            source = {
                "bundle_name": getattr(raw_bundle, "bundle_name", None),
                "bundle_type": getattr(raw_bundle, "bundle_type", None),
                "bundle_path": getattr(raw_bundle, "bundle_path", None),
                "mount_path": getattr(raw_bundle, "mount_path", None),
                "volumes": getattr(raw_bundle, "volumes", None),
            }

        bundle_name = str(source.get("bundle_name") or "").strip()
        bundle_path = str(source.get("bundle_path") or "").strip()
        if not bundle_name or not bundle_path:
            return None

        return {
            "bundle_name": bundle_name,
            "bundle_type": str(source.get("bundle_type") or "local").strip().lower() or "local",
            "bundle_path": str(Path(os.path.expanduser(bundle_path)).resolve()),
            "mount_path": str(source.get("mount_path") or f"/{bundle_name}").strip() or f"/{bundle_name}",
            "volumes": list(source.get("volumes") or []),
        }


__all__ = [
    "BundlePathResolver",
    "ResolvedPath",
]
