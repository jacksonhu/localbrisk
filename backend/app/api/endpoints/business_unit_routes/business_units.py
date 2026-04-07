"""Business unit CRUD endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from app.api.endpoints.business_unit_routes.common import business_unit_service, crud, handle_not_found, logger
from app.models.business_unit import BusinessUnit, BusinessUnitCreate, BusinessUnitTreeNode, BusinessUnitUpdate

router = APIRouter()


@router.get("", response_model=List[BusinessUnit])
async def list_business_units():
    """Return all business units."""
    logger.debug("Listing business units")
    business_units = business_unit_service.discover_business_units()
    logger.info("Discovered %s business unit(s)", len(business_units))
    return business_units


@router.post("", response_model=BusinessUnit)
async def create_business_unit(data: BusinessUnitCreate):
    """Create a business unit."""
    logger.info("Creating business unit: %s", data.name)
    try:
        return business_unit_service.create_business_unit(data)
    except ValueError as exc:
        logger.warning("Failed to create business unit %s: %s", data.name, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tree", response_model=List[BusinessUnitTreeNode])
async def get_business_unit_tree():
    """Return the business unit navigation tree."""
    tree = business_unit_service.get_business_unit_tree()
    logger.debug("Built business unit tree with %s root node(s)", len(tree))
    return tree


@router.get("/{business_unit_id}", response_model=BusinessUnit)
async def get_business_unit(business_unit_id: str):
    """Return business unit details."""
    return handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")


@router.get("/{business_unit_id}/config")
async def get_business_unit_config(business_unit_id: str):
    """Return raw business unit config content."""
    return crud.config_response(business_unit_service.get_business_unit_config_content(business_unit_id), "BusinessUnit")


@router.put("/{business_unit_id}", response_model=BusinessUnit)
async def update_business_unit(business_unit_id: str, update: BusinessUnitUpdate):
    """Update a business unit."""
    result = handle_not_found(
        business_unit_service.update_business_unit(business_unit_id, update),
        "BusinessUnit not found",
    )
    logger.info("Updated business unit: %s", business_unit_id)
    return result


@router.delete("/{business_unit_id}")
async def delete_business_unit(business_unit_id: str):
    """Delete a business unit."""
    if not business_unit_service.delete_business_unit(business_unit_id):
        logger.warning("Business unit not found for delete: %s", business_unit_id)
        raise HTTPException(status_code=404, detail="BusinessUnit not found")
    logger.info("Deleted business unit: %s", business_unit_id)
    return crud.success_message("deleted", "BusinessUnit")
