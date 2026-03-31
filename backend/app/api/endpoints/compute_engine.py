"""Compute Engine API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from compute_engine import get_duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DuckDBSqlExecuteRequest(BaseModel):
    """Execute DuckDB SQL script request."""

    sql_script: str = Field(..., min_length=1, description="SQL script")
    params: Optional[List[Any]] = Field(default=None, description="Optional parameters (placeholder ?)")
    fetch_result: bool = Field(default=True, description="Whether to return result set")
    max_rows: int = Field(default=500, ge=1, le=10000, description="Maximum rows to return")


class DuckDBSqlExecuteResponse(BaseModel):
    """Execute  DuckDB SQL scriptresponse."""

    success: bool
    columns: List[str]
    rows: List[Dict[str, Any]]
    affected_rows: int
    truncated: bool
    execution_ms: float


@router.post("/sql/execute", response_model=DuckDBSqlExecuteResponse)
async def execute_duckdb_sql(request: DuckDBSqlExecuteRequest):
    """Execute  DuckDB SQL script."""
    logger.info("Executing  DuckDB SQL script")

    try:
        service = get_duckdb_service()
        result = service.execute_sql_script(
            script=request.sql_script,
            params=request.params,
            fetch_result=request.fetch_result,
            max_rows=request.max_rows,
        )
        return DuckDBSqlExecuteResponse(**result)
    except ValueError as e:
        logger.warning(f"DuckDB SQL parameter error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"DuckDB service unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"DuckDB SQL Execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"DuckDB SQL Execution failed: {e}")
