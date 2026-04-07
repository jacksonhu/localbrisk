"""Compute engine API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent_engine.monitoring import emit_runtime_event, scoped_logging_context
from compute_engine import get_duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DuckDBSqlExecuteRequest(BaseModel):
    """Request body for executing a DuckDB SQL script."""

    sql_script: str = Field(..., min_length=1, description="SQL script")
    params: Optional[List[Any]] = Field(default=None, description="Optional positional parameters")
    fetch_result: bool = Field(default=True, description="Whether to return the result set")
    max_rows: int = Field(default=500, ge=1, le=10000, description="Maximum rows to return")


class DuckDBSqlExecuteResponse(BaseModel):
    """Response body for DuckDB SQL execution."""

    success: bool
    columns: List[str]
    rows: List[Dict[str, Any]]
    affected_rows: int
    truncated: bool
    execution_ms: float


@router.post("/sql/execute", response_model=DuckDBSqlExecuteResponse)
async def execute_duckdb_sql(request: DuckDBSqlExecuteRequest, http_request: Request):
    """Execute a DuckDB SQL script."""
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    operation_context = {
        "request_id": request_id,
        "session_id": request_id,
        "component": "compute_engine_api",
        "source": "compute_api",
    }

    with scoped_logging_context(**operation_context):
        logger.info("Executing DuckDB SQL script")
        emit_runtime_event(
            "compute.sql.requested",
            statement_preview=" ".join(request.sql_script.strip().split())[:120],
            fetch_result=request.fetch_result,
            max_rows=request.max_rows,
        )
        try:
            service = get_duckdb_service()
            result = service.execute_sql_script(
                script=request.sql_script,
                params=request.params,
                fetch_result=request.fetch_result,
                max_rows=request.max_rows,
            )
            emit_runtime_event(
                "compute.sql.completed",
                duration_ms=result["execution_ms"],
                affected_rows=result["affected_rows"],
                truncated=result["truncated"],
            )
            return DuckDBSqlExecuteResponse(**result)
        except ValueError as exc:
            logger.warning("DuckDB SQL parameter validation failed: %s", exc)
            emit_runtime_event(
                "compute.sql.failed",
                level=logging.WARNING,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            logger.error("DuckDB service unavailable: %s", exc)
            emit_runtime_event(
                "compute.sql.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("DuckDB SQL execution failed: %s", exc)
            emit_runtime_event(
                "compute.sql.failed",
                level=logging.ERROR,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            raise HTTPException(status_code=500, detail=f"DuckDB SQL execution failed: {exc}") from exc
