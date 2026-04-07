"""Asset bundle and asset endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from app.api.endpoints.business_unit_routes.common import (
    business_unit_service,
    crud,
    get_asset_bundle_service,
    handle_not_found,
    logger,
)
from app.models.business_unit import Asset, AssetBundle, AssetBundleCreate, AssetBundleUpdate, AssetCreate
from app.models.metadata import SyncResult

router = APIRouter()


def _get_bundle_or_404(business_unit_id: str, bundle_name: str) -> AssetBundle:
    for bundle in get_asset_bundle_service().get_asset_bundles(business_unit_id):
        if bundle.name == bundle_name:
            return bundle
    raise HTTPException(status_code=404, detail="AssetBundle not found")


@router.get("/{business_unit_id}/asset_bundles", response_model=List[AssetBundle])
async def list_asset_bundles(business_unit_id: str):
    """Return asset bundles under a business unit."""
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    bundles = get_asset_bundle_service().get_asset_bundles(business_unit_id)
    logger.debug("Business unit %s contains %s asset bundle(s)", business_unit_id, len(bundles))
    return bundles


@router.post("/{business_unit_id}/asset_bundles", response_model=AssetBundle)
async def create_asset_bundle(business_unit_id: str, data: AssetBundleCreate):
    """Create an asset bundle."""
    try:
        return get_asset_bundle_service().create_asset_bundle(business_unit_id, data)
    except ValueError as exc:
        logger.warning("Failed to create asset bundle %s/%s: %s", business_unit_id, data.name, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def get_asset_bundle(business_unit_id: str, bundle_name: str):
    """Return asset bundle details."""
    return _get_bundle_or_404(business_unit_id, bundle_name)


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/config")
async def get_asset_bundle_config(business_unit_id: str, bundle_name: str):
    """Return raw asset bundle config content."""
    return crud.config_response(
        get_asset_bundle_service().get_asset_bundle_config_content(business_unit_id, bundle_name),
        "AssetBundle",
    )


@router.put("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def update_asset_bundle(business_unit_id: str, bundle_name: str, update: AssetBundleUpdate):
    """Update an asset bundle."""
    result = handle_not_found(
        get_asset_bundle_service().update_asset_bundle(business_unit_id, bundle_name, update),
        "AssetBundle not found",
    )
    logger.info("Updated asset bundle: %s/%s", business_unit_id, bundle_name)
    return result


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}")
async def delete_asset_bundle(business_unit_id: str, bundle_name: str):
    """Delete an asset bundle."""
    if not get_asset_bundle_service().delete_asset_bundle(business_unit_id, bundle_name):
        logger.warning("Asset bundle not found for delete: %s/%s", business_unit_id, bundle_name)
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    logger.info("Deleted asset bundle: %s/%s", business_unit_id, bundle_name)
    return crud.success_message("deleted", "AssetBundle")


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/sync", response_model=SyncResult)
async def sync_asset_bundle_metadata(business_unit_id: str, bundle_name: str):
    """Synchronize metadata for an external asset bundle."""
    result = get_asset_bundle_service().sync_asset_bundle_metadata(business_unit_id, bundle_name)
    if not result.success and "does not exist" in str(result.errors):
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    return result


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=List[Asset])
async def list_assets(business_unit_id: str, bundle_name: str):
    """Return assets under an asset bundle."""
    assets = get_asset_bundle_service().scan_assets(business_unit_id, bundle_name)
    logger.debug("Asset bundle %s/%s contains %s asset(s)", business_unit_id, bundle_name, len(assets))
    return assets


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=Asset)
async def create_asset(business_unit_id: str, bundle_name: str, data: AssetCreate):
    """Create an asset under an asset bundle."""
    try:
        return get_asset_bundle_service().create_asset(business_unit_id, bundle_name, data)
    except (ValueError, FileNotFoundError) as exc:
        status_code = 404 if isinstance(exc, FileNotFoundError) else 400
        logger.warning("Failed to create asset %s/%s/%s: %s", business_unit_id, bundle_name, data.name, exc)
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}/config")
async def get_asset_config(business_unit_id: str, bundle_name: str, asset_name: str):
    """Return raw asset config content."""
    return crud.config_response(
        get_asset_bundle_service().get_asset_config_content(business_unit_id, bundle_name, asset_name),
        "Asset",
    )


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}")
async def delete_asset(business_unit_id: str, bundle_name: str, asset_name: str):
    """Delete an asset under an asset bundle."""
    if not get_asset_bundle_service().delete_asset(business_unit_id, bundle_name, asset_name):
        logger.warning("Asset not found for delete: %s/%s/%s", business_unit_id, bundle_name, asset_name)
        raise HTTPException(status_code=404, detail="Asset not found")
    logger.info("Deleted asset: %s/%s/%s", business_unit_id, bundle_name, asset_name)
    return crud.success_message("deleted", "Asset")


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/tables/{table_name}/preview")
async def preview_table_data(
    business_unit_id: str,
    bundle_name: str,
    table_name: str,
    limit: int = 100,
    offset: int = 0,
):
    """Preview table data from an asset bundle."""
    try:
        return get_asset_bundle_service().preview_table_data(business_unit_id, bundle_name, table_name, limit, offset)
    except ValueError as exc:
        logger.warning("Failed to preview table %s/%s/%s: %s", business_unit_id, bundle_name, table_name, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
