"""Runtime asset bundle discovery tool bound to one business unit."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Type

import yaml
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.constants import (
    ASSET_BUNDLE_CONFIG_FILE,
    ASSET_BUNDLES_DIR,
    FUNCTIONS_DIR,
    NOTES_DIR,
    TABLES_DIR,
    VOLUMES_DIR,
)

logger = logging.getLogger(__name__)

_SUPPORTED_MODES = {"auto", "overview", "resource"}
_SUPPORTED_ASSET_TYPES = {"bundle", "volume", "table", "function", "note"}


class AssetBundleLinkInput(BaseModel):
    mode: str = Field(
        default="auto",
        description="Query mode: auto, overview, or resource",
    )
    bundle_name: Optional[str] = Field(
        default=None,
        description="Optional bundle name filter",
    )
    bundle_type: Optional[str] = Field(
        default=None,
        description="Optional bundle type filter, such as local or external",
    )
    asset_type: Optional[str] = Field(
        default=None,
        description="Optional asset type filter: bundle, volume, table, function, or note",
    )
    keyword: Optional[str] = Field(
        default=None,
        description="Optional keyword matched against bundle names, resource names, and path fragments",
    )
    max_results: int = Field(
        default=20,
        description="Maximum number of matched resources to return, range: 1-200",
    )
    include_path_samples: bool = Field(
        default=False,
        description="Whether to list a few immediate child entries for local directories",
    )
    sample_limit: int = Field(
        default=5,
        description="Maximum number of child entries to show when include_path_samples is enabled, range: 1-20",
    )


class AssetBundleLinkTool(BaseTool):
    name: str = "assetbundle_link"
    description: str = (
        "Discover asset bundles and resource links for the current business unit. "
        "It can locate local volume paths, external table metadata, and bundle definitions "
        "without exposing sensitive credentials."
    )
    args_schema: Type[BaseModel] = AssetBundleLinkInput

    _business_unit_path: Optional[str] = None
    _asset_bundles: Optional[List[Any]] = None

    def _run(
        self,
        mode: str = "auto",
        bundle_name: Optional[str] = None,
        bundle_type: Optional[str] = None,
        asset_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_results: int = 20,
        include_path_samples: bool = False,
        sample_limit: int = 5,
    ) -> str:
        return self._link_assets(
            mode=mode,
            bundle_name=bundle_name,
            bundle_type=bundle_type,
            asset_type=asset_type,
            keyword=keyword,
            max_results=max_results,
            include_path_samples=include_path_samples,
            sample_limit=sample_limit,
        )

    async def _arun(
        self,
        mode: str = "auto",
        bundle_name: Optional[str] = None,
        bundle_type: Optional[str] = None,
        asset_type: Optional[str] = None,
        keyword: Optional[str] = None,
        max_results: int = 20,
        include_path_samples: bool = False,
        sample_limit: int = 5,
    ) -> str:
        return await asyncio.to_thread(
            self._link_assets,
            mode,
            bundle_name,
            bundle_type,
            asset_type,
            keyword,
            max_results,
            include_path_samples,
            sample_limit,
        )

    def _link_assets(
        self,
        mode: str,
        bundle_name: Optional[str],
        bundle_type: Optional[str],
        asset_type: Optional[str],
        keyword: Optional[str],
        max_results: int,
        include_path_samples: bool,
        sample_limit: int,
    ) -> str:
        normalized_mode = self._resolve_mode(mode=mode, bundle_name=bundle_name, asset_type=asset_type, keyword=keyword)
        normalized_asset_type = self._normalize_asset_type(asset_type)
        normalized_bundle_type = (bundle_type or "").strip().lower() or None
        normalized_bundle_name = (bundle_name or "").strip() or None
        normalized_keyword = (keyword or "").strip().lower() or None
        max_results = max(1, min(int(max_results), 200))
        sample_limit = max(1, min(int(sample_limit), 20))

        bundles = self._load_bundle_records()
        if not bundles:
            return "No asset bundles are available for the current business unit."

        logger.info(
            "Running assetbundle_link: mode=%s bundle_name=%s bundle_type=%s asset_type=%s keyword=%s bundles=%d",
            normalized_mode,
            normalized_bundle_name,
            normalized_bundle_type,
            normalized_asset_type,
            normalized_keyword,
            len(bundles),
        )

        warnings: List[str] = []
        sections: List[str] = []
        matched_items = 0
        matched_bundle_count = 0

        for bundle in bundles:
            if not self._bundle_matches(
                bundle,
                bundle_name=normalized_bundle_name,
                bundle_type=normalized_bundle_type,
            ):
                continue

            section_lines: List[str] = []
            if normalized_mode == "overview":
                section_lines = self._build_overview_section(bundle)
                if normalized_keyword and not self._matches_text_blob(normalized_keyword, section_lines):
                    continue
                matched_bundle_count += 1
            else:
                section_lines, section_match_count, section_warnings = self._build_resource_section(
                    bundle,
                    asset_type=normalized_asset_type,
                    keyword=normalized_keyword,
                    remaining=max_results - matched_items,
                    include_path_samples=include_path_samples,
                    sample_limit=sample_limit,
                )
                warnings.extend(section_warnings)
                if section_match_count <= 0:
                    continue
                matched_bundle_count += 1
                matched_items += section_match_count

            if section_lines:
                sections.append("\n".join(section_lines))

            if normalized_mode == "resource" and matched_items >= max_results:
                break

        if not sections:
            return self._build_empty_result(
                mode=normalized_mode,
                bundle_name=normalized_bundle_name,
                bundle_type=normalized_bundle_type,
                asset_type=normalized_asset_type,
                keyword=normalized_keyword,
            )

        lines = [
            f"Asset bundle link results for `{self._display_business_unit_root()}`",
            f"- Mode: `{normalized_mode}`",
            f"- Bundle matches: {matched_bundle_count}",
        ]
        if normalized_mode == "resource":
            lines.append(f"- Resource matches: {matched_items}")
            if matched_items >= max_results:
                lines.append(f"- Result limit reached: {max_results}")
        if normalized_bundle_name:
            lines.append(f"- Bundle filter: `{normalized_bundle_name}`")
        if normalized_bundle_type:
            lines.append(f"- Bundle type filter: `{normalized_bundle_type}`")
        if normalized_asset_type:
            lines.append(f"- Asset type filter: `{normalized_asset_type}`")
        if normalized_keyword:
            lines.append(f"- Keyword: `{normalized_keyword}`")

        if warnings:
            deduplicated = []
            seen = set()
            for warning in warnings:
                if warning not in seen:
                    seen.add(warning)
                    deduplicated.append(warning)
            lines.append("")
            lines.append("Warnings:")
            for warning in deduplicated:
                lines.append(f"- {warning}")

        lines.append("")
        lines.append("\n\n".join(sections))
        return "\n".join(lines)

    def _resolve_mode(
        self,
        *,
        mode: str,
        bundle_name: Optional[str],
        asset_type: Optional[str],
        keyword: Optional[str],
    ) -> str:
        normalized = (mode or "auto").strip().lower()
        if normalized not in _SUPPORTED_MODES:
            normalized = "auto"
        if normalized == "auto":
            if bundle_name or asset_type or keyword:
                return "resource"
            return "overview"
        return normalized

    def _normalize_asset_type(self, asset_type: Optional[str]) -> Optional[str]:
        normalized = (asset_type or "").strip().lower() or None
        if normalized is None:
            return None
        if normalized.endswith("s") and normalized[:-1] in _SUPPORTED_ASSET_TYPES:
            normalized = normalized[:-1]
        if normalized not in _SUPPORTED_ASSET_TYPES:
            return None
        return normalized

    def _load_bundle_records(self) -> List[Dict[str, Any]]:
        loaded: List[Dict[str, Any]] = []
        for raw_bundle in list(self._asset_bundles or []):
            bundle = self._normalize_bundle_record(raw_bundle)
            if bundle is not None:
                loaded.append(bundle)

        if loaded:
            return sorted(loaded, key=lambda item: item["bundle_name"])

        bundles_root = self._get_asset_bundles_root()
        if bundles_root is None or not bundles_root.exists():
            return []

        discovered: List[Dict[str, Any]] = []
        for bundle_dir in sorted(bundles_root.iterdir()):
            if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
                continue
            bundle_yaml = bundle_dir / ASSET_BUNDLE_CONFIG_FILE
            if not bundle_yaml.exists():
                continue
            payload = self._read_yaml(bundle_yaml)
            if payload is None:
                continue
            discovered.append(
                {
                    "bundle_name": bundle_dir.name,
                    "bundle_type": str(payload.get("bundle_type") or "local").strip().lower() or "local",
                    "bundle_path": str(bundle_dir.resolve()),
                    "mount_path": f"/{bundle_dir.name}",
                    "volumes": [],
                }
            )

        return discovered

    def _normalize_bundle_record(self, raw_bundle: Any) -> Optional[Dict[str, Any]]:
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

    def _bundle_matches(
        self,
        bundle: Dict[str, Any],
        *,
        bundle_name: Optional[str],
        bundle_type: Optional[str],
    ) -> bool:
        if bundle_name and bundle.get("bundle_name") != bundle_name:
            return False
        if bundle_type and bundle.get("bundle_type") != bundle_type:
            return False
        return True

    def _build_overview_section(self, bundle: Dict[str, Any]) -> List[str]:
        bundle_path = self._bundle_path(bundle)
        bundle_config = self._read_yaml(bundle_path / ASSET_BUNDLE_CONFIG_FILE) or {}
        table_files = self._list_yaml_files(bundle_path / TABLES_DIR)
        volume_files = self._list_yaml_files(bundle_path / VOLUMES_DIR)
        function_dir = bundle_path / FUNCTIONS_DIR
        note_dir = bundle_path / NOTES_DIR

        lines = [
            f"## Bundle `{bundle['bundle_name']}`",
            f"- Type: `{bundle['bundle_type']}`",
            f"- Definition: `{self._display_path(bundle_path / ASSET_BUNDLE_CONFIG_FILE)}`",
            f"- Mount path: `{bundle.get('mount_path')}`",
            f"- Tables: {len(table_files)}",
            f"- Volumes: {len(volume_files)}",
            f"- Functions directory: {'available' if function_dir.exists() else 'missing'}",
            f"- Notes directory: {'available' if note_dir.exists() else 'missing'}",
        ]

        connection_summary = self._summarize_connection(bundle_config)
        if connection_summary:
            lines.append(f"- Connection summary: {connection_summary}")
        return lines

    def _build_resource_section(
        self,
        bundle: Dict[str, Any],
        *,
        asset_type: Optional[str],
        keyword: Optional[str],
        remaining: int,
        include_path_samples: bool,
        sample_limit: int,
    ) -> tuple[List[str], int, List[str]]:
        if remaining <= 0:
            return [], 0, []

        bundle_path = self._bundle_path(bundle)
        warnings: List[str] = []
        resource_blocks: List[List[str]] = []
        match_count = 0

        if asset_type in (None, "bundle"):
            bundle_block = self._build_bundle_block(bundle, keyword=keyword)
            if bundle_block is not None:
                resource_blocks.append(bundle_block)
                match_count += 1

        if match_count < remaining and asset_type in (None, "volume"):
            volume_blocks, volume_warnings = self._build_volume_blocks(
                bundle,
                keyword=keyword,
                limit=remaining - match_count,
                include_path_samples=include_path_samples,
                sample_limit=sample_limit,
            )
            resource_blocks.extend(volume_blocks)
            match_count += len(volume_blocks)
            warnings.extend(volume_warnings)

        if match_count < remaining and asset_type in (None, "table"):
            table_blocks, table_warnings = self._build_table_blocks(
                bundle,
                keyword=keyword,
                limit=remaining - match_count,
            )
            resource_blocks.extend(table_blocks)
            match_count += len(table_blocks)
            warnings.extend(table_warnings)

        if match_count < remaining and asset_type in (None, "function"):
            function_block = self._build_directory_block(bundle_path / FUNCTIONS_DIR, bundle, resource_type="function", keyword=keyword)
            if function_block is not None:
                resource_blocks.append(function_block)
                match_count += 1

        if match_count < remaining and asset_type in (None, "note"):
            note_block = self._build_directory_block(bundle_path / NOTES_DIR, bundle, resource_type="note", keyword=keyword)
            if note_block is not None:
                resource_blocks.append(note_block)
                match_count += 1

        if not resource_blocks:
            return [], 0, warnings

        section_lines = [
            f"## Bundle `{bundle['bundle_name']}`",
            f"- Type: `{bundle['bundle_type']}`",
            f"- Definition: `{self._display_path(bundle_path / ASSET_BUNDLE_CONFIG_FILE)}`",
            "",
        ]
        for index, block in enumerate(resource_blocks):
            if index:
                section_lines.append("")
            section_lines.extend(block)
        return section_lines, match_count, warnings

    def _build_bundle_block(self, bundle: Dict[str, Any], keyword: Optional[str]) -> Optional[List[str]]:
        bundle_path = self._bundle_path(bundle)
        bundle_yaml = bundle_path / ASSET_BUNDLE_CONFIG_FILE
        payload = self._read_yaml(bundle_yaml) or {}
        connection_summary = self._summarize_connection(payload)
        content_blob = "\n".join([
            bundle["bundle_name"],
            bundle.get("bundle_type", ""),
            str(bundle_yaml),
            str(bundle.get("mount_path") or ""),
            connection_summary,
        ])
        if keyword and keyword not in content_blob.lower():
            return None

        lines = [
            "### Asset bundle",
            f"- Name: `{bundle['bundle_name']}`",
            f"- Bundle type: `{bundle['bundle_type']}`",
            f"- Definition: `{self._display_path(bundle_yaml)}`",
            f"- Mount path: `{bundle.get('mount_path')}`",
            "- Suggested next step: inspect linked resources or call `file_read` on the definition file.",
        ]
        if connection_summary:
            lines.append(f"- Connection summary: {connection_summary}")
        return lines

    def _build_volume_blocks(
        self,
        bundle: Dict[str, Any],
        *,
        keyword: Optional[str],
        limit: int,
        include_path_samples: bool,
        sample_limit: int,
    ) -> tuple[List[List[str]], List[str]]:
        warnings: List[str] = []
        blocks: List[List[str]] = []

        for volume_file in self._iter_volume_files(bundle):
            if len(blocks) >= limit:
                break
            payload = self._read_yaml(volume_file)
            if payload is None:
                warnings.append(f"Skipped unreadable volume config: {self._display_path(volume_file)}")
                continue

            baseinfo = payload.get("baseinfo") or {}
            volume_name = str(baseinfo.get("name") or volume_file.stem).strip() or volume_file.stem
            display_name = str(baseinfo.get("display_name") or volume_name).strip() or volume_name
            description = str(baseinfo.get("description") or "").strip()
            volume_type = str(payload.get("volume_type") or "local").strip().lower() or "local"
            storage_location = str(payload.get("storage_location") or "").strip()
            resolved_target = self._resolve_target_path(storage_location) if storage_location else None
            target_status = self._describe_target_status(resolved_target)

            content_blob = "\n".join(
                [
                    volume_name,
                    display_name,
                    description,
                    volume_type,
                    storage_location,
                    str(volume_file),
                ]
            )
            if keyword and keyword not in content_blob.lower():
                continue

            block = [
                f"### Volume `{volume_name}`",
                f"- Display name: `{display_name}`",
                f"- Volume type: `{volume_type}`",
                f"- Definition: `{self._display_path(volume_file)}`",
                f"- Source bundle: `{bundle['bundle_name']}`",
            ]
            if description:
                block.append(f"- Description: {description}")
            if storage_location:
                block.append(f"- Linked path: `{resolved_target}`")
                block.append(f"- Path status: {target_status}")
                block.append("- Suggested next step: use `file_search` or `file_read` against the linked path.")
                if include_path_samples:
                    block.extend(self._build_path_samples(resolved_target, sample_limit))
            else:
                block.append("- Linked path: not configured")
                block.append("- Path status: unavailable")
            blocks.append(block)

        return blocks, warnings

    def _build_table_blocks(
        self,
        bundle: Dict[str, Any],
        *,
        keyword: Optional[str],
        limit: int,
    ) -> tuple[List[List[str]], List[str]]:
        warnings: List[str] = []
        blocks: List[List[str]] = []
        tables_dir = self._bundle_path(bundle) / TABLES_DIR

        for table_file in sorted(tables_dir.glob("*.yaml")):
            if len(blocks) >= limit:
                break
            if table_file.name.startswith("."):
                continue
            payload = self._read_yaml(table_file)
            if payload is None:
                warnings.append(f"Skipped unreadable table metadata: {self._display_path(table_file)}")
                continue

            baseinfo = payload.get("baseinfo") or {}
            table_name = str(baseinfo.get("name") or table_file.stem).strip() or table_file.stem
            display_name = str(baseinfo.get("display_name") or table_name).strip() or table_name
            description = str(baseinfo.get("description") or "").strip()
            schema_name = str(payload.get("schema_name") or "").strip()
            columns = payload.get("columns") or []
            primary_keys = payload.get("primary_keys") or []

            content_blob = "\n".join(
                [
                    table_name,
                    display_name,
                    description,
                    schema_name,
                    str(table_file),
                ]
            )
            if keyword and keyword not in content_blob.lower():
                continue

            block = [
                f"### Table `{table_name}`",
                f"- Display name: `{display_name}`",
                f"- Definition: `{self._display_path(table_file)}`",
                f"- Source bundle: `{bundle['bundle_name']}`",
            ]
            if description:
                block.append(f"- Description: {description}")
            if schema_name:
                block.append(f"- Schema: `{schema_name}`")
            block.append(f"- Column count: {len(columns)}")
            block.append(f"- Primary keys: {', '.join(f'`{key}`' for key in primary_keys) if primary_keys else 'none'}")
            block.append("- Suggested next step: use schema-aware analysis or the data-analysis handoff for structured queries.")
            blocks.append(block)

        return blocks, warnings

    def _build_directory_block(
        self,
        directory: Path,
        bundle: Dict[str, Any],
        *,
        resource_type: str,
        keyword: Optional[str],
    ) -> Optional[List[str]]:
        exists = directory.exists() and directory.is_dir()
        content_blob = "\n".join([resource_type, str(directory), bundle["bundle_name"]])
        if keyword and keyword not in content_blob.lower():
            return None
        if not exists:
            return None
        return [
            f"### {resource_type.title()} directory",
            f"- Source bundle: `{bundle['bundle_name']}`",
            f"- Directory: `{self._display_path(directory)}`",
            "- Status: available",
            "- Suggested next step: use `file_search` to locate a specific file in this directory.",
        ]

    def _iter_volume_files(self, bundle: Dict[str, Any]) -> List[Path]:
        files: List[Path] = []
        for volume in bundle.get("volumes") or []:
            if not isinstance(volume, dict):
                continue
            file_path = str(volume.get("file_path") or "").strip()
            if not file_path:
                continue
            files.append(Path(os.path.expanduser(file_path)).resolve())

        if files:
            return sorted({path for path in files if path.name.endswith(".yaml")})

        volumes_dir = self._bundle_path(bundle) / VOLUMES_DIR
        return self._list_yaml_files(volumes_dir)

    def _list_yaml_files(self, directory: Path) -> List[Path]:
        if not directory.exists() or not directory.is_dir():
            return []
        return [
            path
            for path in sorted(directory.glob("*.yaml"))
            if path.is_file() and not path.name.startswith(".")
        ]

    def _read_yaml(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                payload = yaml.safe_load(file) or {}
        except Exception as exc:
            logger.warning("Failed to read YAML file %s: %s", file_path, exc)
            return None
        if not isinstance(payload, dict):
            logger.warning("Skipping non-object YAML payload: %s", file_path)
            return None
        return payload

    def _summarize_connection(self, bundle_config: Dict[str, Any]) -> str:
        connection = bundle_config.get("connection")
        if not isinstance(connection, dict):
            return ""
        connection_type = str(connection.get("type") or "unknown").strip() or "unknown"
        host = str(connection.get("host") or "").strip()
        port = connection.get("port")
        db_name = str(connection.get("db_name") or connection.get("database") or "").strip()
        fragments = [connection_type]
        if host:
            host_fragment = host
            if port not in (None, ""):
                host_fragment = f"{host}:{port}"
            fragments.append(f"host={host_fragment}")
        if db_name:
            fragments.append(f"db={db_name}")
        return ", ".join(fragments)

    def _resolve_target_path(self, raw_path: str) -> Path:
        return Path(os.path.expanduser(raw_path)).resolve()

    def _describe_target_status(self, target_path: Optional[Path]) -> str:
        if target_path is None:
            return "missing target path"
        if not target_path.exists():
            return "missing"
        if target_path.is_dir():
            return "exists (directory)"
        if target_path.is_file():
            return "exists (file)"
        return "exists"

    def _build_path_samples(self, target_path: Path, sample_limit: int) -> List[str]:
        if not target_path.exists() or not target_path.is_dir():
            return []
        try:
            children = sorted(target_path.iterdir(), key=lambda item: item.name.lower())[:sample_limit]
        except Exception as exc:
            logger.warning("Failed to list directory sample for %s: %s", target_path, exc)
            return [f"- Path sample error: {exc}"]
        if not children:
            return ["- Path samples: directory is empty"]

        lines = ["- Path samples:"]
        for child in children:
            suffix = "/" if child.is_dir() else ""
            lines.append(f"  - `{child.name}{suffix}`")
        return lines

    def _matches_text_blob(self, keyword: str, lines: Sequence[str]) -> bool:
        blob = "\n".join(lines).lower()
        return keyword in blob

    def _build_empty_result(
        self,
        *,
        mode: str,
        bundle_name: Optional[str],
        bundle_type: Optional[str],
        asset_type: Optional[str],
        keyword: Optional[str],
    ) -> str:
        filters: List[str] = []
        if bundle_name:
            filters.append(f"bundle_name={bundle_name}")
        if bundle_type:
            filters.append(f"bundle_type={bundle_type}")
        if asset_type:
            filters.append(f"asset_type={asset_type}")
        if keyword:
            filters.append(f"keyword={keyword}")
        filter_text = ", ".join(filters) if filters else "no filters"
        return (
            "No asset bundle links matched the current request. "
            f"Mode: {mode}. Filters: {filter_text}."
        )

    def _bundle_path(self, bundle: Dict[str, Any]) -> Path:
        return Path(os.path.expanduser(str(bundle["bundle_path"]))).resolve()

    def _get_asset_bundles_root(self) -> Optional[Path]:
        business_unit_path = self._get_business_unit_path()
        if business_unit_path is None:
            return None
        return business_unit_path / ASSET_BUNDLES_DIR

    def _get_business_unit_path(self) -> Optional[Path]:
        if self._business_unit_path:
            return Path(os.path.expanduser(self._business_unit_path)).resolve()
        first_bundle = next(iter(self._asset_bundles or []), None)
        if first_bundle is None:
            return None
        normalized = self._normalize_bundle_record(first_bundle)
        if normalized is None:
            return None
        return self._bundle_path(normalized).parent.parent

    def _display_business_unit_root(self) -> str:
        business_unit_path = self._get_business_unit_path()
        return str(business_unit_path) if business_unit_path is not None else "<unknown business unit>"

    def _display_path(self, path: Path) -> str:
        resolved_path = path.resolve()
        business_unit_path = self._get_business_unit_path()
        if business_unit_path is not None:
            try:
                relative = resolved_path.relative_to(business_unit_path)
                return "." if str(relative) == "." else f"./{relative.as_posix()}"
            except ValueError:
                pass
        return str(resolved_path)



def create_assetbundle_link_tool(
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
) -> AssetBundleLinkTool:
    tool = AssetBundleLinkTool()
    tool._business_unit_path = business_unit_path
    tool._asset_bundles = list(asset_bundles or [])
    return tool


__all__ = [
    "AssetBundleLinkInput",
    "AssetBundleLinkTool",
    "create_assetbundle_link_tool",
]
