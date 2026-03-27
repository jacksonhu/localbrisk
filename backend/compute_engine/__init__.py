"""Compute Engine 对外导出。"""

from .duckdb_service import (
    DuckDBService,
    init_duckdb_service,
    get_duckdb_service,
    close_duckdb_service,
)

__all__ = [
    "DuckDBService",
    "init_duckdb_service",
    "get_duckdb_service",
    "close_duckdb_service",
]
