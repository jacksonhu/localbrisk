"""BusinessUnit endpoint router collection."""

from app.api.endpoints.business_unit_routes.agent_resources import router as agent_resources_router
from app.api.endpoints.business_unit_routes.agents import router as agents_router
from app.api.endpoints.business_unit_routes.asset_bundles import router as asset_bundles_router
from app.api.endpoints.business_unit_routes.business_units import router as business_units_router

__all__ = [
    "agent_resources_router",
    "agents_router",
    "asset_bundles_router",
    "business_units_router",
]
