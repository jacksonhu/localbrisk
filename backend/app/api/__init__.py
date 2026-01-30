"""
API 路由模块
"""

from fastapi import APIRouter

from app.api.endpoints import catalog, health

router = APIRouter()

# 注册各个端点路由
router.include_router(health.router, prefix="/health", tags=["健康检查"])
router.include_router(catalog.router, prefix="/catalogs", tags=["Catalog 管理"])
