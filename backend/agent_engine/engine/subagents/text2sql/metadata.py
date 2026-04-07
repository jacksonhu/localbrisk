"""Table metadata loader for text2sql sub-agent.

Scans external AssetBundle ``tables/`` directories, parses the YAML
metadata files, and returns structured schema information that the
text2sql agent can use to generate accurate SQL.

Expected YAML layout per table (produced by metadata_sync_service):
    baseinfo:
      name: <table_name>
      description: "..."
    schema_name: "..."
    columns:
      - name: id
        data_type: bigint
        nullable: false
        is_primary_key: true
        comment: "Primary key"
      - ...
    primary_keys: [id]
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.core.constants import (
    ASSET_BUNDLES_DIR,
    ASSET_BUNDLE_CONFIG_FILE,
    TABLES_DIR,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Public data structures (plain dicts for easy serialisation)
# ------------------------------------------------------------------

def _build_column_info(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a single column entry from YAML into a compact dict."""
    return {
        "name": raw.get("name", ""),
        "data_type": raw.get("data_type", "unknown"),
        "nullable": raw.get("nullable", True),
        "is_primary_key": raw.get("is_primary_key", False),
        "comment": raw.get("comment") or "",
    }


def _build_table_info(
    bundle_name: str,
    table_name: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured table-info dict from parsed YAML config."""
    baseinfo = config.get("baseinfo", {})
    columns_raw: List[Dict[str, Any]] = config.get("columns", [])
    columns = [_build_column_info(c) for c in columns_raw]
    return {
        "bundle_name": bundle_name,
        "table_name": table_name,
        "display_name": baseinfo.get("display_name") or table_name,
        "description": baseinfo.get("description") or "",
        "schema_name": config.get("schema_name") or "",
        "table_type": config.get("table_type") or "BASE TABLE",
        "primary_keys": config.get("primary_keys", []),
        "row_count": config.get("row_count"),
        "columns": columns,
    }


# ------------------------------------------------------------------
# Loader
# ------------------------------------------------------------------

class TableMetadataLoader:
    """Loads table metadata from external AssetBundle YAML files.

    Args:
        business_unit_path: Absolute path to the BusinessUnit directory
            (e.g. ``~/.localbrisk/App_Data/Catalogs/<bu_id>``).
    """

    def __init__(self, business_unit_path: str) -> None:
        self._bu_path = Path(business_unit_path)
        logger.debug(
            "TableMetadataLoader initialised: bu_path=%s", self._bu_path
        )

    # ------------------------------------------------------------------
    # Scan helpers
    # ------------------------------------------------------------------

    def _iter_external_bundles(self) -> List[Path]:
        """Return paths of all external AssetBundles under the BusinessUnit."""
        bundles_dir = self._bu_path / ASSET_BUNDLES_DIR
        if not bundles_dir.exists():
            return []

        result: List[Path] = []
        for bundle_dir in sorted(bundles_dir.iterdir()):
            if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
                continue
            bundle_yaml = bundle_dir / ASSET_BUNDLE_CONFIG_FILE
            if not bundle_yaml.exists():
                continue
            try:
                with open(bundle_yaml, "r", encoding="utf-8") as fh:
                    cfg = yaml.safe_load(fh) or {}
                if cfg.get("bundle_type") == "external":
                    result.append(bundle_dir)
            except Exception as e:
                logger.warning(
                    "Failed to read bundle config %s: %s", bundle_yaml, e
                )
        return result

    def _load_table_yaml(self, yaml_path: Path) -> Optional[Dict[str, Any]]:
        """Safely load and return a single table YAML file."""
        try:
            with open(yaml_path, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception as e:
            logger.warning("Failed to parse table YAML %s: %s", yaml_path, e)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_tables(
        self,
        bundle_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return a compact summary of all available tables.

        Each item contains ``bundle_name``, ``table_name``, ``description``,
        ``column_count``, and ``primary_keys``.

        Args:
            bundle_name: If provided, only scan the specified bundle.
        """
        summaries: List[Dict[str, Any]] = []
        for bundle_dir in self._iter_external_bundles():
            if bundle_name and bundle_dir.name != bundle_name:
                continue
            tables_dir = bundle_dir / TABLES_DIR
            if not tables_dir.exists():
                continue
            for yaml_file in sorted(tables_dir.glob("*.yaml")):
                if yaml_file.name.startswith("."):
                    continue
                cfg = self._load_table_yaml(yaml_file)
                if cfg is None:
                    continue
                baseinfo = cfg.get("baseinfo", {})
                summaries.append({
                    "bundle_name": bundle_dir.name,
                    "table_name": baseinfo.get("name") or yaml_file.stem,
                    "description": baseinfo.get("description") or "",
                    "column_count": len(cfg.get("columns", [])),
                    "primary_keys": cfg.get("primary_keys", []),
                })

        logger.info("Listed %d table(s) from external bundles", len(summaries))
        return summaries

    def get_table_schema(
        self,
        bundle_name: str,
        table_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the full schema (with columns) for a specific table.

        Args:
            bundle_name: The AssetBundle name.
            table_name: The table name (stem of the YAML file).

        Returns:
            Structured table info dict, or ``None`` if not found.
        """
        tables_dir = (
            self._bu_path / ASSET_BUNDLES_DIR / bundle_name / TABLES_DIR
        )
        if not tables_dir.exists():
            logger.debug("Tables dir does not exist: %s", tables_dir)
            return None

        yaml_path = tables_dir / f"{table_name}.yaml"
        if not yaml_path.exists():
            logger.debug("Table YAML not found: %s", yaml_path)
            return None

        cfg = self._load_table_yaml(yaml_path)
        if cfg is None:
            return None

        return _build_table_info(bundle_name, table_name, cfg)

    def get_all_schemas(
        self,
        bundle_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return full schemas for all tables (optionally filtered by bundle).

        Useful when the total number of tables is small and the agent wants
        all metadata in one shot.
        """
        results: List[Dict[str, Any]] = []
        for bundle_dir in self._iter_external_bundles():
            if bundle_name and bundle_dir.name != bundle_name:
                continue
            tables_dir = bundle_dir / TABLES_DIR
            if not tables_dir.exists():
                continue
            for yaml_file in sorted(tables_dir.glob("*.yaml")):
                if yaml_file.name.startswith("."):
                    continue
                cfg = self._load_table_yaml(yaml_file)
                if cfg is None:
                    continue
                tname = (cfg.get("baseinfo") or {}).get("name") or yaml_file.stem
                results.append(
                    _build_table_info(bundle_dir.name, tname, cfg)
                )

        logger.info(
            "Loaded full schemas for %d table(s) from external bundles",
            len(results),
        )
        return results
