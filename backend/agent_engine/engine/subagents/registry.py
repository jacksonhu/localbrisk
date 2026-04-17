"""Built-in subagent registry and builder helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


_TEXT2SQL_SYSTEM_PROMPT = """You are the Text2SQL data-retrieval sub-assistant.
You have two dedicated tools:
  - `list_table_metadata` — discover available tables and their column schemas.
  - `duckdb_query` — execute read-only SQL via DuckDB against attached databases.

Workflow:
1) Call `list_table_metadata` (no args) to see all available tables.
2) Call `list_table_metadata` with bundle_name + table_name to get detailed column schemas.
3) Compose a precise SQL query and execute it with `duckdb_query`.
4) Summarise the results for the user, including key findings and the SQL used.

Rules:
- Table references in SQL must use the pattern `<bundle_name>.<table_name>`.
- If a bundle name contains special characters, wrap it with double quotes in SQL.
- Only SELECT / WITH / SHOW / DESCRIBE / PRAGMA / EXPLAIN statements are allowed.
- Never execute destructive SQL (DROP / TRUNCATE / DELETE / UPDATE / INSERT).
- When uncertain about column names, always check metadata first.
- Return at most 200 rows; add LIMIT to large queries.
- Always respond in the same language the user uses."""

SubagentDefinition = Dict[str, Any]
SubagentBuilder = Callable[["BuiltinSubagentContext"], Optional["SubagentBuildResult"]]


@dataclass(frozen=True)
class BuiltinSubagentContext:
    """Normalized build context shared by all built-in subagent builders."""

    parent_model: Any
    parent_tools: List[Any]
    business_unit_path: Optional[str] = None
    asset_bundles: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SubagentBuildResult:
    """One built subagent definition together with any owned resources."""

    definition: SubagentDefinition
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuiltinSubagentCollection:
    """Aggregated built-in subagent definitions and shared resource handles."""

    subagents: List[SubagentDefinition]
    resources: Dict[str, Any] = field(default_factory=dict)


class SubagentRegistry:
    """Ordered registry for built-in subagent builder functions."""

    def __init__(self) -> None:
        self._builders: Dict[str, SubagentBuilder] = {}

    def register(self, name: str, builder: SubagentBuilder, *, replace: bool = False) -> None:
        """Register one named subagent builder."""
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("Subagent builder name cannot be empty")
        if not callable(builder):
            raise TypeError("Subagent builder must be callable")
        if normalized_name in self._builders and not replace:
            raise ValueError(f"Subagent builder already registered: {normalized_name}")

        self._builders[normalized_name] = builder
        logger.debug("Registered subagent builder: %s", normalized_name)

    def list_names(self) -> List[str]:
        """Return registered builder names in build order."""
        return list(self._builders.keys())

    def build_all(self, context: BuiltinSubagentContext) -> List[SubagentBuildResult]:
        """Build every registered subagent using the same normalized context."""
        results: List[SubagentBuildResult] = []
        for builder_name, builder in self._builders.items():
            build_result = builder(context)
            if build_result is None:
                logger.debug("Subagent builder skipped: %s", builder_name)
                continue
            self._validate_result(builder_name, build_result)
            results.append(build_result)

        logger.info(
            "Built %d subagent(s): %s",
            len(results),
            [result.definition["name"] for result in results],
        )
        return results

    @staticmethod
    def _validate_result(builder_name: str, result: SubagentBuildResult) -> None:
        """Validate that one builder returned a stable, self-consistent payload."""
        if not isinstance(result.definition, dict):
            raise TypeError(f"Subagent builder '{builder_name}' must return a dict definition")

        built_name = str(result.definition.get("name") or "").strip()
        if not built_name:
            raise ValueError(f"Subagent builder '{builder_name}' returned a definition without a name")
        if built_name != builder_name:
            raise ValueError(
                f"Subagent builder '{builder_name}' returned mismatched definition name '{built_name}'"
            )


def _as_dict_subagent(
    *,
    name: str,
    description: str,
    system_prompt: str,
    tools: Optional[List[Any]] = None,
    model: Optional[Any] = None,
) -> SubagentDefinition:
    """Build one dict-style subagent definition."""
    payload: SubagentDefinition = {
        "name": name,
        "description": description,
        "system_prompt": system_prompt,
    }
    if tools is not None:
        payload["tools"] = tools
    if model is not None:
        payload["model"] = model
    return payload


def _normalise_bundle_config(bundle: Any) -> Dict[str, Any]:
    """Normalize one asset bundle config into a stable plain dict."""
    if isinstance(bundle, dict):
        source = bundle
    else:
        source = {
            "bundle_name": getattr(bundle, "bundle_name", ""),
            "bundle_type": getattr(bundle, "bundle_type", ""),
            "bundle_path": getattr(bundle, "bundle_path", ""),
            "mount_path": getattr(bundle, "mount_path", ""),
            "volumes": getattr(bundle, "volumes", []),
        }

    raw_volumes = source.get("volumes") or []
    volumes = raw_volumes if isinstance(raw_volumes, list) else [raw_volumes]
    return {
        "bundle_name": str(source.get("bundle_name") or ""),
        "bundle_type": str(source.get("bundle_type") or ""),
        "bundle_path": str(source.get("bundle_path") or ""),
        "mount_path": str(source.get("mount_path") or ""),
        "volumes": volumes,
    }


def _normalise_bundle_configs(asset_bundles: Optional[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Normalize AssetBundle config inputs before they reach builders."""
    if not asset_bundles:
        return []
    return [_normalise_bundle_config(bundle) for bundle in asset_bundles]


def _resolve_table_analysis_tools(context: BuiltinSubagentContext) -> tuple[List[Any], Optional[Any]]:
    """Resolve dedicated tools for the table analysis subagent when possible."""
    if not context.business_unit_path:
        logger.debug("business_unit_path not provided, data_analysis_agent will use parent tools")
        return context.parent_tools, None

    try:
        from .text2sql import create_text2sql_tools

        text2sql_tools, text2sql_service = create_text2sql_tools(
            business_unit_path=context.business_unit_path,
            asset_bundles=context.asset_bundles,
        )
        if text2sql_tools:
            logger.info(
                "Resolved dedicated Text2SQL tools for data_analysis_agent: %d tool(s), %d attached source(s)",
                len(text2sql_tools),
                len(text2sql_service.attached_sources) if text2sql_service else 0,
            )
            return text2sql_tools, text2sql_service

        logger.warning(
            "Text2SQL tool factory returned no tools for data_analysis_agent, falling back to parent tools"
        )
    except Exception as exc:
        logger.warning(
            "Failed to create Text2SQL tools for data_analysis_agent, falling back to parent tools: %s",
            exc,
        )

    return context.parent_tools, None


def _build_table_analysis_subagent(context: BuiltinSubagentContext) -> SubagentBuildResult:
    """Build the built-in table analysis subagent."""
    tools, text2sql_service = _resolve_table_analysis_tools(context)
    resources: Dict[str, Any] = {}
    if text2sql_service is not None:
        resources["text2sql_service"] = text2sql_service

    return SubagentBuildResult(
        definition=_as_dict_subagent(
            name="data_analysis_agent",
            description=(
                "data analysis across local CSV/Excel files and remote databases, "
                "including joint querying and result interpretation"
            ),
            system_prompt=_TEXT2SQL_SYSTEM_PROMPT,
            tools=tools,
            model=context.parent_model,
        ),
        resources=resources,
    )


def create_default_subagent_registry() -> SubagentRegistry:
    """Create a fresh registry populated with the built-in subagent builders."""
    registry = SubagentRegistry()
    registry.register("data_analysis_agent", _build_table_analysis_subagent)
    return registry


_BUILTIN_SUBAGENT_REGISTRY: Optional[SubagentRegistry] = None


def get_builtin_subagent_registry() -> SubagentRegistry:
    """Return the process-wide built-in subagent registry singleton."""
    global _BUILTIN_SUBAGENT_REGISTRY
    if _BUILTIN_SUBAGENT_REGISTRY is None:
        _BUILTIN_SUBAGENT_REGISTRY = create_default_subagent_registry()
    return _BUILTIN_SUBAGENT_REGISTRY


def build_builtin_subagents(
    *,
    parent_model: Any,
    parent_tools: List[Any],
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
    registry: Optional[SubagentRegistry] = None,
) -> BuiltinSubagentCollection:
    """Build built-in subagents and aggregate any returned resources."""
    context = BuiltinSubagentContext(
        parent_model=parent_model,
        parent_tools=parent_tools,
        business_unit_path=business_unit_path,
        asset_bundles=_normalise_bundle_configs(asset_bundles),
    )

    results = (registry or get_builtin_subagent_registry()).build_all(context)
    subagents: List[SubagentDefinition] = []
    resources: Dict[str, Any] = {}

    for result in results:
        subagents.append(result.definition)
        for resource_name, resource in result.resources.items():
            if resource is None:
                continue
            if resource_name in resources and resources[resource_name] is not resource:
                logger.warning(
                    "Overwriting subagent resource '%s' while aggregating built-in subagents",
                    resource_name,
                )
            resources[resource_name] = resource

    return BuiltinSubagentCollection(subagents=subagents, resources=resources)


def create_builtin_subagents(
    *,
    parent_model: Any,
    parent_tools: List[Any],
    business_unit_path: Optional[str] = None,
    asset_bundles: Optional[Sequence[Any]] = None,
    registry: Optional[SubagentRegistry] = None,
) -> tuple[List[Any], Optional[Any]]:
    """Compatibility wrapper returning built-in subagents and Text2SQL service."""
    collection = build_builtin_subagents(
        parent_model=parent_model,
        parent_tools=parent_tools,
        business_unit_path=business_unit_path,
        asset_bundles=asset_bundles,
        registry=registry,
    )
    return collection.subagents, collection.resources.get("text2sql_service")


__all__ = [
    "BuiltinSubagentCollection",
    "BuiltinSubagentContext",
    "SubagentBuildResult",
    "SubagentRegistry",
    "build_builtin_subagents",
    "create_builtin_subagents",
    "create_default_subagent_registry",
    "get_builtin_subagent_registry",
]
