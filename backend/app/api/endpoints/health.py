"""
健康检查端点
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {"status": "ready"}
