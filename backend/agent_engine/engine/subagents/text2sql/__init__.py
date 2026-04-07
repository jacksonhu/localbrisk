"""Text2SQL sub-agent module.

Provides the DuckDB-backed text2sql capability:
- ``Text2SQLDuckDBService`` — per-agent DuckDB connection with ATTACH support
- ``TableMetadataLoader`` — external AssetBundle table metadata scanner
- ``DuckDBQueryTool`` / ``ListTableMetadataTool`` — LangChain tools for the sub-agent
- ``create_text2sql_tools`` — factory to wire everything together
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.core.constants import ASSET_BUNDLE_CONFIG_FILE

from .metadata import TableMetadataLoader
from .service import Text2SQLDuckDBService
from .tools import DuckDBQueryTool, ListTableMetadataTool

logger = logging.getLogger(__name__)


def _read_bundle_connection(bundle_path: Path) -> Optional[Dict[str, Any]]:
    """Read connection config from an external bundle.yaml file."""
    config_path = bundle_path / ASSET_BUNDLE_CONFIG_FILE
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            bundle_yaml = yaml.safe_load(file) or {}
    except Exception as exc:
        logger.warning("Failed to read bundle config '%s': %s", config_path, exc)
        return None

    connection = bundle_yaml.get("connection")
    if isinstance(connection, dict):
        return connection
    return None


def _normalise_connection_type(raw_type: Any) -> str:
    """Normalize connection type aliases from bundle.yaml."""
    normalized = str(raw_type or "").strip().lower()
    if normalized == "postgres":
        return "postgresql"
    return normalized


def _attach_external_bundle(
    service: Text2SQLDuckDBService,
    bundle_name: str,
    bundle_path: Path,
) -> bool:
    """Attach one external AssetBundle to the DuckDB service when possible."""
    connection = _read_bundle_connection(bundle_path)
    if not connection:
        logger.debug("No connection config found for bundle '%s'", bundle_name)
        return False

    conn_type = _normalise_connection_type(connection.get("type"))
    host = connection.get("host", "127.0.0.1")
    port = connection.get("port")
    db_name = connection.get("db_name", "")
    username = connection.get("username", "")
    password = connection.get("password", "")

    if not db_name:
        logger.warning("Bundle '%s' is missing db_name in connection config", bundle_name)
        return False

    if conn_type == "mysql":
        service.attach_mysql(
            name=bundle_name,
            host=host,
            port=int(port or 3306),
            db=db_name,
            user=username,
            password=password,
        )
        return True

    if conn_type == "postgresql":
        service.attach_postgres(
            name=bundle_name,
            host=host,
            port=int(port or 5432),
            db=db_name,
            user=username,
            password=password,
        )
        return True

    logger.debug(
        "Unsupported connection type '%s' for bundle '%s', skipping attach",
        conn_type,
        bundle_name,
    )
    return False


def create_text2sql_tools(
    *,
    business_unit_path: str,
    asset_bundles: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Any], Text2SQLDuckDBService]:
    """Create text2sql-specific tools and the backing DuckDB service."""
    service = Text2SQLDuckDBService()

    attached_bundle_count = 0
    for bundle_cfg in asset_bundles or []:
        if bundle_cfg.get("bundle_type") != "external":
            continue

        bundle_name = str(bundle_cfg.get("bundle_name") or "").strip()
        bundle_path_raw = bundle_cfg.get("bundle_path")
        if not bundle_name or not bundle_path_raw:
            continue

        if _attach_external_bundle(service, bundle_name, Path(bundle_path_raw)):
            attached_bundle_count += 1

    loader = TableMetadataLoader(business_unit_path)
    tools: List[Any] = [
        DuckDBQueryTool(service=service),
        ListTableMetadataTool(loader=loader),
    ]
    logger.info(
        "Text2SQL tools created: %d tool(s), %d configured bundle(s), %d attached source(s)",
        len(tools),
        attached_bundle_count,
        len(service.attached_sources),
    )
    return tools, service


__all__ = [
    "Text2SQLDuckDBService",
    "TableMetadataLoader",
    "DuckDBQueryTool",
    "ListTableMetadataTool",
    "create_text2sql_tools",
]
