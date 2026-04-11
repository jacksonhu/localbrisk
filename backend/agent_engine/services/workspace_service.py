"""Virtual workspace service with explicit mount boundaries and safe path resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class WorkspaceMount:
    """One virtual mount entry exposed inside the runtime workspace."""

    virtual_prefix: str
    real_path: str
    writable: bool = False
    source_type: str = "filesystem"


class WorkspaceService:
    """Provide a safe virtual filesystem view for runtime tools."""

    def __init__(self, root_dir: str | Path, mounts: Optional[Iterable[WorkspaceMount]] = None) -> None:
        self.root_dir = Path(os.path.expanduser(str(root_dir))).resolve()
        if not self.root_dir.exists() or not self.root_dir.is_dir():
            raise ValueError(f"Workspace root does not exist or is not a directory: {root_dir}")

        normalized_mounts = [self._normalize_mount(mount) for mount in mounts or []]
        self._mounts = sorted(normalized_mounts, key=lambda mount: len(mount.virtual_prefix), reverse=True)

    @staticmethod
    def normalize_virtual_path(virtual_path: str) -> str:
        """Normalize one virtual path and reject traversal attempts."""
        raw = str(virtual_path or "/").strip().replace("\\", "/")
        if not raw:
            return "/"
        if not raw.startswith("/"):
            raw = f"/{raw}"

        parts: List[str] = []
        for part in raw.split("/"):
            if not part or part == ".":
                continue
            if part == "..":
                raise ValueError("Path traversal is not allowed")
            parts.append(part)
        return "/" + "/".join(parts) if parts else "/"

    def resolve_virtual_path(self, virtual_path: str) -> str:
        """Resolve a virtual path into one safe real filesystem path."""
        normalized = self.normalize_virtual_path(virtual_path)
        mount = self._match_mount(normalized)
        if mount is not None:
            relative_part = normalized[len(mount.virtual_prefix) :].lstrip("/")
            return str(self._resolve_under_root(Path(mount.real_path), relative_part))
        return str(self._resolve_under_root(self.root_dir, normalized.lstrip("/")))

    def ls_info(self, virtual_path: str = "/") -> List[Dict[str, Any]]:
        """List one directory in virtual-path form for tool traversal."""
        normalized = self.normalize_virtual_path(virtual_path)
        if normalized == "/":
            return self._list_root_directory()

        mount = self._match_mount(normalized)
        if mount is not None:
            relative_part = normalized[len(mount.virtual_prefix) :].lstrip("/")
            target_root = self._resolve_under_root(Path(mount.real_path), relative_part)
            return self._list_directory(target_root, normalized, mount=mount)

        target_root = self._resolve_under_root(self.root_dir, normalized.lstrip("/"))
        return self._list_directory(target_root, normalized, mount=None)

    def list_mounts(self) -> Dict[str, str]:
        """Return current virtual mount mappings for debugging and observability."""
        result = {"/": str(self.root_dir)}
        for mount in self._mounts:
            result[mount.virtual_prefix] = mount.real_path
        return result

    def _list_root_directory(self) -> List[Dict[str, Any]]:
        """List the root directory and inject top-level mount placeholders."""
        entries: Dict[str, Dict[str, Any]] = {}
        for child in sorted(self.root_dir.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
            if child.name.startswith("."):
                continue
            entry = self._build_entry(child, parent_virtual="/")
            entries[entry["path"]] = entry

        for mount in self._mounts:
            top_level_name = mount.virtual_prefix.strip("/").split("/", 1)[0]
            if not top_level_name:
                continue
            virtual_path = f"/{top_level_name}"
            entries.setdefault(
                virtual_path,
                {
                    "name": top_level_name,
                    "path": virtual_path,
                    "is_dir": True,
                    "type": "directory",
                    "size": 0,
                    "source_type": mount.source_type,
                    "mounted": True,
                },
            )
        return list(entries.values())

    def _list_directory(self, target_root: Path, parent_virtual: str, *, mount: Optional[WorkspaceMount]) -> List[Dict[str, Any]]:
        """List one real directory and return virtual entries."""
        if not target_root.exists() or not target_root.is_dir():
            return []

        entries: List[Dict[str, Any]] = []
        for child in sorted(target_root.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
            if child.name.startswith("."):
                continue
            entry = self._build_entry(child, parent_virtual=parent_virtual)
            if mount is not None:
                entry["mounted"] = True
                entry["source_type"] = mount.source_type
            entries.append(entry)
        return entries

    def _build_entry(self, target_path: Path, *, parent_virtual: str) -> Dict[str, Any]:
        """Build one virtual directory entry."""
        parent = "/" if parent_virtual == "/" else parent_virtual.rstrip("/")
        virtual_path = f"/{target_path.name}" if parent == "/" else f"{parent}/{target_path.name}"
        return {
            "name": target_path.name,
            "path": virtual_path,
            "is_dir": target_path.is_dir(),
            "type": "directory" if target_path.is_dir() else "file",
            "size": 0 if target_path.is_dir() else target_path.stat().st_size,
        }

    def _match_mount(self, normalized_virtual_path: str) -> Optional[WorkspaceMount]:
        """Return the longest matching mount for a normalized virtual path."""
        for mount in self._mounts:
            prefix = mount.virtual_prefix
            if normalized_virtual_path == prefix or normalized_virtual_path.startswith(f"{prefix}/"):
                return mount
        return None

    @staticmethod
    def _resolve_under_root(root_dir: Path, relative_part: str) -> Path:
        """Resolve a relative path and keep it constrained inside its root."""
        base_root = Path(os.path.expanduser(str(root_dir))).resolve()
        target = (base_root / relative_part).resolve()
        try:
            target.relative_to(base_root)
        except ValueError as exc:
            raise ValueError("Resolved path escapes the workspace boundary") from exc
        return target

    @classmethod
    def _normalize_mount(cls, mount: WorkspaceMount) -> WorkspaceMount:
        """Normalize one mount definition before runtime use."""
        normalized_prefix = cls.normalize_virtual_path(mount.virtual_prefix)
        normalized_root = str(Path(os.path.expanduser(mount.real_path)).resolve())
        return WorkspaceMount(
            virtual_prefix=normalized_prefix,
            real_path=normalized_root,
            writable=mount.writable,
            source_type=mount.source_type,
        )


__all__ = ["WorkspaceMount", "WorkspaceService"]
