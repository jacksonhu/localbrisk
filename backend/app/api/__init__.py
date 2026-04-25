"""
API routing module.
"""

from fastapi import APIRouter

from app.api.endpoints import business_unit, health, agent_runtime, llm_providers, model_runtime, compute_engine, foreman_runtime

router = APIRouter()

# Register endpoint routers
router.include_router(health.router, prefix="/health", tags=["Health Check"])
router.include_router(business_unit.router, prefix="/business_units", tags=["BusinessUnit Management"])
router.include_router(agent_runtime.router, prefix="/runtime", tags=["Agent Runtime"])
router.include_router(model_runtime.router, prefix="/runtime", tags=["Model Runtime"])
router.include_router(llm_providers.router, prefix="/llm", tags=["LLM Configuration"])
router.include_router(compute_engine.router, prefix="/compute", tags=["Compute Engine"])
router.include_router(foreman_runtime.router, prefix="/foreman", tags=["Foreman"])
