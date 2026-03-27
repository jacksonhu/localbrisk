"""Compute Engine API 端点。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from compute_engine import get_duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter()


class DuckDBSqlExecuteRequest(BaseModel):
    """执行 DuckDB SQL 脚本请求。"""

    sql_script: str = Field(..., min_length=1, description="SQL 脚本")
    params: Optional[List[Any]] = Field(default=None, description="可选参数（占位符 ?）")
    fetch_result: bool = Field(default=True, description="是否返回结果集")
    max_rows: int = Field(default=500, ge=1, le=10000, description="最大返回行数")


class DuckDBSqlExecuteResponse(BaseModel):
    """执行 DuckDB SQL 脚本响应。"""

    success: bool
    columns: List[str]
    rows: List[Dict[str, Any]]
    affected_rows: int
    truncated: bool
    execution_ms: float


@router.post("/sql/execute", response_model=DuckDBSqlExecuteResponse)
async def execute_duckdb_sql(request: DuckDBSqlExecuteRequest):
    """执行 DuckDB SQL 脚本。"""
    logger.info("执行 DuckDB SQL 脚本")

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
        logger.warning(f"DuckDB SQL 参数错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"DuckDB 服务不可用: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"DuckDB SQL 执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"DuckDB SQL 执行失败: {e}")
