"""
Health check endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """Health check."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check."""
    return {"status": "ready"}
