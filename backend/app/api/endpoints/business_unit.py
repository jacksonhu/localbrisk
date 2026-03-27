"""
BusinessUnit API 端点
提供 BusinessUnit、AssetBundle、Asset、Agent、Model、MCP、Memory、Skill 的 CRUD 操作
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
    """output 文件内容响应"""
    path: str
    relative_path: str
    content: str


# ==================== BusinessUnit ====================

@router.get("", response_model=List[BusinessUnit])
async def list_business_units():
    """获取所有 BusinessUnit"""
    logger.debug("获取所有 BusinessUnit 列表")
    business_units = business_unit_service.discover_business_units()
    logger.info(f"发现 {len(business_units)} 个 BusinessUnit")
    return business_units


@router.post("", response_model=BusinessUnit)
async def create_business_unit(data: BusinessUnitCreate):
    """创建 BusinessUnit"""
    logger.info(f"创建 BusinessUnit: {data.name}")
    try:
        bu = business_unit_service.create_business_unit(data)
        logger.info(f"BusinessUnit 创建成功: {data.name}")
        return bu
    except ValueError as e:
        logger.warning(f"创建 BusinessUnit 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree", response_model=List[BusinessUnitTreeNode])
async def get_business_unit_tree():
    """获取 BusinessUnit 导航树"""
    logger.debug("获取 BusinessUnit 导航树")
    tree = business_unit_service.get_business_unit_tree()
    logger.debug(f"导航树包含 {len(tree)} 个根节点")
    return tree


@router.get("/{business_unit_id}", response_model=BusinessUnit)
async def get_business_unit(business_unit_id: str):
    """获取 BusinessUnit 详情"""
    logger.debug(f"获取 BusinessUnit 详情: {business_unit_id}")
    return handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")


@router.get("/{business_unit_id}/config")
async def get_business_unit_config(business_unit_id: str):
    """获取 BusinessUnit 配置文件原始内容"""
    logger.debug(f"获取 BusinessUnit 配置: {business_unit_id}")
    return crud.config_response(business_unit_service.get_business_unit_config_content(business_unit_id), "BusinessUnit")


@router.put("/{business_unit_id}", response_model=BusinessUnit)
async def update_business_unit(business_unit_id: str, update: BusinessUnitUpdate):
    """更新 BusinessUnit"""
    logger.info(f"更新 BusinessUnit: {business_unit_id}")
    result = handle_not_found(business_unit_service.update_business_unit(business_unit_id, update), "BusinessUnit not found")
    logger.info(f"BusinessUnit 更新成功: {business_unit_id}")
    return result


@router.delete("/{business_unit_id}")
async def delete_business_unit(business_unit_id: str):
    """删除 BusinessUnit"""
    logger.info(f"删除 BusinessUnit: {business_unit_id}")
    if not business_unit_service.delete_business_unit(business_unit_id):
        logger.warning(f"BusinessUnit 不存在: {business_unit_id}")
        raise HTTPException(status_code=404, detail="BusinessUnit not found")
    logger.info(f"BusinessUnit 删除成功: {business_unit_id}")
    return crud.success_message("deleted", "BusinessUnit")


# ==================== AssetBundle ====================

@router.get("/{business_unit_id}/asset_bundles", response_model=List[AssetBundle])
async def list_asset_bundles(business_unit_id: str):
    """获取 AssetBundle 列表"""
    logger.debug(f"获取 AssetBundle 列表: business_unit={business_unit_id}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    bundles = business_unit_service.get_asset_bundles(business_unit_id)
    logger.debug(f"BusinessUnit {business_unit_id} 包含 {len(bundles)} 个 AssetBundle")
    return bundles


@router.post("/{business_unit_id}/asset_bundles", response_model=AssetBundle)
async def create_asset_bundle(business_unit_id: str, data: AssetBundleCreate):
    """创建 AssetBundle"""
    logger.info(f"创建 AssetBundle: business_unit={business_unit_id}, name={data.name}")
    try:
        bundle = business_unit_service.create_asset_bundle(business_unit_id, data)
        logger.info(f"AssetBundle 创建成功: {business_unit_id}/{data.name}")
        return bundle
    except ValueError as e:
        logger.warning(f"创建 AssetBundle 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def get_asset_bundle(business_unit_id: str, bundle_name: str):
    """获取 AssetBundle 详情"""
    logger.debug(f"获取 AssetBundle 详情: {business_unit_id}/{bundle_name}")
    for bundle in business_unit_service.get_asset_bundles(business_unit_id):
        if bundle.name == bundle_name:
            return bundle
    logger.warning(f"AssetBundle 不存在: {business_unit_id}/{bundle_name}")
    raise HTTPException(status_code=404, detail="AssetBundle not found")


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/config")
async def get_asset_bundle_config(business_unit_id: str, bundle_name: str):
    """获取 AssetBundle 配置原始内容"""
    logger.debug(f"获取 AssetBundle 配置: {business_unit_id}/{bundle_name}")
    return crud.config_response(business_unit_service.get_asset_bundle_config_content(business_unit_id, bundle_name), "AssetBundle")


@router.put("/{business_unit_id}/asset_bundles/{bundle_name}", response_model=AssetBundle)
async def update_asset_bundle(business_unit_id: str, bundle_name: str, update: AssetBundleUpdate):
    """更新 AssetBundle"""
    logger.info(f"更新 AssetBundle: {business_unit_id}/{bundle_name}")
    result = handle_not_found(business_unit_service.update_asset_bundle(business_unit_id, bundle_name, update), "AssetBundle not found")
    logger.info(f"AssetBundle 更新成功: {business_unit_id}/{bundle_name}")
    return result


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}")
async def delete_asset_bundle(business_unit_id: str, bundle_name: str):
    """删除 AssetBundle"""
    logger.info(f"删除 AssetBundle: {business_unit_id}/{bundle_name}")
    if not business_unit_service.delete_asset_bundle(business_unit_id, bundle_name):
        logger.warning(f"AssetBundle 不存在: {business_unit_id}/{bundle_name}")
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    logger.info(f"AssetBundle 删除成功: {business_unit_id}/{bundle_name}")
    return crud.success_message("deleted", "AssetBundle")


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/sync", response_model=SyncResult)
async def sync_asset_bundle_metadata(business_unit_id: str, bundle_name: str):
    """同步 AssetBundle 元数据"""
    logger.info(f"同步 AssetBundle 元数据: {business_unit_id}/{bundle_name}")
    result = business_unit_service.sync_asset_bundle_metadata(business_unit_id, bundle_name)
    if not result.success and "不存在" in str(result.errors):
        logger.warning(f"AssetBundle 不存在: {business_unit_id}/{bundle_name}")
        raise HTTPException(status_code=404, detail="AssetBundle not found")
    if result.success:
        logger.info(f"AssetBundle 元数据同步成功: {business_unit_id}/{bundle_name}")
    else:
        logger.warning(f"AssetBundle 元数据同步失败: {result.errors}")
    return result


# ==================== Asset ====================

@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=List[Asset])
async def list_assets(business_unit_id: str, bundle_name: str):
    """获取 Asset 列表"""
    logger.debug(f"获取 Asset 列表: {business_unit_id}/{bundle_name}")
    assets = business_unit_service.scan_assets(business_unit_id, bundle_name)
    logger.debug(f"AssetBundle {bundle_name} 包含 {len(assets)} 个 Asset")
    return assets


@router.post("/{business_unit_id}/asset_bundles/{bundle_name}/assets", response_model=Asset)
async def create_asset(business_unit_id: str, bundle_name: str, data: AssetCreate):
    """创建 Asset"""
    logger.info(f"创建 Asset: {business_unit_id}/{bundle_name}/{data.name}, type={data.asset_type}")
    try:
        asset = business_unit_service.create_asset(business_unit_id, bundle_name, data)
        logger.info(f"Asset 创建成功: {business_unit_id}/{bundle_name}/{data.name}")
        return asset
    except (ValueError, FileNotFoundError) as e:
        status = 404 if isinstance(e, FileNotFoundError) else 400
        logger.warning(f"创建 Asset 失败: {e}")
        raise HTTPException(status_code=status, detail=str(e))


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}/config")
async def get_asset_config(business_unit_id: str, bundle_name: str, asset_name: str):
    """获取 Asset 配置原始内容"""
    logger.debug(f"获取 Asset 配置: {business_unit_id}/{bundle_name}/{asset_name}")
    return crud.config_response(business_unit_service.get_asset_config_content(business_unit_id, bundle_name, asset_name), "Asset")


@router.delete("/{business_unit_id}/asset_bundles/{bundle_name}/assets/{asset_name}")
async def delete_asset(business_unit_id: str, bundle_name: str, asset_name: str):
    """删除 Asset"""
    logger.info(f"删除 Asset: {business_unit_id}/{bundle_name}/{asset_name}")
    if not business_unit_service.delete_asset(business_unit_id, bundle_name, asset_name):
        logger.warning(f"Asset 不存在: {business_unit_id}/{bundle_name}/{asset_name}")
        raise HTTPException(status_code=404, detail="Asset not found")
    logger.info(f"Asset 删除成功: {business_unit_id}/{bundle_name}/{asset_name}")
    return crud.success_message("deleted", "Asset")


@router.get("/{business_unit_id}/asset_bundles/{bundle_name}/tables/{table_name}/preview")
async def preview_table_data(business_unit_id: str, bundle_name: str, table_name: str, limit: int = 100, offset: int = 0):
    """预览表数据"""
    logger.debug(f"预览表数据: {business_unit_id}/{bundle_name}/{table_name}, limit={limit}, offset={offset}")
    try:
        result = business_unit_service.preview_table_data(business_unit_id, bundle_name, table_name, limit, offset)
        logger.debug(f"表数据预览成功: {table_name}")
        return result
    except ValueError as e:
        logger.warning(f"预览表数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Agent ====================

@router.get("/{business_unit_id}/agents", response_model=List[Agent])
async def list_agents(business_unit_id: str):
    """获取 Agent 列表"""
    logger.debug(f"获取 Agent 列表: business_unit={business_unit_id}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    agents = business_unit_service.list_agents(business_unit_id)
    logger.debug(f"BusinessUnit {business_unit_id} 包含 {len(agents)} 个 Agent")
    return agents


@router.post("/{business_unit_id}/agents", response_model=Agent)
async def create_agent(business_unit_id: str, data: AgentCreate):
    """创建 Agent"""
    logger.info(f"创建 Agent: business_unit={business_unit_id}, name={data.name}")
    try:
        agent = business_unit_service.create_agent(business_unit_id, data)
        logger.info(f"Agent 创建成功: {business_unit_id}/{data.name}")
        return agent
    except ValueError as e:
        logger.warning(f"创建 Agent 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def get_agent(business_unit_id: str, agent_name: str):
    """获取 Agent 详情"""
    logger.debug(f"获取 Agent 详情: {business_unit_id}/{agent_name}")
    return handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")


@router.get("/{business_unit_id}/agents/{agent_name}/config")
async def get_agent_config(business_unit_id: str, agent_name: str):
    """获取 Agent 配置原始内容"""
    logger.debug(f"获取 Agent 配置: {business_unit_id}/{agent_name}")
    return crud.config_response(business_unit_service.get_agent_config_content(business_unit_id, agent_name), "Agent")


@router.get("/{business_unit_id}/agents/{agent_name}/output/file", response_model=OutputFileContentResponse)
async def get_agent_output_file_content(
    business_unit_id: str,
    agent_name: str,
    path: str = Query(..., description="output 下的相对路径"),
):
    """读取 Agent output 下指定文件内容"""
    logger.debug(f"读取 Agent output 文件: {business_unit_id}/{agent_name}, path={path}")
    try:
        return business_unit_service.get_output_file_content(business_unit_id, agent_name, path)
    except FileNotFoundError as e:
        logger.warning(f"output 文件不存在: {business_unit_id}/{agent_name}, path={path}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.warning(f"output 路径非法或文件不可读: {business_unit_id}/{agent_name}, path={path}, error={e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{business_unit_id}/agents/{agent_name}", response_model=Agent)
async def update_agent(business_unit_id: str, agent_name: str, update: AgentUpdate):
    """更新 Agent"""
    logger.info(f"更新 Agent: {business_unit_id}/{agent_name}")
    result = handle_not_found(business_unit_service.update_agent(business_unit_id, agent_name, update), "Agent not found")
    logger.info(f"Agent 更新成功: {business_unit_id}/{agent_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}")
async def delete_agent(business_unit_id: str, agent_name: str):
    """删除 Agent"""
    logger.info(f"删除 Agent: {business_unit_id}/{agent_name}")
    if not business_unit_service.delete_agent(business_unit_id, agent_name):
        logger.warning(f"Agent 不存在: {business_unit_id}/{agent_name}")
        raise HTTPException(status_code=404, detail="Agent not found")
    logger.info(f"Agent 删除成功: {business_unit_id}/{agent_name}")
    return crud.success_message("deleted", "Agent")


# ==================== Memory ====================

@router.get("/{business_unit_id}/agents/{agent_name}/memories", response_model=List[Memory])
async def list_agent_memories(business_unit_id: str, agent_name: str):
    """获取 Memory 列表"""
    logger.debug(f"获取 Memory 列表: {business_unit_id}/{agent_name}")
    memories = handle_not_found(business_unit_service.list_agent_memories(business_unit_id, agent_name), "Agent not found")
    logger.debug(f"Agent {agent_name} 包含 {len(memories) if memories else 0} 个 Memory")
    return memories


@router.get("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}", response_model=Memory)
async def get_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """获取 Memory 详情"""
    logger.debug(f"获取 Memory 详情: {business_unit_id}/{agent_name}/{memory_name}")
    return handle_not_found(business_unit_service.get_agent_memory_detail(business_unit_id, agent_name, memory_name), "Memory not found")


@router.post("/{business_unit_id}/agents/{agent_name}/memories")
async def create_agent_memory(business_unit_id: str, agent_name: str, data: MemoryCreate):
    """创建 Memory"""
    logger.info(f"创建 Memory: {business_unit_id}/{agent_name}/{data.name}")
    try:
        if not business_unit_service.create_agent_memory(business_unit_id, agent_name, data):
            logger.warning(f"Agent 不存在: {business_unit_id}/{agent_name}")
            raise HTTPException(status_code=404, detail="Agent not found")
        logger.info(f"Memory 创建成功: {business_unit_id}/{agent_name}/{data.name}")
        return crud.success_message("created", "Memory")
    except ValueError as e:
        logger.warning(f"创建 Memory 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def update_agent_memory(business_unit_id: str, agent_name: str, memory_name: str, update: MemoryUpdate):
    """更新 Memory"""
    logger.info(f"更新 Memory: {business_unit_id}/{agent_name}/{memory_name}")
    if not business_unit_service.update_agent_memory(business_unit_id, agent_name, memory_name, update):
        logger.warning(f"Memory 不存在: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory 更新成功: {business_unit_id}/{agent_name}/{memory_name}")
    return crud.success_message("updated", "Memory")


@router.delete("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}")
async def delete_agent_memory(business_unit_id: str, agent_name: str, memory_name: str):
    """删除 Memory"""
    logger.info(f"删除 Memory: {business_unit_id}/{agent_name}/{memory_name}")
    if not business_unit_service.delete_agent_memory(business_unit_id, agent_name, memory_name):
        logger.warning(f"Memory 不存在: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory 删除成功: {business_unit_id}/{agent_name}/{memory_name}")
    return crud.success_message("deleted", "Memory")


@router.post("/{business_unit_id}/agents/{agent_name}/memories/{memory_name}/toggle")
async def toggle_agent_memory_enabled(business_unit_id: str, agent_name: str, memory_name: str, enabled: bool):
    """切换 Memory 启用状态"""
    logger.info(f"切换 Memory 启用状态: {business_unit_id}/{agent_name}/{memory_name} -> {enabled}")
    if not business_unit_service.toggle_memory_enabled(business_unit_id, agent_name, memory_name, enabled):
        logger.warning(f"Memory 不存在: {business_unit_id}/{agent_name}/{memory_name}")
        raise HTTPException(status_code=404, detail="Memory not found")
    logger.info(f"Memory 启用状态更新成功: {memory_name}, enabled={enabled}")
    return {"message": "Memory enabled status updated successfully", "enabled": enabled}


# ==================== Skill ====================

class SkillImportRequest(BaseModel):
    """Skill 导入请求"""
    zip_file_path: str


@router.post("/{business_unit_id}/agents/{agent_name}/skills/import")
async def import_agent_skill(business_unit_id: str, agent_name: str, request: SkillImportRequest):
    """从本地 zip 文件导入 Skill"""
    logger.info(f"导入 Skill: {business_unit_id}/{agent_name}, file={request.zip_file_path}")
    zip_path = Path(request.zip_file_path)
    
    if not zip_path.exists():
        logger.warning(f"zip 文件不存在: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="文件不存在")
    if not zip_path.is_file():
        logger.warning(f"路径不是文件: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="路径不是文件")
    if zip_path.suffix.lower() != '.zip':
        logger.warning(f"不是 zip 文件: {request.zip_file_path}")
        raise HTTPException(status_code=400, detail="只支持 zip 格式文件")
    
    result = business_unit_service.import_skill_from_zip(business_unit_id, agent_name, zip_path, zip_path.name)
    if not result["success"]:
        logger.warning(f"导入 Skill 失败: {result['message']}")
        raise HTTPException(status_code=400, detail=result["message"])
    logger.info(f"Skill 导入成功: {result.get('skill_name', 'unknown')}")
    return result


@router.get("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def get_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """获取 Skill 内容"""
    logger.debug(f"获取 Skill: {business_unit_id}/{agent_name}/{skill_name}")
    result = handle_not_found(business_unit_service.get_agent_skill(business_unit_id, agent_name, skill_name), "Skill not found")
    return {"name": skill_name, "content": result["content"], "path": result["path"]}


@router.delete("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}")
async def delete_agent_skill(business_unit_id: str, agent_name: str, skill_name: str):
    """删除 Skill"""
    logger.info(f"删除 Skill: {business_unit_id}/{agent_name}/{skill_name}")
    if not business_unit_service.delete_agent_skill(business_unit_id, agent_name, skill_name):
        logger.warning(f"Skill 不存在: {business_unit_id}/{agent_name}/{skill_name}")
        raise HTTPException(status_code=404, detail="Skill not found")
    logger.info(f"Skill 删除成功: {business_unit_id}/{agent_name}/{skill_name}")
    return crud.success_message("deleted", "Skill")


@router.post("/{business_unit_id}/agents/{agent_name}/skills/{skill_name}/toggle")
async def toggle_agent_skill_enabled(business_unit_id: str, agent_name: str, skill_name: str, enabled: bool):
    """切换 Skill 启用状态"""
    logger.info(f"切换 Skill 启用状态: {business_unit_id}/{agent_name}/{skill_name} -> {enabled}")
    if not business_unit_service.toggle_skill_enabled(business_unit_id, agent_name, skill_name, enabled):
        logger.warning(f"Skill 不存在: {business_unit_id}/{agent_name}/{skill_name}")
        raise HTTPException(status_code=404, detail="Skill not found")
    logger.info(f"Skill 启用状态更新成功: {skill_name}, enabled={enabled}")
    return {"message": "Skill enabled status updated successfully", "enabled": enabled}


# ==================== Model (Agent 下) ====================

@router.get("/{business_unit_id}/agents/{agent_name}/models", response_model=List[Model])
async def list_models(business_unit_id: str, agent_name: str):
    """获取 Agent 下的 Model 列表"""
    logger.debug(f"获取 Model 列表: {business_unit_id}/{agent_name}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")
    models = business_unit_service.list_models(business_unit_id, agent_name)
    logger.debug(f"Agent {agent_name} 包含 {len(models)} 个 Model")
    return models


@router.post("/{business_unit_id}/agents/{agent_name}/models", response_model=Model)
async def create_model(business_unit_id: str, agent_name: str, data: ModelCreate):
    """在 Agent 下创建 Model"""
    logger.info(f"创建 Model: {business_unit_id}/{agent_name}/{data.name}, type={data.model_type}")
    try:
        model = business_unit_service.create_model(business_unit_id, agent_name, data)
        logger.info(f"Model 创建成功: {business_unit_id}/{agent_name}/{data.name}")
        return model
    except ValueError as e:
        logger.warning(f"创建 Model 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def get_model(business_unit_id: str, agent_name: str, model_name: str):
    """获取 Model 详情"""
    logger.debug(f"获取 Model 详情: {business_unit_id}/{agent_name}/{model_name}")
    return handle_not_found(business_unit_service.get_model(business_unit_id, agent_name, model_name), "Model not found")


@router.get("/{business_unit_id}/agents/{agent_name}/models/{model_name}/config")
async def get_model_config(business_unit_id: str, agent_name: str, model_name: str):
    """获取 Model 配置原始内容"""
    logger.debug(f"获取 Model 配置: {business_unit_id}/{agent_name}/{model_name}")
    return crud.config_response(business_unit_service.get_model_config_content(business_unit_id, agent_name, model_name), "Model")


@router.put("/{business_unit_id}/agents/{agent_name}/models/{model_name}", response_model=Model)
async def update_model(business_unit_id: str, agent_name: str, model_name: str, update: ModelUpdate):
    """更新 Model"""
    logger.info(f"更新 Model: {business_unit_id}/{agent_name}/{model_name}")
    result = handle_not_found(business_unit_service.update_model(business_unit_id, agent_name, model_name, update), "Model not found")
    logger.info(f"Model 更新成功: {business_unit_id}/{agent_name}/{model_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}/models/{model_name}")
async def delete_model(business_unit_id: str, agent_name: str, model_name: str):
    """删除 Model"""
    logger.info(f"删除 Model: {business_unit_id}/{agent_name}/{model_name}")
    if not business_unit_service.delete_model(business_unit_id, agent_name, model_name):
        logger.warning(f"Model 不存在: {business_unit_id}/{agent_name}/{model_name}")
        raise HTTPException(status_code=404, detail="Model not found")
    logger.info(f"Model 删除成功: {business_unit_id}/{agent_name}/{model_name}")
    return crud.success_message("deleted", "Model")


@router.post("/{business_unit_id}/agents/{agent_name}/models/{model_name}/enable")
async def enable_model(business_unit_id: str, agent_name: str, model_name: str):
    """启用指定 Model（同时禁用其他 Model）"""
    logger.info(f"启用 Model: {business_unit_id}/{agent_name}/{model_name}")
    if not business_unit_service.enable_model(business_unit_id, agent_name, model_name):
        logger.warning(f"Model 不存在: {business_unit_id}/{agent_name}/{model_name}")
        raise HTTPException(status_code=404, detail="Model not found")
    logger.info(f"Model 启用成功: {business_unit_id}/{agent_name}/{model_name}")
    return {"message": "Model enabled successfully", "model_name": model_name}


# ==================== MCP (Agent 下) ====================

@router.get("/{business_unit_id}/agents/{agent_name}/mcps", response_model=List[MCP])
async def list_mcps(business_unit_id: str, agent_name: str):
    """获取 Agent 下的 MCP 列表"""
    logger.debug(f"获取 MCP 列表: {business_unit_id}/{agent_name}")
    handle_not_found(business_unit_service.get_business_unit(business_unit_id), "BusinessUnit not found")
    handle_not_found(business_unit_service.get_agent(business_unit_id, agent_name), "Agent not found")
    mcps = business_unit_service.list_mcps(business_unit_id, agent_name)
    logger.debug(f"Agent {agent_name} 包含 {len(mcps)} 个 MCP")
    return mcps


@router.post("/{business_unit_id}/agents/{agent_name}/mcps", response_model=MCP)
async def create_mcp(business_unit_id: str, agent_name: str, data: MCPCreate):
    """在 Agent 下创建 MCP"""
    logger.info(f"创建 MCP: {business_unit_id}/{agent_name}/{data.name}, type={data.mcp_type}")
    try:
        mcp = business_unit_service.create_mcp(business_unit_id, agent_name, data)
        logger.info(f"MCP 创建成功: {business_unit_id}/{agent_name}/{data.name}")
        return mcp
    except ValueError as e:
        logger.warning(f"创建 MCP 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def get_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """获取 MCP 详情"""
    logger.debug(f"获取 MCP 详情: {business_unit_id}/{agent_name}/{mcp_name}")
    return handle_not_found(business_unit_service.get_mcp(business_unit_id, agent_name, mcp_name), "MCP not found")


@router.put("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}", response_model=MCP)
async def update_mcp(business_unit_id: str, agent_name: str, mcp_name: str, update: MCPUpdate):
    """更新 MCP"""
    logger.info(f"更新 MCP: {business_unit_id}/{agent_name}/{mcp_name}")
    result = handle_not_found(business_unit_service.update_mcp(business_unit_id, agent_name, mcp_name, update), "MCP not found")
    logger.info(f"MCP 更新成功: {business_unit_id}/{agent_name}/{mcp_name}")
    return result


@router.delete("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}")
async def delete_mcp(business_unit_id: str, agent_name: str, mcp_name: str):
    """删除 MCP"""
    logger.info(f"删除 MCP: {business_unit_id}/{agent_name}/{mcp_name}")
    if not business_unit_service.delete_mcp(business_unit_id, agent_name, mcp_name):
        logger.warning(f"MCP 不存在: {business_unit_id}/{agent_name}/{mcp_name}")
        raise HTTPException(status_code=404, detail="MCP not found")
    logger.info(f"MCP 删除成功: {business_unit_id}/{agent_name}/{mcp_name}")
    return crud.success_message("deleted", "MCP")


@router.post("/{business_unit_id}/agents/{agent_name}/mcps/{mcp_name}/toggle")
async def toggle_mcp_enabled(business_unit_id: str, agent_name: str, mcp_name: str, enabled: bool):
    """切换 MCP 启用状态"""
    logger.info(f"切换 MCP 启用状态: {business_unit_id}/{agent_name}/{mcp_name} -> {enabled}")
    mcp = business_unit_service.get_mcp(business_unit_id, agent_name, mcp_name)
    if not mcp:
        logger.warning(f"MCP 不存在: {business_unit_id}/{agent_name}/{mcp_name}")
        raise HTTPException(status_code=404, detail="MCP not found")
    
    from app.models.business_unit import MCPUpdate as MCPUpdateModel
    result = business_unit_service.update_mcp(business_unit_id, agent_name, mcp_name, MCPUpdateModel(enabled=enabled))
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update MCP")
    
    logger.info(f"MCP 启用状态更新成功: {mcp_name}, enabled={enabled}")
    return {"message": "MCP enabled status updated successfully", "enabled": enabled}
