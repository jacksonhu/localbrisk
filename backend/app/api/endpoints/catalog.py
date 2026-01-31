"""
Catalog 管理端点
提供 Catalog、Schema、Asset、Agent、Model 等资源的 CRUD 操作

树形结构：
├── Catalog (Namespace)
│   ├── agents/{agent_name}/
│   │   ├── agent_spec.yaml
│   │   ├── prompts/
│   │   └── skills/
│   └── schemas/{schema_name}/
│       ├── schema.yaml
│       ├── models/
│       ├── tables/
│       ├── functions/
│       └── volumes/
"""

import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.catalog import (
    Catalog,
    CatalogCreate,
    CatalogUpdate,
    CatalogTreeNode,
    Schema,
    SchemaCreate,
    SchemaUpdate,
    Asset,
    AssetCreate,
    Agent,
    AgentCreate,
    AgentUpdate,
    Model,
    ModelCreate,
    ModelUpdate,
    Prompt,
    PromptCreate,
    PromptUpdate,
)
from app.models.metadata import SyncResult
from app.services.catalog_service import catalog_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Catalog ====================

@router.get("", response_model=List[Catalog])
async def list_catalogs():
    """获取所有 Catalog"""
    return catalog_service.discover_catalogs()


@router.post("", response_model=Catalog)
async def create_catalog(catalog: CatalogCreate):
    """创建 Catalog"""
    try:
        return catalog_service.create_catalog(catalog)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree", response_model=List[CatalogTreeNode])
async def get_catalog_tree():
    """获取 Catalog 导航树"""
    return catalog_service.get_catalog_tree()


@router.get("/{catalog_id}", response_model=Catalog)
async def get_catalog(catalog_id: str):
    """获取 Catalog 详情"""
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog


@router.put("/{catalog_id}", response_model=Catalog)
async def update_catalog(catalog_id: str, update: CatalogUpdate):
    """更新 Catalog"""
    try:
        catalog = catalog_service.update_catalog(catalog_id, update)
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")
        return catalog
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}")
async def delete_catalog(catalog_id: str):
    """删除 Catalog"""
    if not catalog_service.delete_catalog(catalog_id):
        raise HTTPException(status_code=404, detail="Catalog not found")
    return {"message": "Catalog deleted successfully"}


# ==================== Schema ====================

@router.get("/{catalog_id}/schemas", response_model=List[Schema])
async def list_schemas(catalog_id: str):
    """获取 Schema 列表"""
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog.schemas


@router.post("/{catalog_id}/schemas", response_model=Schema)
async def create_schema(catalog_id: str, schema: SchemaCreate):
    """创建 Schema"""
    try:
        return catalog_service.create_schema(catalog_id, schema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{catalog_id}/schemas/{schema_name}", response_model=Schema)
async def get_schema(catalog_id: str, schema_name: str):
    """获取 Schema 详情"""
    schemas = catalog_service.get_schemas(catalog_id)
    for schema in schemas:
        if schema.name == schema_name:
            return schema
    raise HTTPException(status_code=404, detail="Schema not found")


@router.get("/{catalog_id}/schemas/{schema_name}/config")
async def get_schema_config(catalog_id: str, schema_name: str):
    """获取 Schema 配置原始内容"""
    content = catalog_service.get_schema_config_content(catalog_id, schema_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Schema config not found")
    return {"content": content}


@router.put("/{catalog_id}/schemas/{schema_name}", response_model=Schema)
async def update_schema(catalog_id: str, schema_name: str, update: SchemaUpdate):
    """更新 Schema"""
    try:
        schema = catalog_service.update_schema(catalog_id, schema_name, update)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        return schema
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/schemas/{schema_name}")
async def delete_schema(catalog_id: str, schema_name: str):
    """删除 Schema"""
    if not catalog_service.delete_schema(catalog_id, schema_name):
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"message": "Schema deleted successfully"}


@router.post("/{catalog_id}/schemas/{schema_name}/sync", response_model=SyncResult)
async def sync_schema_metadata(catalog_id: str, schema_name: str):
    """同步 Schema 元数据"""
    result = catalog_service.sync_schema_metadata(catalog_id, schema_name)
    if not result.success and "不存在" in str(result.errors):
        raise HTTPException(status_code=404, detail="Schema not found")
    return result


# ==================== Asset ====================

@router.get("/{catalog_id}/schemas/{schema_name}/assets", response_model=List[Asset])
async def list_assets(catalog_id: str, schema_name: str):
    """获取 Asset 列表"""
    return catalog_service.scan_assets(catalog_id, schema_name)


@router.post("/{catalog_id}/schemas/{schema_name}/assets", response_model=Asset)
async def create_asset(catalog_id: str, schema_name: str, asset: AssetCreate):
    """创建 Asset"""
    try:
        return catalog_service.create_asset(catalog_id, schema_name, asset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{catalog_id}/schemas/{schema_name}/assets/{asset_name}/config")
async def get_asset_config(catalog_id: str, schema_name: str, asset_name: str):
    """获取 Asset 配置原始内容"""
    content = catalog_service.get_asset_config_content(catalog_id, schema_name, asset_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Asset config not found")
    return {"content": content}


@router.delete("/{catalog_id}/schemas/{schema_name}/assets/{asset_name}")
async def delete_asset(catalog_id: str, schema_name: str, asset_name: str):
    """删除 Asset"""
    if not catalog_service.delete_asset(catalog_id, schema_name, asset_name):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


@router.get("/{catalog_id}/schemas/{schema_name}/tables/{table_name}/preview")
async def preview_table_data(catalog_id: str, schema_name: str, table_name: str, limit: int = 100, offset: int = 0):
    """预览表数据"""
    try:
        return catalog_service.preview_table_data(catalog_id, schema_name, table_name, limit, offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Agent ====================

@router.get("/{catalog_id}/agents", response_model=List[Agent])
async def list_agents(catalog_id: str):
    """获取 Agent 列表"""
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog_service.list_agents(catalog_id)


@router.post("/{catalog_id}/agents", response_model=Agent)
async def create_agent(catalog_id: str, agent: AgentCreate):
    """创建 Agent"""
    try:
        return catalog_service.create_agent(catalog_id, agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{catalog_id}/agents/{agent_name}", response_model=Agent)
async def get_agent(catalog_id: str, agent_name: str):
    """获取 Agent 详情"""
    agent = catalog_service.get_agent(catalog_id, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{catalog_id}/agents/{agent_name}/config")
async def get_agent_config(catalog_id: str, agent_name: str):
    """获取 Agent 配置原始内容"""
    content = catalog_service.get_agent_config_content(catalog_id, agent_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Agent config not found")
    return {"content": content}


@router.put("/{catalog_id}/agents/{agent_name}", response_model=Agent)
async def update_agent(catalog_id: str, agent_name: str, update: AgentUpdate):
    """更新 Agent"""
    try:
        agent = catalog_service.update_agent(catalog_id, agent_name, update)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/agents/{agent_name}")
async def delete_agent(catalog_id: str, agent_name: str):
    """删除 Agent"""
    if not catalog_service.delete_agent(catalog_id, agent_name):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}


# ==================== Prompt ====================

@router.get("/{catalog_id}/agents/{agent_name}/prompts", response_model=List[Prompt])
async def list_agent_prompts(catalog_id: str, agent_name: str):
    """获取 Prompt 列表"""
    prompts = catalog_service.list_agent_prompts(catalog_id, agent_name)
    if prompts is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return prompts


@router.get("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}", response_model=Prompt)
async def get_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str):
    """获取 Prompt 详情"""
    prompt = catalog_service.get_agent_prompt_detail(catalog_id, agent_name, prompt_name)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/{catalog_id}/agents/{agent_name}/prompts")
async def create_agent_prompt(catalog_id: str, agent_name: str, prompt: PromptCreate):
    """创建 Prompt"""
    try:
        if not catalog_service.create_agent_prompt(catalog_id, agent_name, prompt):
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": "Prompt created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}")
async def update_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str, update: PromptUpdate):
    """更新 Prompt"""
    try:
        if not catalog_service.update_agent_prompt(catalog_id, agent_name, prompt_name, update):
            raise HTTPException(status_code=404, detail="Prompt not found")
        return {"message": "Prompt updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}")
async def delete_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str):
    """删除 Prompt"""
    if not catalog_service.delete_agent_prompt(catalog_id, agent_name, prompt_name):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted successfully"}


@router.post("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}/toggle")
async def toggle_agent_prompt_enabled(catalog_id: str, agent_name: str, prompt_name: str, enabled: bool):
    """切换 Prompt 启用状态"""
    if not catalog_service.toggle_prompt_enabled(catalog_id, agent_name, prompt_name, enabled):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt enabled status updated successfully", "enabled": enabled}


# ==================== Skill ====================

# 注意：import 端点必须在 {skill_name} 之前定义，
# 否则 "import" 会被当作 skill_name 参数匹配

class SkillImportRequest(BaseModel):
    """Skill 导入请求"""
    zip_file_path: str  # 本地 zip 文件路径


@router.post("/{catalog_id}/agents/{agent_name}/skills/import")
async def import_agent_skill(
    catalog_id: str, 
    agent_name: str, 
    request: SkillImportRequest
):
    """
    从本地 zip 文件导入 Skill
    
    本地桌面应用场景下，直接传递本地文件路径，
    后端从本地路径复制并解压 zip 文件到 agent 的 skills 目录下。
    """
    logger.info(f"收到 Skill 导入请求: catalog_id={catalog_id}, agent_name={agent_name}, zip_path={request.zip_file_path}")
    
    zip_path = Path(request.zip_file_path)
    
    # 验证文件路径
    if not zip_path.exists():
        logger.error(f"文件不存在: {zip_path}")
        raise HTTPException(status_code=400, detail="文件不存在")
    
    if not zip_path.is_file():
        logger.error(f"路径不是文件: {zip_path}")
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    if not zip_path.suffix.lower() == '.zip':
        logger.error(f"不是 zip 文件: {zip_path}")
        raise HTTPException(status_code=400, detail="只支持 zip 格式文件")
    
    logger.info(f"开始导入 Skill，zip 文件: {zip_path}, 大小: {zip_path.stat().st_size} bytes")
    
    # 调用服务层处理导入（直接使用本地路径）
    result = catalog_service.import_skill_from_zip(
        catalog_id, 
        agent_name, 
        zip_path,
        original_filename=zip_path.name
    )
    
    logger.info(f"Skill 导入结果: {result}")
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/{catalog_id}/agents/{agent_name}/skills/{skill_name}")
async def get_agent_skill(catalog_id: str, agent_name: str, skill_name: str):
    """获取 Skill 内容"""
    result = catalog_service.get_agent_skill(catalog_id, agent_name, skill_name)
    if result is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"name": skill_name, "content": result["content"], "path": result["path"]}



@router.delete("/{catalog_id}/agents/{agent_name}/skills/{skill_name}")
async def delete_agent_skill(catalog_id: str, agent_name: str, skill_name: str):
    """删除 Skill"""
    if not catalog_service.delete_agent_skill(catalog_id, agent_name, skill_name):
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill deleted successfully"}


@router.post("/{catalog_id}/agents/{agent_name}/skills/{skill_name}/toggle")
async def toggle_agent_skill_enabled(catalog_id: str, agent_name: str, skill_name: str, enabled: bool):
    """切换 Skill 启用状态"""
    if not catalog_service.toggle_skill_enabled(catalog_id, agent_name, skill_name, enabled):
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill enabled status updated successfully", "enabled": enabled}


# ==================== Model ====================

@router.get("/{catalog_id}/schemas/{schema_name}/models", response_model=List[Model])
async def list_models(catalog_id: str, schema_name: str):
    """获取 Model 列表"""
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog_service.list_models(catalog_id, schema_name)


@router.post("/{catalog_id}/schemas/{schema_name}/models", response_model=Model)
async def create_model(catalog_id: str, schema_name: str, model: ModelCreate):
    """创建 Model"""
    try:
        return catalog_service.create_model(catalog_id, schema_name, model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{catalog_id}/schemas/{schema_name}/models/{model_name}", response_model=Model)
async def get_model(catalog_id: str, schema_name: str, model_name: str):
    """获取 Model 详情"""
    model = catalog_service.get_model(catalog_id, schema_name, model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.get("/{catalog_id}/schemas/{schema_name}/models/{model_name}/config")
async def get_model_config(catalog_id: str, schema_name: str, model_name: str):
    """获取 Model 配置原始内容"""
    content = catalog_service.get_model_config_content(catalog_id, schema_name, model_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Model config not found")
    return {"content": content}


@router.put("/{catalog_id}/schemas/{schema_name}/models/{model_name}", response_model=Model)
async def update_model(catalog_id: str, schema_name: str, model_name: str, update: ModelUpdate):
    """更新 Model"""
    try:
        model = catalog_service.update_model(catalog_id, schema_name, model_name, update)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/schemas/{schema_name}/models/{model_name}")
async def delete_model(catalog_id: str, schema_name: str, model_name: str):
    """删除 Model"""
    if not catalog_service.delete_model(catalog_id, schema_name, model_name):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}
