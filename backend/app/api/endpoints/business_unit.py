"""BusinessUnit API endpoint aggregator."""

from app.api.endpoints.business_unit_routes import (
    agent_resources_router,
    agents_router,
    asset_bundles_router,
    business_units_router,
)

# Reuse the root BusinessUnit router as the aggregation root so its empty-path
# collection endpoints remain mounted at `/business_units` without triggering
# FastAPI's nested empty-prefix validation.
router = business_units_router
router.include_router(asset_bundles_router)
router.include_router(agents_router)
router.include_router(agent_resources_router)
