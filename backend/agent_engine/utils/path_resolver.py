"""Helpers for resolving virtual workspace paths into real filesystem paths."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)



def resolve_virtual_path(backend: object, virtual_path: str) -> str:
    """Resolve one virtual path using the first supported backend interface."""
    if backend is None:
        raise ValueError("backend is required")

    direct_resolver = getattr(backend, "resolve_virtual_path", None)
    if callable(direct_resolver):
        resolved = direct_resolver(virtual_path)
        return str(resolved)

    try:
        from deepagents.backends.composite import CompositeBackend as _CompositeBackend
        from deepagents.backends.filesystem import FilesystemBackend
    except ImportError:
        _CompositeBackend = None
        FilesystemBackend = None

    if FilesystemBackend is not None and isinstance(backend, FilesystemBackend):
        resolved = backend._resolve_path(virtual_path)
        return str(resolved)

    if _CompositeBackend is not None and isinstance(backend, _CompositeBackend):
        selected_backend, stripped_key = backend._get_backend_and_key(virtual_path)
        if FilesystemBackend is not None and isinstance(selected_backend, FilesystemBackend):
            resolved = selected_backend._resolve_path(stripped_key)
            return str(resolved)
        logger.warning(
            "Backend route %s does not expose a local filesystem path for %s",
            type(selected_backend).__name__,
            virtual_path,
        )
        return virtual_path

    logger.warning("Backend type %s does not support virtual path resolution", type(backend).__name__)
    return virtual_path



def resolve_virtual_path_safe(backend: object, virtual_path: str) -> Optional[str]:
    """Resolve one virtual path and return ``None`` instead of raising on failure."""
    try:
        return resolve_virtual_path(backend, virtual_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to resolve virtual path %s: %s", virtual_path, exc)
        return None



def list_backend_routes(backend: object) -> dict[str, str]:
    """Return the currently visible backend routes for debugging."""
    list_mounts = getattr(backend, "list_mounts", None)
    if callable(list_mounts):
        result = list_mounts()
        return result if isinstance(result, dict) else {}

    try:
        from deepagents.backends.composite import CompositeBackend as _CompositeBackend
        from deepagents.backends.filesystem import FilesystemBackend
    except ImportError:
        _CompositeBackend = None
        FilesystemBackend = None

    result: dict[str, str] = {}
    if FilesystemBackend is not None and isinstance(backend, FilesystemBackend):
        result["/"] = str(backend.cwd)
        return result

    if _CompositeBackend is not None and isinstance(backend, _CompositeBackend):
        for prefix, routed_backend in backend.sorted_routes:
            if FilesystemBackend is not None and isinstance(routed_backend, FilesystemBackend):
                result[prefix.rstrip("/") or "/"] = str(routed_backend.cwd)
            else:
                result[prefix.rstrip("/") or "/"] = f"<{type(routed_backend).__name__}>"
        default_backend = backend.default
        if FilesystemBackend is not None and isinstance(default_backend, FilesystemBackend):
            result["/"] = str(default_backend.cwd)
    return result
