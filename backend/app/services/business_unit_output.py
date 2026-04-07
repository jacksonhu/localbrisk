"""BusinessUnit output file operations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from app.core.constants import AGENT_OUTPUT_DIR

if TYPE_CHECKING:
    from app.services.business_unit_service import BusinessUnitService


class BusinessUnitOutputService:
    """Handle output file access for agents under a business unit."""

    def __init__(self, business_unit_service: "BusinessUnitService"):
        self._business_unit_service = business_unit_service

    def _resolve_output_path(self, business_unit_id: str, agent_name: str, relative_path: str) -> Path:
        """Resolve an output file path and block directory traversal."""
        agent_path = self._business_unit_service.agent_service._get_agent_path(business_unit_id, agent_name)
        output_path = (agent_path / AGENT_OUTPUT_DIR).resolve()
        if not output_path.exists() or not output_path.is_dir():
            raise FileNotFoundError("output not found")

        if relative_path is None:
            raise ValueError("relative path is required")

        normalized = relative_path.strip().replace('\\', '/')
        if normalized.startswith('/'):
            raise ValueError("absolute path is not allowed")

        target_path = (output_path / normalized).resolve()
        try:
            target_path.relative_to(output_path)
        except ValueError as exc:
            raise ValueError("invalid relative path") from exc

        return target_path

    def get_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str) -> Dict[str, Any]:
        """Read an existing UTF-8 text file under the agent output directory."""
        target_path = self._resolve_output_path(business_unit_id, agent_name, relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("output file not found")

        content = self._business_unit_service._read_file(target_path)
        if content is None:
            raise ValueError("file content is not readable as utf-8 text")

        return {
            "path": str(target_path),
            "relative_path": relative_path.replace('\\', '/'),
            "content": content,
        }

    def save_output_file_content(self, business_unit_id: str, agent_name: str, relative_path: str, content: str) -> Dict[str, Any]:
        """Save content to an existing file under the agent output directory."""
        target_path = self._resolve_output_path(business_unit_id, agent_name, relative_path)
        if not target_path.exists() or not target_path.is_file():
            raise FileNotFoundError("output file not found")

        self._business_unit_service._write_file(target_path, content)
        return {
            "path": str(target_path),
            "relative_path": relative_path.replace('\\', '/'),
            "content": content,
        }
