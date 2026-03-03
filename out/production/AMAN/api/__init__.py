"""
API 路由模块
"""

from fastapi import APIRouter

from app.api.endpoints import business_unit, health, agent_runtime, llm_providers, model_runtime

router = APIRouter()

# 注册各个端点路由
router.include_router(health.router, prefix="/health", tags=["健康检查"])
router.include_router(business_unit.router, prefix="/business_units", tags=["BusinessUnit 管理"])
router.include_router(agent_runtime.router, prefix="/runtime", tags=["Agent 运行时"])
router.include_router(model_runtime.router, prefix="/runtime", tags=["Model 运行时"])
router.include_router(llm_providers.router, prefix="/llm", tags=["LLM 配置"])
