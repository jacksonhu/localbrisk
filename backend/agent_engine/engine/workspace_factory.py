"""Workspace factory for building safe runtime filesystem views."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from app.core.constants import ASSET_BUNDLES_DIR, TABLES_DIR

from ..services.workspace_service import WorkspaceMount, WorkspaceService
from .agent_context_loader import AgentBuildContext


SYSTEM_MOUNTS = (
    ("/large_tool_results", ".large_tool_results", "large_tool_results"),
    ("/conversation_history", ".conversation_history", "conversation_history"),
)


class WorkspaceFactory:
    """Build a workspace service from one normalized agent context."""

    @classmethod
    def create_workspace(cls, context: AgentBuildContext) -> WorkspaceService:
        """Create one workspace service for an agent runtime."""
        mounts: List[WorkspaceMount] = []

        for virtual_prefix, relative_dir, source_type in SYSTEM_MOUNTS:
            real_dir = Path(context.agent_path) / relative_dir
            real_dir.mkdir(parents=True, exist_ok=True)
            mounts.append(
                WorkspaceMount(
                    virtual_prefix=virtual_prefix,
                    real_path=str(real_dir),
                    writable=True,
                    source_type=source_type,
                )
            )

        for bundle in context.asset_bundles or []:
            if bundle.bundle_type == "external":
                real_dir = Path(context.business_unit_path) / ASSET_BUNDLES_DIR / bundle.bundle_name / TABLES_DIR
                if real_dir.exists() and real_dir.is_dir():
                    mounts.append(
                        WorkspaceMount(
                            virtual_prefix=bundle.mount_path,
                            real_path=str(real_dir),
                            writable=False,
                            source_type="asset_bundle_table",
                        )
                    )
                continue

            if bundle.bundle_type != "local":
                continue

            for volume in bundle.volumes:
                volume_name = str(volume.get("name") or "").strip()
                volume_type = str(volume.get("volume_type") or "local").strip()
                storage_location = str(volume.get("storage_location") or "").strip()
                if volume_type != "local" or not volume_name or not storage_location:
                    continue

                real_dir = Path(os.path.expanduser(storage_location))
                if not real_dir.exists() or not real_dir.is_dir():
                    continue

                mounts.append(
                    WorkspaceMount(
                        virtual_prefix=f"{bundle.mount_path}_{volume_name}",
                        real_path=str(real_dir),
                        writable=False,
                        source_type="asset_bundle_volume",
                    )
                )

        return WorkspaceService(root_dir=context.agent_path, mounts=mounts)



def create_workspace_backend(context: AgentBuildContext) -> WorkspaceService:
    """Compatibility helper returning the default runtime workspace object."""
    return WorkspaceFactory.create_workspace(context)


__all__ = ["WorkspaceFactory", "create_workspace_backend"]
