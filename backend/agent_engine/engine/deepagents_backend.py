"""Backend assembly helpers for DeepAgents engine."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Type

from app.core.constants import AGENT_MEMORIES_DIR, ASSET_BUNDLES_DIR, TABLES_DIR

from .deepagents_context import AgentBuildContext

logger = logging.getLogger(__name__)


def create_backend(
    context: AgentBuildContext,
    filesystem_backend_cls: Type[Any],
    local_shell_backend_cls: Optional[Type[Any]],
    composite_backend_cls: Optional[Type[Any]],
):
    """Create a DeepAgents backend with mounted memories and asset bundles."""
    output_path = context.output_path
    has_memories = bool(context.memories)
    has_skills = bool(context.skills)
    has_bundles = bool(context.asset_bundles)

    if (not has_skills and not has_bundles and not has_memories) or composite_backend_cls is None or local_shell_backend_cls is None:
        logger.info("Creating simple FilesystemBackend for %s", output_path)
        return filesystem_backend_cls(root_dir=output_path)

    routes = {
        "/large_tool_results/": filesystem_backend_cls(root_dir=f"{context.agent_path}/.large_tool_results", virtual_mode=True),
        "/conversation_history/": filesystem_backend_cls(root_dir=f"{context.agent_path}/.conversation_history", virtual_mode=True),
    }
    if has_memories:
        memories_dir = f"{context.agent_path}/{AGENT_MEMORIES_DIR}"
        if os.path.exists(memories_dir):
            routes["/memories/"] = filesystem_backend_cls(root_dir=memories_dir, virtual_mode=True)
        else:
            logger.warning("Memories directory does not exist: %s", memories_dir)

    if has_bundles:
        for bundle_config in context.asset_bundles:
            if bundle_config.bundle_type == "external":
                mount_path = f"{bundle_config.mount_path}/"
                real_path = f"{context.business_unit_path}/{ASSET_BUNDLES_DIR}/{bundle_config.bundle_name}/{TABLES_DIR}"
                routes[mount_path] = filesystem_backend_cls(root_dir=real_path, virtual_mode=True)
                continue

            if bundle_config.bundle_type != "local":
                continue
            for volume in bundle_config.volumes:
                volume_name = volume.get("name", "")
                volume_type = volume.get("volume_type", "local")
                storage_location = volume.get("storage_location", "")
                if volume_type != "local" or not storage_location:
                    logger.debug("Skipping non-local or empty volume %s for bundle %s", volume_name, bundle_config.bundle_name)
                    continue
                storage_path = os.path.expanduser(storage_location)
                if not os.path.exists(storage_path):
                    logger.warning("Volume path does not exist: %s", storage_path)
                    continue
                mount_path = f"{bundle_config.mount_path}_{volume_name}/"
                routes[mount_path] = filesystem_backend_cls(root_dir=storage_path, virtual_mode=True)

    venv_path = f"{context.agent_path}/venv"
    env = {
        "PATH": f"{venv_path}/bin:{os.environ.get('PATH', '')}",
        "VIRTUAL_ENV": venv_path,
    }
    if not routes:
        raise ValueError("No valid mount points")

    backend = composite_backend_cls(
        default=local_shell_backend_cls(
            root_dir=context.agent_path,
            virtual_mode=False,
            inherit_env=True,
            env=env,
        ),
        routes=routes,
    )
    try:
        python_location = backend.execute("which python").output
        logger.info("DeepAgents backend python path: %s", python_location)
    except Exception as exc:
        logger.warning("Failed to inspect backend python path: %s", exc)
    logger.info("Created CompositeBackend with %s route(s)", len(routes))
    return backend
