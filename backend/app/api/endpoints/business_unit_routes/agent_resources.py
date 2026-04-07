"""Agent nested resource endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException

from app.api.endpoints.business_unit_routes.common import business_unit_service, crud, get_agent_service, handle_not_found, logger
from app.models.business_unit import (
    MCP,
    MCPCreate,
    MCPUpdate,
    Memory,
    MemoryCreate,
    MemoryUpdate,
    Model,
    ModelCreate,
    ModelUpdate,
)

router = APIRouter()


@router.get("/{business_unit_id}/agents/{agent_name}/memories", response_model=List[Memory])
async def list_agent_memories(business_unit_id: str, agent_name: str):
    """Return memories under an agent."""
    memories = handle_not_found(get_agent_service().list_memories(business_unit_id, agent_name), "Agent not found")
    return memories


@router.get("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}", response_model=Memory)
async def get_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """Return memory details."""
    return handle_not_found(get_agent_service().get_memory(business_unit_id, agent_name, memory_name), "Memory not found")


@router.post("/{business_unit_id}/agents/{agent_name}/memories")
async def create_agent_memory(business_unit_id: str, agent_name: str, data: MemoryCreate):
    """Create a memory under an agent."""
    try:
        if not get_agent_service().create_memory(business_unit_id, agent_name, data):
            raise HTTPException(status_code=404, detail="Agent not found")
        return crud.success_message("created", "Memory")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def update_agent_memory(business_unit_id: str, agent_name: str, memory_name: str, update: MemoryUpdate):
    """Update a memory."""
    if not get_agent_service().update_memory(business_unit_id, agent_name, memory_name, update):
        raise HTTPException(status_code=404, detail="Memory not found")
    return crud.success_message("updated", "Memory")


@router.delete("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def delete_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """Delete a memory."""
    if not get_agent_service().delete_memory(business_unit_id, agent_name, memory_name):
        raise HTTPException(status_code=404, detail="Memory not found")
    return crud.success_message("deleted", "Memory")


@router.post("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}/toggle")
async def toggle_agent_memory_enabled(business_unit_id: str, agent_name: str, memory_name: str, enabled: bool):
    """Toggle a memory enablement flag."""
    if not get_agent_service().toggle_memory_enabled(business_unit_id, agent_name, memory_name, enabled):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"message": "Memory enabled status updated successfully", "enabled": enabled}


@router.get("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def get_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """Return skill content."""
    result = handle_not_found(get_agent_service().get_skill(business_unit_id, agent_name, skill_name), "Skill not found")
    return {"name": skill_name, "content": result["content"], "path": result["path"]}


@router.delete("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def delete_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """Delete a skill."""
    if not get_agent_service().delete_skill(business_unit_id, agent_name, skill_name):
        raise HTTPException(status_code=404, detail="Skill not found")
    return crud.success_message("deleted", "Skill")


@router.post("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}/toggle")
async def toggle_agent_skill_enabled(business_unit_id: str, agent_name: str, skill_name: str, enabled: bool):
    """Toggle a skill enablement flag."""
    if not get_agent_service().toggle_skill_enabled(business_unit_id, agent_name, skill_name, enabled):
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill enabled status updated successfully", "enabled": enabled}


@router.get("/{business_unit_id}/agents/{agent_name}/models", response_model=List[Model])
async def list_models(business_unit_id: str, agent_name: str):
    """Return models under an agent."""
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(get_agent_service().get_agent(business_unit_id, agent_name), "Agent not found")
    return get_agent_service().list_models(business_unit_id, agent_name)


@router.post("/{business_unit_id}/agents/{agent_name}/models", response_model=Model)
async def create_model(business_unit_id: str, agent_name: str, data: ModelCreate):
    """Create a model under an agent."""
    try:
        return get_agent_service().create_model(business_unit_id, agent_name, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def get_model(business_unit_id: str, agent_name: str, model_name: str):
    """Return model details."""
    return handle_not_found(get_agent_service().get_model(business_unit_id, agent_name, model_name), "Model not found")


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}/config")
async def get_model_config(business_unit_id: str, agent_name: str, model_name: str):
    """Return raw model config content."""
    return crud.config_response(get_agent_service().get_model_config_content(business_unit_id, agent_name, model_name), "Model")


@router.put("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def update_model(business_unit_id: str, agent_name: str, model_name: str, update: ModelUpdate):
    """Update a model."""
    return handle_not_found(get_agent_service().update_model(business_unit_id, agent_name, model_name, update), "Model not found")


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}")
async def delete_model(business_unit_id: str, agent_name: str, model_name: str):
    """Delete a model."""
    if not get_agent_service().delete_model(business_unit_id, agent_name, model_name):
        raise HTTPException(status_code=404, detail="Model not found")
    return crud.success_message("deleted", "Model")


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/enable")
async def enable_model(business_unit_id: str, agent_name: str, model_name: str):
    """Enable a model and disable others under the same agent."""
    if not get_agent_service().enable_model(business_unit_id, agent_name, model_name):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model enabled successfully", "model_name": model_name}


@router.get("/{business_unit_id}/agents/{agent_name}/mcps", response_model=List[MCP])
async def list_mcps(business_unit_id: str, agent_name: str):
    """Return MCP configs under an agent."""
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(get_agent_service().get_agent(business_unit_id, agent_name), "Agent not found")
    return get_agent_service().list_mcps(business_unit_id, agent_name)


@router.post("/{business_unit_id}/agents/{agent_name}/mcps", response_model=MCP)
async def create_mcp(business_unit_id: str, agent_name: str, data: MCPCreate):
    """Create an MCP under an agent."""
    try:
        return get_agent_service().create_mcp(business_unit_id, agent_name, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def get_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """Return MCP details."""
    return handle_not_found(get_agent_service().get_mcp(business_unit_id, agent_name, mcp_name), "MCP not found")


@router.put("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def update_mcp(business_unit_id: str, agent_name: str, mcp_name: str, update: MCPUpdate):
    """Update an MCP."""
    return handle_not_found(get_agent_service().update_mcp(business_unit_id, agent_name, mcp_name, update), "MCP not found")


@router.delete("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}")
async def delete_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """Delete an MCP."""
    if not get_agent_service().delete_mcp(business_unit_id, agent_name, mcp_name):
        raise HTTPException(status_code=404, detail="MCP not found")
    return crud.success_message("deleted", "MCP")


@router.post("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}/toggle")
async def toggle_mcp_enabled(business_unit_id: str, agent_name: str, mcp_name: str, enabled: bool):
    """Toggle an MCP enablement flag."""
    result = handle_not_found(get_agent_service().get_mcp(business_unit_id, agent_name, mcp_name), "MCP not found")
    updated = get_agent_service().update_mcp(
        business_unit_id,
        agent_name,
        mcp_name,
        MCPUpdate(enabled=enabled),
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to update MCP")
    logger.info("Toggled MCP %s/%s/%s to enabled=%s", business_unit_id, agent_name, result.name, enabled)
    return {"message": "MCP enabled status updated successfully", "enabled": enabled}
