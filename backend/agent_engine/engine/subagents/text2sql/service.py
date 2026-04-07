"""Text2SQL DuckDB query service.

Provides a per-agent lightweight DuckDB in-memory connection that can
ATTACH remote MySQL / PostgreSQL databases via official DuckDB extensions.
Only read-only SQL is allowed.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Dict, Optional

from agent_engine.monitoring import emit_audit_event

try:
    import duckdb

    _DUCKDB_AVAILABLE = True
    _DUCKDB_IMPORT_ERROR: Optional[str] = None
except ImportError as exc:  # pragma: no cover - depends on local environment
    duckdb = None
    _DUCKDB_AVAILABLE = False
    _DUCKDB_IMPORT_ERROR = str(exc)

logger = logging.getLogger(__name__)

_QUERY_SQL_PREFIXES = ("SELECT", "WITH", "SHOW", "DESCRIBE", "PRAGMA", "EXPLAIN")
_FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b("
    r"INSERT\s+INTO|"
    r"UPDATE\s+[A-Za-z_]|"
    r"DELETE\s+FROM|"
    r"DROP\s+(TABLE|VIEW|SCHEMA|DATABASE)|"
    r"TRUNCATE\s+(TABLE|SCHEMA)|"
    r"ALTER\s+(TABLE|VIEW|SCHEMA|DATABASE)|"
    r"CREATE\s+(TABLE|VIEW|SCHEMA|DATABASE)|"
    r"MERGE\s+INTO|"
    r"CALL\s+[A-Za-z_]|"
    r"COPY\s+[A-Za-z_].*\b(TO|FROM)\b|"
    r"ATTACH\b|DETACH\b|INSTALL\b|LOAD\b|"
    r"EXPORT\s+DATABASE|IMPORT\s+DATABASE|"
    r"REPLACE\s+INTO|GRANT\b|REVOKE\b"
    r")\b",
    re.IGNORECASE | re.DOTALL,
)
_SQL_COMMENT_PATTERN = re.compile(r"(--[^\n]*$)|(/\*.*?\*/)", re.MULTILINE | re.DOTALL)


def check_duckdb_available() -> None:
    """Raise a descriptive error when duckdb is unavailable."""
    if _DUCKDB_AVAILABLE:
        return
    raise ImportError(
        "duckdb is required for Text2SQL support. "
        f"Original import error: {_DUCKDB_IMPORT_ERROR}"
    )


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments before validation."""
    return _SQL_COMMENT_PATTERN.sub(" ", sql)


def validate_read_only_sql(sql: str) -> str:
    """Validate and normalize a single read-only SQL statement."""
    normalized = (sql or "").strip()
    if not normalized:
        raise ValueError("SQL query must not be empty")

    without_comments = _strip_sql_comments(normalized).strip()
    if not without_comments:
        raise ValueError("SQL query must not be empty")

    statement = without_comments.rstrip("; ").strip()
    if not statement:
        raise ValueError("SQL query must not be empty")

    if ";" in statement:
        raise ValueError("Only a single SQL statement is allowed")

    upper_sql = statement.upper()
    if not upper_sql.startswith(_QUERY_SQL_PREFIXES):
        raise ValueError(
            "Only read-only SQL is allowed "
            "(SELECT / WITH / SHOW / DESCRIBE / PRAGMA / EXPLAIN)"
        )

    forbidden_match = _FORBIDDEN_SQL_PATTERN.search(statement)
    if forbidden_match:
        raise ValueError(
            f"Forbidden SQL keyword detected: {forbidden_match.group(0)}"
        )

    return statement


def _quote_identifier(identifier: str) -> str:
    """Safely quote a DuckDB identifier."""
    cleaned = (identifier or "").strip()
    if not cleaned:
        raise ValueError("Data source name must not be empty")
    return '"' + cleaned.replace('"', '""') + '"'


def _quote_sql_literal(value: Any) -> str:
    """Safely quote a SQL string literal."""
    text = "" if value is None else str(value)
    return "'" + text.replace("'", "''") + "'"


def _redact_secret(message: str, secret: Optional[str]) -> str:
    """Mask sensitive values from error messages before logging."""
    if not secret:
        return message
    return message.replace(secret, "***")


class Text2SQLDuckDBService:
    """Per-agent lightweight DuckDB connection for text2sql queries."""

    def __init__(self) -> None:
        check_duckdb_available()
        self._conn: Optional[Any] = None
        self._lock = threading.RLock()
        self._attached_sources: Dict[str, str] = {}
        self._initialize()

    def _initialize(self) -> None:
        """Create an in-memory DuckDB connection."""
        with self._lock:
            if self._conn is not None:
                return
            self._conn = duckdb.connect(":memory:")
            logger.info("Text2SQL DuckDB in-memory connection created")

    def attach_mysql(
        self,
        name: str,
        host: str,
        port: int,
        db: str,
        user: str,
        password: str,
    ) -> None:
        """Attach a remote MySQL database via DuckDB mysql extension."""
        self._attach_remote(
            name=name,
            db_type="mysql",
            extension="mysql",
            attach_type="MYSQL",
            dsn_items={
                "host": host,
                "port": int(port or 3306),
                "user": user,
                "password": password,
                "database": db,
            },
            password=password,
        )

    def attach_postgres(
        self,
        name: str,
        host: str,
        port: int,
        db: str,
        user: str,
        password: str,
    ) -> None:
        """Attach a remote PostgreSQL database via DuckDB postgres extension."""
        self._attach_remote(
            name=name,
            db_type="postgresql",
            extension="postgres",
            attach_type="POSTGRES",
            dsn_items={
                "host": host,
                "port": int(port or 5432),
                "user": user,
                "password": password,
                "dbname": db,
            },
            password=password,
        )

    def _attach_remote(
        self,
        *,
        name: str,
        db_type: str,
        extension: str,
        attach_type: str,
        dsn_items: Dict[str, Any],
        password: Optional[str],
    ) -> None:
        """Load extension and attach a remote read-only data source."""
        with self._lock:
            if self._conn is None:
                raise RuntimeError("DuckDB connection is not initialized")

            if name in self._attached_sources:
                logger.debug("Data source '%s' already attached, skipping", name)
                return

            try:
                self._conn.execute(f"INSTALL {extension}")
                self._conn.execute(f"LOAD {extension}")
                logger.info("DuckDB extension '%s' loaded successfully", extension)
            except Exception as ext_err:
                logger.warning(
                    "Failed to load DuckDB extension '%s' for data source '%s': %s",
                    extension,
                    name,
                    _redact_secret(str(ext_err), password),
                )
                return

            dsn = " ".join(
                f"{key}={value}"
                for key, value in dsn_items.items()
                if value not in (None, "")
            )
            attach_sql = (
                f"ATTACH {_quote_sql_literal(dsn)} AS {_quote_identifier(name)} "
                f"(TYPE {attach_type}, READ_ONLY)"
            )

            try:
                self._conn.execute(attach_sql)
                self._attached_sources[name] = db_type
                logger.info(
                    "Attached %s data source '%s' (host=%s, port=%s, database=%s)",
                    db_type,
                    name,
                    dsn_items.get("host", ""),
                    dsn_items.get("port", ""),
                    dsn_items.get("database") or dsn_items.get("dbname") or "",
                )
            except Exception as attach_err:
                logger.warning(
                    "Failed to attach %s data source '%s': %s",
                    db_type,
                    name,
                    _redact_secret(str(attach_err), password),
                )

    def execute_query(
        self,
        sql: str,
        max_rows: int = 200,
    ) -> Dict[str, Any]:
        """Execute a read-only SQL query and return structured results."""
        statement = validate_read_only_sql(sql)
        max_rows = max(1, min(int(max_rows), 1000))

        start = time.perf_counter()
        try:
            with self._lock:
                if self._conn is None:
                    raise RuntimeError("DuckDB connection is not initialized")
                cursor = self._conn.execute(statement)
                desc = cursor.description or []
                columns = [item[0] for item in desc]

                if columns:
                    fetched = cursor.fetchmany(max_rows + 1)
                    truncated = len(fetched) > max_rows
                    if truncated:
                        fetched = fetched[:max_rows]
                    rows = [dict(zip(columns, row)) for row in fetched]
                else:
                    rows = []
                    truncated = False

            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            logger.info(
                "Text2SQL query executed: rows=%d, truncated=%s, elapsed_ms=%.3f",
                len(rows),
                truncated,
                elapsed_ms,
            )
            emit_audit_event(
                "sql.executed",
                source="text2sql",
                statement_type=statement.split(None, 1)[0].upper() if statement else "UNKNOWN",
                sql_preview=" ".join(statement.split())[:240],
                success=True,
                duration_ms=elapsed_ms,
                affected_rows=len(rows),
                truncated=truncated,
            )
            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "execution_ms": elapsed_ms,
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            logger.warning("Text2SQL query failed: %s", exc)
            emit_audit_event(
                "sql.executed",
                source="text2sql",
                statement_type=statement.split(None, 1)[0].upper() if statement else "UNKNOWN",
                sql_preview=" ".join(statement.split())[:240] if statement else "",
                success=False,
                duration_ms=elapsed_ms,
                error_message=str(exc),
            )
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "execution_ms": elapsed_ms,
                "error": str(exc),
            }

    @property
    def attached_sources(self) -> Dict[str, str]:
        """Return a copy of the attached data source mapping."""
        return dict(self._attached_sources)

    def close(self) -> None:
        """Close the DuckDB connection and release resources."""
        with self._lock:
            if self._conn is None:
                return
            try:
                self._conn.close()
            except Exception as exc:
                logger.warning("Error closing Text2SQL DuckDB connection: %s", exc)
            finally:
                self._conn = None
                self._attached_sources.clear()
                logger.info("Text2SQL DuckDB connection closed")


__all__ = [
    "Text2SQLDuckDBService",
    "check_duckdb_available",
    "validate_read_only_sql",
]
