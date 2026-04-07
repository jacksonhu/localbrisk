"""Unit tests for the Text2SQL sub-agent helpers."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_text2sql_business_unit(tmp_path: Path) -> Path:
    """Create a temporary BusinessUnit with one external and one local bundle."""
    business_unit_dir = tmp_path / "test_unit"

    external_bundle = business_unit_dir / "asset_bundles" / "sales_bundle"
    external_tables = external_bundle / "tables"
    external_tables.mkdir(parents=True, exist_ok=True)

    with open(external_bundle / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "bundle_type": "external",
                "connection": {
                    "type": "mysql",
                    "host": "127.0.0.1",
                    "port": 3306,
                    "db_name": "sales_db",
                    "username": "demo",
                    "password": "secret",
                },
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    with open(external_tables / "orders.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump(
            {
                "baseinfo": {"name": "orders", "description": "Orders table"},
                "schema_name": "sales_db",
                "primary_keys": ["id"],
                "row_count": 12,
                "columns": [
                    {"name": "id", "data_type": "bigint", "nullable": False, "is_primary_key": True, "comment": "PK"},
                    {"name": "note", "data_type": "varchar", "nullable": True, "is_primary_key": False, "comment": "Contains | and newline\ntext"},
                ],
            },
            file,
            allow_unicode=True,
            sort_keys=False,
        )

    local_bundle = business_unit_dir / "asset_bundles" / "local_docs"
    local_bundle.mkdir(parents=True, exist_ok=True)
    with open(local_bundle / "bundle.yaml", "w", encoding="utf-8") as file:
        yaml.safe_dump({"bundle_type": "local"}, file, allow_unicode=True, sort_keys=False)

    return business_unit_dir


class TestTableMetadataLoader:
    """Metadata loader tests."""

    def test_list_tables_and_get_schema(self, temp_text2sql_business_unit: Path):
        from agent_engine.engine.subagents.text2sql.metadata import TableMetadataLoader

        loader = TableMetadataLoader(str(temp_text2sql_business_unit))

        tables = loader.list_tables()
        assert len(tables) == 1
        assert tables[0]["bundle_name"] == "sales_bundle"
        assert tables[0]["table_name"] == "orders"

        schema = loader.get_table_schema("sales_bundle", "orders")
        assert schema is not None
        assert schema["primary_keys"] == ["id"]
        assert len(schema["columns"]) == 2
        assert schema["columns"][1]["comment"] == "Contains | and newline\ntext"


class TestCreateText2SQLTools:
    """Factory tests."""

    def test_create_text2sql_tools_attaches_only_external_bundles(self, temp_text2sql_business_unit: Path, monkeypatch):
        from agent_engine.engine.subagents.text2sql import create_text2sql_tools

        attached_calls = []

        class FakeService:
            def __init__(self):
                self.attached_sources = {}

            def attach_mysql(self, **kwargs):
                attached_calls.append(("mysql", kwargs))
                self.attached_sources[kwargs["name"]] = "mysql"

            def attach_postgres(self, **kwargs):
                attached_calls.append(("postgresql", kwargs))
                self.attached_sources[kwargs["name"]] = "postgresql"

        monkeypatch.setattr(
            "agent_engine.engine.subagents.text2sql.Text2SQLDuckDBService",
            FakeService,
        )

        tools, service = create_text2sql_tools(
            business_unit_path=str(temp_text2sql_business_unit),
            asset_bundles=[
                {
                    "bundle_name": "sales_bundle",
                    "bundle_type": "external",
                    "bundle_path": str(temp_text2sql_business_unit / "asset_bundles" / "sales_bundle"),
                    "mount_path": "/sales_bundle",
                    "volumes": [],
                },
                {
                    "bundle_name": "local_docs",
                    "bundle_type": "local",
                    "bundle_path": str(temp_text2sql_business_unit / "asset_bundles" / "local_docs"),
                    "mount_path": "/local_docs",
                    "volumes": [],
                },
            ],
        )

        assert [tool.name for tool in tools] == ["duckdb_query", "list_table_metadata"]
        assert len(attached_calls) == 1
        assert attached_calls[0][0] == "mysql"
        assert attached_calls[0][1]["name"] == "sales_bundle"
        assert service.attached_sources == {"sales_bundle": "mysql"}


class TestSqlValidation:
    """Read-only SQL validation tests."""

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM sales_bundle.orders",
            "WITH recent AS (SELECT 1 AS id) SELECT * FROM recent",
            "EXPLAIN SELECT * FROM sales_bundle.orders",
        ],
    )
    def test_validate_read_only_sql_accepts_safe_queries(self, sql: str):
        from agent_engine.engine.subagents.text2sql.service import validate_read_only_sql

        assert validate_read_only_sql(sql) == sql.rstrip("; ")

    @pytest.mark.parametrize(
        "sql, expected_message",
        [
            ("", "must not be empty"),
            ("DELETE FROM sales_bundle.orders", "Only read-only SQL is allowed"),
            ("SELECT 1; DROP TABLE x", "Only a single SQL statement is allowed"),
            ("WITH t AS (SELECT 1) INSERT INTO demo VALUES (1)", "Forbidden SQL keyword detected"),
        ],
    )
    def test_validate_read_only_sql_rejects_unsafe_queries(self, sql: str, expected_message: str):
        from agent_engine.engine.subagents.text2sql.service import validate_read_only_sql

        with pytest.raises(ValueError, match=expected_message):
            validate_read_only_sql(sql)


class TestText2SQLTools:
    """Tool formatting tests."""

    def test_duckdb_query_tool_formats_markdown_safely(self):
        from agent_engine.engine.subagents.text2sql.tools import DuckDBQueryTool

        class FakeService:
            def execute_query(self, sql: str, max_rows: int = 200):
                assert sql == "SELECT note FROM sales_bundle.orders"
                assert max_rows == 2
                return {
                    "success": True,
                    "columns": ["note"],
                    "rows": [{"note": "hello|world\nnext"}],
                    "row_count": 1,
                    "truncated": False,
                    "execution_ms": 1.2,
                }

        tool = DuckDBQueryTool(service=FakeService())
        result = tool._run("SELECT note FROM sales_bundle.orders", max_rows=2)

        assert "hello\\|world<br>next" in result
        assert "1 row(s) returned" in result

    def test_list_table_metadata_tool_returns_missing_message(self, temp_text2sql_business_unit: Path):
        from agent_engine.engine.subagents.text2sql.metadata import TableMetadataLoader
        from agent_engine.engine.subagents.text2sql.tools import ListTableMetadataTool

        loader = TableMetadataLoader(str(temp_text2sql_business_unit))
        tool = ListTableMetadataTool(loader=loader)

        result = tool._run(bundle_name="sales_bundle", table_name="missing_table")
        assert result == "Table 'missing_table' not found in bundle 'sales_bundle'."

    def test_execute_query_returns_failure_payload_when_connection_errors(self):
        from agent_engine.engine.subagents.text2sql.service import Text2SQLDuckDBService

        class BrokenConnection:
            def execute(self, statement: str):
                raise RuntimeError("boom")

        service = object.__new__(Text2SQLDuckDBService)
        service._conn = BrokenConnection()
        service._lock = threading.RLock()
        service._attached_sources = {}

        result = service.execute_query("SELECT 1")

        assert result["success"] is False
        assert result["error"] == "boom"
