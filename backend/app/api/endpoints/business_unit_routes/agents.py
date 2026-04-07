"""Agent CRUD and output endpoints."""

from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.api.endpoints.business_unit_routes.common import business_unit_service, crud, get_agent_service, handle_not_found, logger
from app.api.endpoints.business_unit_routes.schemas import OutputFileContentResponse, OutputFileSaveRequest, SkillImportRequest
from app.models.business_unit import Agent, AgentCreate, AgentUpdate

router = APIRouter()


@router.get("/{business_unit_id}/agents", response_model=List[Agent])
async def list_agents(business_unit_id: str):
    """Return agents under a business unit."""
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    agents = get_agent_service().list_agents(business_unit_id)
    logger.debug("Business unit %s contains %s agent(s)", business_unit_id, len(agents))
    return agents


@router.post("/{business_unit_id}/agents", response_model=Agent)
async def create_agent(business_unit_id: str, data: AgentCreate):
    """Create an agent."""
    try:
        return business_unit_service.create_agent(business_unit_id, data)
    except ValueError as exc:
        logger.warning("Failed to create agent %s/%s: %s", business_unit_id, data.name, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def get_agent(business_unit_id: str, agent_name: str):
    """Return agent details."""
    return handle_not_found(get_agent_service().get_agent(business_unit_id, agent_name), "Agent not found")


@router.get("/{business_unit_id}/agents/{agent_name}/config")
async def get_agent_config(business_unit_id: str, agent_name: str):
    """Return raw agent config content."""
    return crud.config_response(get_agent_service().get_agent_config_content(business_unit_id, agent_name), "Agent")


@router.get("/{business_unit_id}/agents/{agent_name}/output/file", response_model=OutputFileContentResponse)
async def get_agent_output_file_content(
    business_unit_id: str,
    agent_name: str,
    path: str = Query(..., description="Relative path under output"),
):
    """Read a text file under agent output."""
    try:
        return business_unit_service.get_output_file_content(business_unit_id, agent_name, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{business_unit_id}/agents/{agent_name}/output/file", response_model=OutputFileContentResponse)
async def save_agent_output_file_content(
    business_unit_id: str,
    agent_name: str,
    request: OutputFileSaveRequest,
):
    """Save edited content to an agent output file."""
    try:
        return business_unit_service.save_output_file_content(
            business_unit_id,
            agent_name,
            request.path,
            request.content,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def update_agent(business_unit_id: str, agent_name: str, update: AgentUpdate):
    """Update an agent."""
    result = handle_not_found(get_agent_service().update_agent(business_unit_id, agent_name, update), "Agent not found")
    logger.info("Updated agent: %s/%s", business_unit_id, agent_name)
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}")
async def delete_agent(business_unit_id: str, agent_name: str):
    """Delete an agent."""
    if not get_agent_service().delete_agent(business_unit_id, agent_name):
        logger.warning("Agent not found for delete: %s/%s", business_unit_id, agent_name)
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info("Deleted agent: %s/%s", business_unit_id, agent_name)
    return crud.success_message("deleted", "Agent")


@router.post("/{business_unit_id}/agents/{agent_name}/skills/import")
async def import_agent_skill(business_unit_id: str, agent_name: str, request: SkillImportRequest):
    """Import a skill zip file into an agent."""
    zip_path = Path(request.zip_file_path)
    if not zip_path.exists():
        raise HTTPException(status_code=400, detail="File does not exist")
    if not zip_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    if zip_path.suffix.lower() != ".zip":
        raise HTTPException(status_code=400, detail="Only zip format files are supported")

    result = get_agent_service().import_skill_from_zip(business_unit_id, agent_name, zip_path, zip_path.name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    logger.info("Imported skill into agent %s/%s: %s", business_unit_id, agent_name, result.get("skill_name", "unknown"))
    return result
