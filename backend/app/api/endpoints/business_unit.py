"""
BusinessUnit API Endpoints
Provides CRUD operations for BusinessUnit, AssetBundle, Asset, Agent, Model, MCP, Memory, Skill
"""

import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.business_unit import (
    # BusinessUnit
    BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate, BusinessUnitTreeNode,
    # AssetBundle
    AssetBundle, AssetBundleCreate, AssetBundleUpdate,
    # Asset
    Asset, AssetCreate,
    # Agent
    Agent, AgentCreate, AgentUpdate,
    # Model
    Model, ModelCreate, ModelUpdate,
    # MCP
    MCP, MCPCreate, MCPUpdate,
    # Memory
    Memory, MemoryCreate, MemoryUpdate,
)
from app.models.metadata import SyncResult
from app.services import business_unit_service
from app.api.utils import handle_not_found, CRUDRouter

logger = logging.getLogger(__name__)
router = APIRouter()
crud = CRUDRouter()


class OutputFileContentResponse(BaseModel):
    """Output file content response"""
    path: str
    relative_path: str
    content: str


# ==================== BusinessUnit ====================

@router.get("", response_model=List[BusinessUnit])
async def list_business_units():
    """Get all BusinessUnits"""
    logger.debug("Getting all BusinessUnit list")
    business_units = business_unit_service.discover_business_units()
    logger.info(f"Discover {len(business_units)}  BusinessUnit(s)")
    return business_units


@router.post("", response_model=BusinessUnit)
async def create_business_unit(data: BusinessUnitCreate):
    """Create BusinessUnit"""
    logger.info(f"Creating BusinessUnit: {data.name}")
    try:
        bu = business_unit_service.create_business_unit(data)
        logger.info(f"BusinessUnit created successfully: {data.name}")
        return bu
    except ValueError as e:
        logger.warning(f"Create BusinessUnit failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree", response_model=List[BusinessUnitTreeNode])
async def get_business_unit_tree():
    """Get BusinessUnit navigation tree"""
    logger.debug("Getting BusinessUnit navigation tree")
    tree = business_unit_service.get_business_unit_tree()
    logger.debug(f"Navigation tree contains {len(tree)}  root nodes")
    return tree


@router.get("/{business_unit_id}", response_model=BusinessUnit)
async def get_business_unit(business_unit_id: str):
    """Get BusinessUnit details"""
    logger.debug(f"Fetching BusinessUnit details: {business_unit_id}")
    return handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")


@router.get("/{business_unit_id}/config")
async def get_business_unit_config(business_unit_id: str):
    """Get BusinessUnit config raw content"""
    logger.debug(f"Fetching BusinessUnit config: {business_unit_id}")
    return crud.config_response(business_unit_service.get_business_unit_config_content(business_unit_id), "BusinessUnit")


@router.put("/{business_unit_id}", response_model=BusinessUnit)
async def update_business_unit(business_unit_id: str, update: BusinessUnitUpdate):
    """Update BusinessUnit"""
    logger.info(f"Updating BusinessUnit: {business_unit_id}")
    result = handle_not_found(business_unit_service.update_business_unit(business_unit_id, update), "BusinessUnit not found")
    logger.info(f"BusinessUnit updated successfully: {business_unit_id}")
    return result


@router.delete("/{business_unit_id}")
async def delete_business_unit(business_unit_id: str):
    """Delete BusinessUnit"""
    logger.info(f"Deleting BusinessUnit: {business_unit_id}")
    if not business_unit_service.delete_business_unit(business_unit_id):
        logger.warning(f"BusinessUnit  does not exist: {business_unit_id}")
        raise HTTPException(status_code=404, detail="BusinessUnit not found")
    logger.info(f"BusinessUnit deleted successfully: {business_unit_id}")
    return crud.success_message("deleted", "BusinessUnit")


# ==================== AssetBundle ====================

@router.get("/{business_unit_id}/asset_bundles", response_model=List[AssetBundle])
async def list_asset_bundles(business_unit_id: str):
    """Get AssetBundle list"""
    logger.debug(f"Fetching AssetBundle list: business_unit={business_unit_id}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    bundles = business_unit_service.get_asset_bundles(business_unit_id)
    logger.debug(f"BusinessUnit {business_unit_id} contains {len(bundles)}  AssetBundle(s)")
    return bundles


@router.post("/{business_unit_id}/asset_bundles", response_model=AssetBundle)
async def create_asset_bundle(business_unit_id: str, data: AssetBundleCreate):
    """Create AssetBundle"""
    logger.info(f"Creating AssetBundle: business_unit={business_unit_id}, name={data.name}")
    try:
        bundle = business_unit_service.create_asset_bundle(business_unit_id, data)
        logger.info(f"AssetBundle created successfully: {business_unit_id}/{data.name}")
        return bundle
    except ValueError as e:
        logger.warning(f"Create AssetBundle failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def get_asset_bundle(business_unit_id: str, bundle_name: str):
    """Get AssetBundle details"""
    logger.debug(f"Fetching AssetBundle details: {business_unit_id}/{bundle_name}")
    for bundle in business_unit_service.get_asset_bundles(business_unit_id):
        if bundle.name == bundle_name:
            return bundle
    logger.warning(f"AssetBundle  does not exist: {business_unit_id}/{bundle_name}")
    raise HTTPException(status_code=404, detail="AssetBundle not found")


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/config")
async def get_asset_bundle_config(business_unit_id: str, bundle_name: str):
    """Get AssetBundle config raw content"""
    logger.debug(f"Fetching AssetBundle config: {business_unit_id}/{bundle_name}")
    return crud.config_response(business_unit_service.get_asset_bundle_config_content(business_unit_id, bundle_name), "AssetBundle")


@router.put("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def update_asset_bundle(business_unit_id: str, bundle_name: str, update: AssetBundleUpdate):
    """Update AssetBundle"""
    logger.info(f"Updating AssetBundle: {business_unit_id}/{bundle_name}")
    result = handle_not_found(business_unit_service.update_asset_bundle(business_unit_id, bundle_name, update), "AssetBundle not found")
    logger.info(f"AssetBundle updated successfully: {business_unit_id}/{bundle_name}")
    return result


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}")
async def delete_asset_bundle(business_unit_id: str, bundle_name: str):
    """Delete AssetBundle"""
    logger.info(f"Deleting AssetBundle: {business_unit_id}/{bundle_name}")
    if not business_unit_service.delete_asset_bundle(business_unit_id, bundle_name):
        logger.warning(f"AssetBundle  does not exist: {business_unit_id}/{bundle_name}")
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    logger.info(f"AssetBundle deleted successfully: {business_unit_id}/{bundle_name}")
    return crud.success_message("deleted", "AssetBundle")


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/sync", response_model=SyncResult)
async def sync_asset_bundle_metadata(business_unit_id: str, bundle_name: str):
    """Sync AssetBundle metadata"""
    logger.info(f"Syncing AssetBundle metadata: {business_unit_id}/{bundle_name}")
    result = business_unit_service.sync_asset_bundle_metadata(business_unit_id, bundle_name)
    if not result.success and "does not exist" in str(result.errors):
        logger.warning(f"AssetBundle  does not exist: {business_unit_id}/{bundle_name}")
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    if result.success:
        logger.info(f"AssetBundle Metadata sync succeeded: {business_unit_id}/{bundle_name}")
    else:
        logger.warning(f"AssetBundle Metadata sync failed: {result.errors}")
    return result


# ==================== Asset ====================

@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=List[Asset])
async def list_assets(business_unit_id: str, bundle_name: str):
    """Get Asset list"""
    logger.debug(f"Fetching Asset list: {business_unit_id}/{bundle_name}")
    assets = business_unit_service.scan_assets(business_unit_id, bundle_name)
    logger.debug(f"AssetBundle {bundle_name} contains {len(assets)}  Asset(s)")
    return assets


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=Asset)
async def create_asset(business_unit_id: str, bundle_name: str, data: AssetCreate):
    """Create Asset"""
    logger.info(f"Creating Asset: {business_unit_id}/{bundle_name}/{data.name}, type={data.asset_type}")
    try:
        asset = business_unit_service.create_asset(business_unit_id, bundle_name, data)
        logger.info(f"Asset created successfully: {business_unit_id}/{bundle_name}/{data.name}")
        return asset
    except (ValueError, FileNotFoundError) as e:
        status = 404 if isinstance(e, FileNotFoundError) else 400
        logger.warning(f"Create Asset failed: {e}")
        raise HTTPException(status_code=status, detail=str(e))


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}/config")
async def get_asset_config(business_unit_id: str, bundle_name: str, asset_name: str):
    """Get Asset config raw content"""
    logger.debug(f"Fetching Asset config: {business_unit_id}/{bundle_name}/{asset_name}")
    return crud.config_response(business_unit_service.get_asset_config_content(business_unit_id, bundle_name, asset_name), "Asset")


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}")
async def delete_asset(business_unit_id: str, bundle_name: str, asset_name: str):
    """Delete Asset"""
    logger.info(f"Deleting Asset: {business_unit_id}/{bundle_name}/{asset_name}")
    if not business_unit_service.delete_asset(business_unit_id, bundle_name, asset_name):
        logger.warning(f"Asset  does not exist: {business_unit_id}/{bundle_name}/{asset_name}")
        raise HTTPException(status_code=404, detail="Asset not found")
    logger.info(f"Asset deleted successfully: {business_unit_id}/{bundle_name}/{asset_name}")
    return crud.success_message("deleted", "Asset")


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/tables/{table_name}/preview")
async def preview_table_data(business_unit_id: str, bundle_name: str, table_name: str, limit: int = 100, offset: int = 0):
    """Preview table data"""
    logger.debug(f"Previewing table data: {business_unit_id}/{bundle_name}/{table_name}, limit={limit}, offset={offset}")
    try:
        result = business_unit_service.preview_table_data(business_unit_id, bundle_name, table_name, limit, offset)
        logger.debug(f"Table data preview succeeded: {table_name}")
        return result
    except ValueError as e:
        logger.warning(f"Preview table datafailed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Agent ====================

@router.get("/{business_unit_id}/agents", response_model=List[Agent])
async def list_agents(business_unit_id: str):
    """Get Agent list"""
    logger.debug(f"Fetching Agent list: business_unit={business_unit_id}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    agents = business_unit_service.list_agents(business_unit_id)
    logger.debug(f"BusinessUnit {business_unit_id} contains {len(agents)}  Agent(s)")
    return agents


@router.post("/{business_unit_id}/agents", response_model=Agent)
async def create_agent(business_unit_id: str, data: AgentCreate):
    """Create Agent"""
    logger.info(f"Creating Agent: business_unit={business_unit_id}, name={data.name}")
    try:
        agent = business_unit_service.create_agent(business_unit_id, data)
        logger.info(f"Agent created successfully: {business_unit_id}/{data.name}")
        return agent
    except ValueError as e:
        logger.warning(f"Create Agent failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def get_agent(business_unit_id: str, agent_name: str):
    """Get Agent details"""
    logger.debug(f"Fetching Agent details: {business_unit_id}/{agent_name}")
    return handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")


@router.get("/{business_unit_id}/agents/{agent_name}/config")
async def get_agent_config(business_unit_id: str, agent_name: str):
    """Get Agent config raw content"""
    logger.debug(f"Fetching Agent config: {business_unit_id}/{agent_name}")
    return crud.config_response(business_unit_service.get_agent_config_content(business_unit_id, agent_name), "Agent")


@router.get("/{business_unit_id}/agents/{agent_name}/output/file", response_model=OutputFileContentResponse)
async def get_agent_output_file_content(
    business_unit_id: str,
    agent_name: str,
    path: str = Query(..., description="Relative path under output"),
):
    """Read specified file content under Agent output"""
    logger.debug(f"Reading Agent output file: {business_unit_id}/{agent_name}, path={path}")
    try:
        return business_unit_service.get_output_file_content(business_unit_id, agent_name, path)
    except FileNotFoundError as e:
        logger.warning(f"Output file does not exist: {business_unit_id}/{agent_name}, path={path}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning(f"Output path invalid or file unreadable: {business_unit_id}/{agent_name}, path={path}, error={e}")
        raise HTTPException(status_code=400, detail=str(e))


class OutputFileSaveRequest(BaseModel):
    """Save output file content request"""
    path: str
    content: str


@router.put("/{business_unit_id}/agents/{agent_name}/output/file", response_model=OutputFileContentResponse)
async def save_agent_output_file_content(
    business_unit_id: str,
    agent_name: str,
    request: OutputFileSaveRequest,
):
    """Save edited content to an Agent output file"""
    logger.debug(f"Saving Agent output file: {business_unit_id}/{agent_name}, path={request.path}")
    try:
        return business_unit_service.save_output_file_content(business_unit_id, agent_name, request.path, request.content)
    except FileNotFoundError as e:
        logger.warning(f"Output file does not exist: {business_unit_id}/{agent_name}, path={request.path}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning(f"Output path invalid: {business_unit_id}/{agent_name}, path={request.path}, error={e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def update_agent(business_unit_id: str, agent_name: str, update: AgentUpdate):
    """Update Agent"""
    logger.info(f"Updating Agent: {business_unit_id}/{agent_name}")
    result = handle_not_found(business_unit_service.update_agent(business_unit_id, agent_name, update), "Agent not found")
    logger.info(f"Agent updated successfully: {business_unit_id}/{agent_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}")
async def delete_agent(business_unit_id: str, agent_name: str):
    """Delete Agent"""
    logger.info(f"Deleting Agent: {business_unit_id}/{agent_name}")
    if not business_unit_service.delete_agent(business_unit_id, agent_name):
        logger.warning(f"Agent  does not exist: {business_unit_id}/{agent_name}")
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info(f"Agent deleted successfully: {business_unit_id}/{agent_name}")
    return crud.success_message("deleted", "Agent")


# ==================== Memory ====================

@router.get("/{business_unit_id}/agents/{agent_name}/memories", response_model=List[Memory])
async def list_agent_memories(business_unit_id: str, agent_name: str):
    """Get Memory list"""
    logger.debug(f"Fetching Memory list: {business_unit_id}/{agent_name}")
    memories = handle_not_found(business_unit_service.list_agent_memories(business_unit_id, agent_name), "Agent not found")
    logger.debug(f"Agent {agent_name} contains {len(memories) if memories else 0}  Memory(s)")
    return memories


@router.get("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}", response_model=Memory)
async def get_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """Get Memory details"""
    logger.debug(f"Fetching Memory details: {business_unit_id}/{agent_name}/{memory_name}")
    return handle_not_found(business_unit_service.get_agent_memory_detail(business_unit_id, agent_name, memory_name), "Memory not found")


@router.post("/{business_unit_id}/agents/{agent_name}/memories")
async def create_agent_memory(business_unit_id: str, agent_name: str, data: MemoryCreate):
    """Create Memory"""
    logger.info(f"Creating Memory: {business_unit_id}/{agent_name}/{data.name}")
    try:
        if not business_unit_service.create_agent_memory(business_unit_id, agent_name, data):
            logger.warning(f"Agent  does not exist: {business_unit_id}/{agent_name}")
            raise HTTPException(status_code=404, detail="Agent not found")
        logger.info(f"Memory created successfully: {business_unit_id}/{agent_name}/{data.name}")
        return crud.success_message("created", "Memory")
    except ValueError as e:
        logger.warning(f"Create Memory failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def update_agent_memory(business_unit_id: str, agent_name: str, memory_name: str, update: MemoryUpdate):
    """Update Memory"""
    logger.info(f"Updating Memory: {business_unit_id}/{agent_name}/{memory_name}")
    if not business_unit_service.update_agent_memory(business_unit_id, agent_name, memory_name, update):
        logger.warning(f"Memory  does not exist: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory updated successfully: {business_unit_id}/{agent_name}/{memory_name}")
    return crud.success_message("updated", "Memory")


@router.delete("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def delete_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """Delete Memory"""
    logger.info(f"Deleting Memory: {business_unit_id}/{agent_name}/{memory_name}")
    if not business_unit_service.delete_agent_memory(business_unit_id, agent_name, memory_name):
        logger.warning(f"Memory  does not exist: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory deleted successfully: {business_unit_id}/{agent_name}/{memory_name}")
    return crud.success_message("deleted", "Memory")


@router.post("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}/toggle")
async def toggle_agent_memory_enabled(business_unit_id: str, agent_name: str, memory_name: str, enabled: bool):
    """Toggle Memory enabled status"""
    logger.info(f"Toggling Memory enabled status: {business_unit_id}/{agent_name}/{memory_name} -> {enabled}")
    if not business_unit_service.toggle_memory_enabled(business_unit_id, agent_name, memory_name, enabled):
        logger.warning(f"Memory  does not exist: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory 启用状态updated successfully: {memory_name}, enabled={enabled}")
    return {"message": "Memory enabled status updated successfully", "enabled": enabled}


# ==================== Skill ====================

class SkillImportRequest(BaseModel):
    """Skill import request"""
    zip_file_path: str


@router.post("/{business_unit_id}/agents/{agent_name}/skills/import")
async def import_agent_skill(business_unit_id: str, agent_name: str, request: SkillImportRequest):
    """Import Skill from local zip file"""
    logger.info(f"Importing Skill: {business_unit_id}/{agent_name}, file={request.zip_file_path}")
    zip_path = Path(request.zip_file_path)
    
    if not zip_path.exists():
        logger.warning(f"zip file does not exist: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="File does not exist")
    if not zip_path.is_file():
        logger.warning(f"Path is not a file: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="Path is not a file")
    if zip_path.suffix.lower() != '.zip':
        logger.warning(f"Not a zip file: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="Only zip format files are supported")
    
    result = business_unit_service.import_skill_from_zip(business_unit_id, agent_name, zip_path, zip_path.name)
    if not result["success"]:
        logger.warning(f"Skill import failed: {result['message']}")
        raise HTTPException(status_code=400, detail=result["message"])
    logger.info(f"Skill imported successfully: {result.get('skill_name', 'unknown')}")
    return result


@router.get("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def get_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """Get Skill content"""
    logger.debug(f"Fetching Skill: {business_unit_id}/{agent_name}/{skill_name}")
    result = handle_not_found(business_unit_service.get_agent_skill(business_unit_id, agent_name, skill_name), "Skill not found")
    return {"name": skill_name, "content": result["content"], "path": result["path"]}


@router.delete("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def delete_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """Delete Skill"""
    logger.info(f"Deleting Skill: {business_unit_id}/{agent_name}/{skill_name}")
    if not business_unit_service.delete_agent_skill(business_unit_id, agent_name, skill_name):
        logger.warning(f"Skill  does not exist: {business_unit_id}/{agent_name}/{skill_name}")
        raise HTTPException(status_code=404, detail="Skill not found")
    logger.info(f"Skill deleted successfully: {business_unit_id}/{agent_name}/{skill_name}")
    return crud.success_message("deleted", "Skill")


@router.post("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}/toggle")
async def toggle_agent_skill_enabled(business_unit_id: str, agent_name: str, skill_name: str, enabled: bool):
    """Toggle Skill enabled status"""
    logger.info(f"Toggling Skill enabled status: {business_unit_id}/{agent_name}/{skill_name} -> {enabled}")
    if not business_unit_service.toggle_skill_enabled(business_unit_id, agent_name, skill_name, enabled):
        logger.warning(f"Skill  does not exist: {business_unit_id}/{agent_name}/{skill_name}")
        raise HTTPException(status_code=404, detail="Skill not found")
    logger.info(f"Skill 启用状态updated successfully: {skill_name}, enabled={enabled}")
    return {"message": "Skill enabled status updated successfully", "enabled": enabled}


# ==================== Model (Agent 下) ====================

@router.get("/{business_unit_id}/agents/{agent_name}/models", response_model=List[Model])
async def list_models(business_unit_id: str, agent_name: str):
    """Get Model list under Agent"""
    logger.debug(f"Fetching Model list: {business_unit_id}/{agent_name}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")
    models = business_unit_service.list_models(business_unit_id, agent_name)
    logger.debug(f"Agent {agent_name} contains {len(models)}  Model(s)")
    return models


@router.post("/{business_unit_id}/agents/{agent_name}/models", response_model=Model)
async def create_model(business_unit_id: str, agent_name: str, data: ModelCreate):
    """Create Model under Agent"""
    logger.info(f"Creating Model: {business_unit_id}/{agent_name}/{data.name}, type={data.model_type}")
    try:
        model = business_unit_service.create_model(business_unit_id, agent_name, data)
        logger.info(f"Model created successfully: {business_unit_id}/{agent_name}/{data.name}")
        return model
    except ValueError as e:
        logger.warning(f"Create Model failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def get_model(business_unit_id: str, agent_name: str, model_name: str):
    """Get Model 详情"""
    logger.debug(f"Fetching Model details: {business_unit_id}/{agent_name}/{model_name}")
    return handle_not_found(business_unit_service.get_model(business_unit_id, agent_name, model_name), "Model not found")


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}/config")
async def get_model_config(business_unit_id: str, agent_name: str, model_name: str):
    """Get Model 配置原始内容"""
    logger.debug(f"Fetching Model config: {business_unit_id}/{agent_name}/{model_name}")
    return crud.config_response(business_unit_service.get_model_config_content(business_unit_id, agent_name, model_name), "Model")


@router.put("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def update_model(business_unit_id: str, agent_name: str, model_name: str, update: ModelUpdate):
    """Update Model"""
    logger.info(f"Updating Model: {business_unit_id}/{agent_name}/{model_name}")
    result = handle_not_found(business_unit_service.update_model(business_unit_id, agent_name, model_name, update), "Model not found")
    logger.info(f"Model updated successfully: {business_unit_id}/{agent_name}/{model_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}")
async def delete_model(business_unit_id: str, agent_name: str, model_name: str):
    """Delete Model"""
    logger.info(f"Deleting Model: {business_unit_id}/{agent_name}/{model_name}")
    if not business_unit_service.delete_model(business_unit_id, agent_name, model_name):
        logger.warning(f"Model  does not exist: {business_unit_id}/{agent_name}/{model_name}")
        raise HTTPException(status_code=404, detail="Model not found")
    logger.info(f"Model deleted successfully: {business_unit_id}/{agent_name}/{model_name}")
    return crud.success_message("deleted", "Model")


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/enable")
async def enable_model(business_unit_id: str, agent_name: str, model_name: str):
    """Enable specified Model (disable all others)"""
    logger.info(f"Enabling Model: {business_unit_id}/{agent_name}/{model_name}")
    if not business_unit_service.enable_model(business_unit_id, agent_name, model_name):
        logger.warning(f"Model  does not exist: {business_unit_id}/{agent_name}/{model_name}")
        raise HTTPException(status_code=404, detail="Model not found")
    logger.info(f"Model enabled successfully: {business_unit_id}/{agent_name}/{model_name}")
    return {"message": "Model enabled successfully", "model_name": model_name}


# ==================== MCP (Agent 下) ====================

@router.get("/{business_unit_id}/agents/{agent_name}/mcps", response_model=List[MCP])
async def list_mcps(business_unit_id: str, agent_name: str):
    """Get Agent 下的 MCP 列表"""
    logger.debug(f"Fetching MCP list: {business_unit_id}/{agent_name}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")
    mcps = business_unit_service.list_mcps(business_unit_id, agent_name)
    logger.debug(f"Agent {agent_name} contains {len(mcps)}  MCP(s)")
    return mcps


@router.post("/{business_unit_id}/agents/{agent_name}/mcps", response_model=MCP)
async def create_mcp(business_unit_id: str, agent_name: str, data: MCPCreate):
    """Create MCP under Agent"""
    logger.info(f"Creating MCP: {business_unit_id}/{agent_name}/{data.name}, type={data.mcp_type}")
    try:
        mcp = business_unit_service.create_mcp(business_unit_id, agent_name, data)
        logger.info(f"MCP created successfully: {business_unit_id}/{agent_name}/{data.name}")
        return mcp
    except ValueError as e:
        logger.warning(f"Create MCP failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def get_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """Get MCP 详情"""
    logger.debug(f"Fetching MCP details: {business_unit_id}/{agent_name}/{mcp_name}")
    return handle_not_found(business_unit_service.get_mcp(business_unit_id, agent_name, mcp_name), "MCP not found")


@router.put("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def update_mcp(business_unit_id: str, agent_name: str, mcp_name: str, update: MCPUpdate):
    """Update MCP"""
    logger.info(f"Updating MCP: {business_unit_id}/{agent_name}/{mcp_name}")
    result = handle_not_found(business_unit_service.update_mcp(business_unit_id, agent_name, mcp_name, update), "MCP not found")
    logger.info(f"MCP updated successfully: {business_unit_id}/{agent_name}/{mcp_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}")
async def delete_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """Delete MCP"""
    logger.info(f"Deleting MCP: {business_unit_id}/{agent_name}/{mcp_name}")
    if not business_unit_service.delete_mcp(business_unit_id, agent_name, mcp_name):
        logger.warning(f"MCP  does not exist: {business_unit_id}/{agent_name}/{mcp_name}")
        raise HTTPException(status_code=404, detail="MCP not found")
    logger.info(f"MCP deleted successfully: {business_unit_id}/{agent_name}/{mcp_name}")
    return crud.success_message("deleted", "MCP")


@router.post("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}/toggle")
async def toggle_mcp_enabled(business_unit_id: str, agent_name: str, mcp_name: str, enabled: bool):
    """Toggle MCP enabled status"""
    logger.info(f"Toggling MCP enabled status: {business_unit_id}/{agent_name}/{mcp_name} -> {enabled}")
    mcp = business_unit_service.get_mcp(business_unit_id, agent_name, mcp_name)
    if not mcp:
        logger.warning(f"MCP  does not exist: {business_unit_id}/{agent_name}/{mcp_name}")
        raise HTTPException(status_code=404, detail="MCP not found")
    
    from app.models.business_unit import MCPUpdate as MCPUpdateModel
    result = business_unit_service.update_mcp(business_unit_id, agent_name, mcp_name, MCPUpdateModel(enabled=enabled))
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update MCP")
    
    logger.info(f"MCP 启用状态updated successfully: {mcp_name}, enabled={enabled}")
    return {"message": "MCP enabled status updated successfully", "enabled": enabled}
