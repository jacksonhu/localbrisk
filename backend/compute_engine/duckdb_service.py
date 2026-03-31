"""DuckDB compute engine service (persistent mode)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb


class DuckDBService:
    """Manages persistent DuckDB connections and executes SQL scripts."""

    _QUERY_SQL_PREFIXES = ("SELECT", "WITH", "SHOW", "DESCRIBE", "PRAGMA")

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._lock = threading.RLock()

    @property
    def is_initialized(self) -> bool:
        return self._conn is not None

    def initialize(self) -> None:
        with self._lock:
            if self._conn is not None:
                return

            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.db_path))
            self._init_schema()

    def close(self) -> None:
        with self._lock:
            if self._conn is None:
                return
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        assert self._conn is not None

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compute_registry (
                name VARCHAR PRIMARY KEY,
                value_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sql_execution_history (
                id BIGINT,
                sql_script TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                execution_ms DOUBLE,
                affected_rows BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    def upsert_registry(self, name: str, value: Dict[str, Any]) -> None:
        if not name.strip():
            raise ValueError("name 不能为空")

        self.initialize()
        payload = json.dumps(value, ensure_ascii=False)

        with self._lock:
            assert self._conn is not None
            self._conn.execute(
                """
                INSERT INTO compute_registry(name, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE
                SET value_json = EXCLUDED.value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [name, payload],
            )

    def execute_sql_script(
        self,
        script: str,
        params: Optional[List[Any]] = None,
        fetch_result: bool = True,
        max_rows: int = 500,
    ) -> Dict[str, Any]:
        if not script or not script.strip():
            raise ValueError("SQL script不能为空")
        if max_rows <= 0:
            raise ValueError("max_rows 必须大于 0")

        self.initialize()

        start = time.perf_counter()
        success = False
        error_message: Optional[str] = None
        affected_rows = 0

        columns: List[str] = []
        rows: List[Dict[str, Any]] = []
        truncated = False

        try:
            with self._lock:
                assert self._conn is not None
                if params:
                    cursor = self._conn.execute(script, params)
                else:
                    cursor = self._conn.execute(script)

                desc = cursor.description or []
                columns = [item[0] for item in desc]

                if fetch_result and columns:
                    fetched = cursor.fetchmany(max_rows + 1)
                    truncated = len(fetched) > max_rows
                    if truncated:
                        fetched = fetched[:max_rows]
                    rows = [dict(zip(columns, row)) for row in fetched]
                    affected_rows = len(rows)
                else:
                    affected_rows = max(cursor.rowcount, 0)

            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._record_execution(script, success, error_message, elapsed_ms, affected_rows)

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "affected_rows": affected_rows,
            "truncated": truncated,
            "execution_ms": round(elapsed_ms, 3),
        }

    def execute_query_sql_script(
        self,
        script: str,
        params: Optional[List[Any]] = None,
        max_rows: int = 500,
    ) -> Dict[str, Any]:
        """Execute查询类 SQL script, 并返回表格数据."""
        normalized_script = (script or "").strip()
        if not normalized_script:
            raise ValueError("SQL script不能为空")

        upper_script = normalized_script.upper()
        if not upper_script.startswith(self._QUERY_SQL_PREFIXES):
            raise ValueError("仅支持查询类 SQL (SELECT/WITH/SHOW/DESCRIBE/PRAGMA)")

        result = self.execute_sql_script(
            script=normalized_script,
            params=params,
            fetch_result=True,
            max_rows=max_rows,
        )

        table = {
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": len(result["rows"]),
            "truncated": result["truncated"],
        }

        return {
            **result,
            "table": table,
        }

    def _record_execution(
        self,
        script: str,
        success: bool,
        error_message: Optional[str],
        execution_ms: float,
        affected_rows: int,
    ) -> None:
        with self._lock:
            if self._conn is None:
                return
            self._conn.execute(
                """
                INSERT INTO sql_execution_history(
                    sql_script,
                    success,
                    error_message,
                    execution_ms,
                    affected_rows
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [script, success, error_message, execution_ms, affected_rows],
            )


_service: Optional[DuckDBService] = None
_service_lock = threading.Lock()


def init_duckdb_service(db_path: Path) -> DuckDBService:
    global _service
    with _service_lock:
        if _service is None:
            _service = DuckDBService(db_path)
        _service.initialize()
        return _service


def get_duckdb_service() -> DuckDBService:
    if _service is None:
        raise RuntimeError("DuckDBService has not been initialized")
    return _service


def close_duckdb_service() -> None:
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None
