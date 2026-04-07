"""LangChain tools for the text2sql sub-agent.

Two tools are exposed:
1. ``DuckDBQueryTool`` — execute read-only SQL via DuckDB.
2. ``ListTableMetadataTool`` — inspect external AssetBundle table schemas.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from .metadata import TableMetadataLoader
from .service import Text2SQLDuckDBService

logger = logging.getLogger(__name__)


class DuckDBQueryInput(BaseModel):
    """Input schema for the DuckDB query tool."""

    sql: str = Field(
        description=(
            "Read-only SQL query to execute against attached databases. "
            "Must start with SELECT / WITH / SHOW / DESCRIBE / PRAGMA / EXPLAIN. "
            "Use <attached_db_name>.<table_name> to reference tables."
        )
    )
    max_rows: int = Field(
        default=200,
        description="Maximum number of rows to return (1-1000, default 200)",
    )


class DuckDBQueryTool(BaseTool):
    """Execute read-only SQL against remote databases via DuckDB."""

    name: str = "duckdb_query"
    description: str = (
        "Execute a read-only SQL query against attached external databases via DuckDB. "
        "Returns query results as a Markdown table. Use list_table_metadata first "
        "to discover available tables and columns."
    )
    args_schema: Type[BaseModel] = DuckDBQueryInput

    _service: Optional[Text2SQLDuckDBService] = PrivateAttr(default=None)

    def __init__(self, *, service: Optional[Text2SQLDuckDBService] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._service = service

    def _ensure_service(self) -> Text2SQLDuckDBService:
        if self._service is None:
            raise RuntimeError("DuckDB service is not initialised")
        return self._service

    def _run(self, sql: str, max_rows: int = 200) -> str:
        service = self._ensure_service()
        result = service.execute_query(sql, max_rows=max_rows)
        return _format_query_result(result)

    async def _arun(self, sql: str, max_rows: int = 200) -> str:
        return await asyncio.to_thread(self._run, sql, max_rows)


class ListTableMetadataInput(BaseModel):
    """Input schema for the table metadata listing tool."""

    bundle_name: Optional[str] = Field(
        default=None,
        description="Filter by AssetBundle name. Omit to list tables from all external bundles.",
    )
    table_name: Optional[str] = Field(
        default=None,
        description=(
            "If provided, return the full column-level schema for this specific table. "
            "Requires bundle_name to be set as well."
        ),
    )


class ListTableMetadataTool(BaseTool):
    """List available tables and their schemas from external AssetBundles."""

    name: str = "list_table_metadata"
    description: str = (
        "Discover available database tables and their schemas. "
        "Call with no arguments to list all tables. "
        "Call with bundle_name and table_name to get detailed column definitions."
    )
    args_schema: Type[BaseModel] = ListTableMetadataInput

    _loader: Optional[TableMetadataLoader] = PrivateAttr(default=None)

    def __init__(self, *, loader: Optional[TableMetadataLoader] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loader = loader

    def _ensure_loader(self) -> TableMetadataLoader:
        if self._loader is None:
            raise RuntimeError("Table metadata loader is not initialised")
        return self._loader

    def _run(
        self,
        bundle_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> str:
        loader = self._ensure_loader()

        if bundle_name and table_name:
            schema = loader.get_table_schema(bundle_name, table_name)
            if schema is None:
                return f"Table '{table_name}' not found in bundle '{bundle_name}'."
            return _format_table_schema(schema)

        tables = loader.list_tables(bundle_name=bundle_name)
        if not tables:
            return "No external tables found."
        return _format_table_list(tables)

    async def _arun(
        self,
        bundle_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> str:
        return await asyncio.to_thread(self._run, bundle_name, table_name)


def _markdown_cell(value: Any) -> str:
    """Escape cell values for Markdown tables."""
    if value is None:
        rendered = ""
    elif isinstance(value, (dict, list, tuple, set)):
        rendered = json.dumps(value, ensure_ascii=False, default=str)
    else:
        rendered = str(value)
    return rendered.replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def _format_query_result(result: dict) -> str:
    """Convert a query result dict to a Markdown response."""
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"Query failed: {error}"

    columns: List[str] = result.get("columns", [])
    rows: List[dict] = result.get("rows", [])
    row_count = result.get("row_count", 0)
    truncated = result.get("truncated", False)
    elapsed = result.get("execution_ms", 0)

    if not columns:
        return f"Query executed successfully ({elapsed:.1f}ms), no result columns."

    lines = ["| " + " | ".join(_markdown_cell(column) for column in columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

    if not rows:
        footer = f"_No rows returned ({elapsed:.1f}ms)_"
        return "\n".join(lines + ["", footer])

    for row in rows:
        cells = [_markdown_cell(row.get(column, "")) for column in columns]
        lines.append("| " + " | ".join(cells) + " |")

    footer = f"_{row_count} row(s) returned ({elapsed:.1f}ms)"
    if truncated:
        footer += ", results truncated"
    footer += "_"
    return "\n".join(lines + [footer])


def _format_table_list(tables: List[dict]) -> str:
    """Format a compact table list as Markdown."""
    lines = ["| Bundle | Table | Description | Columns | Primary Keys |"]
    lines.append("| --- | --- | --- | --- | --- |")
    for table in tables:
        primary_keys = ", ".join(table.get("primary_keys", []))
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(table.get("bundle_name", "")),
                    _markdown_cell(table.get("table_name", "")),
                    _markdown_cell(table.get("description", "")),
                    _markdown_cell(table.get("column_count", 0)),
                    _markdown_cell(primary_keys),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _format_table_schema(schema: dict) -> str:
    """Format a full table schema as Markdown."""
    parts = [f"## {schema['bundle_name']}.{schema['table_name']}", ""]
    if schema.get("description"):
        parts.append(f"_{_markdown_cell(schema['description'])}_")
        parts.append("")

    primary_keys = ", ".join(schema.get("primary_keys", []))
    if primary_keys:
        parts.append(f"**Primary keys**: {_markdown_cell(primary_keys)}")
        parts.append("")

    if schema.get("row_count") is not None:
        parts.append(f"**Approximate row count**: {_markdown_cell(schema['row_count'])}")
        parts.append("")

    columns = schema.get("columns", [])
    if not columns:
        parts.append("_No column information available._")
        return "\n".join(parts)

    parts.append("| Column | Type | Nullable | PK | Comment |")
    parts.append("| --- | --- | --- | --- | --- |")
    for column in columns:
        parts.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(column.get("name", "")),
                    _markdown_cell(column.get("data_type", "")),
                    "YES" if column.get("nullable") else "NO",
                    "Y" if column.get("is_primary_key") else "",
                    _markdown_cell(column.get("comment", "")),
                ]
            )
            + " |"
        )

    return "\n".join(parts)


__all__ = [
    "DuckDBQueryInput",
    "DuckDBQueryTool",
    "ListTableMetadataInput",
    "ListTableMetadataTool",
]
