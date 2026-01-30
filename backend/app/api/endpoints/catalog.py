"""
Catalog 管理端点
提供 Catalog、Schema、Asset、Agent、Model 等资源的 CRUD 操作

树形结构定义：
├── Catalog (Namespace)
│   ├── agents/{agent_name}/           # Agent 智能体目录
│   │   ├── agent.yaml                 # Agent 配置
│   │   ├── prompts/                   # 提示词模板目录
│   │   └── skills/                    # Skills 文件目录
│   └── schemas/{schema_name}/         # Schema 逻辑库目录
│       ├── schema.yaml                # Schema 配置
│       ├── models/                    # 模型定义目录
│       ├── tables/                    # 表映射目录
│       ├── functions/                 # 自定义函数目录
│       └── volumes/                   # 文档存储目录
"""

from typing import List
from fastapi import APIRouter, HTTPException

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

router = APIRouter()


# ==================== Catalog 端点 ====================

@router.get("", response_model=List[Catalog])
async def list_catalogs():
    """
    获取所有 Catalog 列表
    扫描 App_Data/Catalogs 目录，发现并加载所有 Catalog
    """
    return catalog_service.discover_catalogs()


@router.post("", response_model=Catalog)
async def create_catalog(catalog: CatalogCreate):
    """
    创建新的 Catalog
    在 App_Data/Catalogs 下创建新的文件夹和 config.yaml
    """
    try:
        return catalog_service.create_catalog(catalog)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tree", response_model=List[CatalogTreeNode])
async def get_catalog_tree():
    """
    获取完整的 Catalog 导航树
    包含所有 Catalog、Agent、Schema、Asset 的层级结构
    """
    return catalog_service.get_catalog_tree()


@router.get("/{catalog_id}", response_model=Catalog)
async def get_catalog(catalog_id: str):
    """获取指定 Catalog 详情"""
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog


@router.put("/{catalog_id}", response_model=Catalog)
async def update_catalog(catalog_id: str, catalog_update: CatalogUpdate):
    """更新指定 Catalog 的信息"""
    try:
        catalog = catalog_service.update_catalog(catalog_id, catalog_update)
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")
        return catalog
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}")
async def delete_catalog(catalog_id: str):
    """删除指定 Catalog（包括其所有 Agent、Schema 和资产）"""
    success = catalog_service.delete_catalog(catalog_id)
    if not success:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return {"message": "Catalog deleted successfully"}


@router.post("/{catalog_id}/sync", response_model=SyncResult)
async def sync_catalog_metadata(catalog_id: str):
    """
    手动触发 Catalog 的元数据同步
    从配置的数据库连接中拉取最新的元数据
    """
    result = catalog_service.sync_catalog_metadata(catalog_id)
    if not result.success and "不存在" in str(result.errors):
        raise HTTPException(status_code=404, detail="Catalog not found")
    return result


# ==================== Schema 端点 ====================

@router.get("/{catalog_id}/schemas", response_model=List[Schema])
async def list_schemas(catalog_id: str):
    """
    获取 Catalog 下的所有 Schema
    包括本地创建的 Schema 和外部连接同步的 Schema
    """
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog.schemas


@router.post("/{catalog_id}/schemas", response_model=Schema)
async def create_schema(catalog_id: str, schema: SchemaCreate):
    """
    在 Catalog 下创建新的 Schema
    会在 schemas/ 目录下创建对应的子文件夹
    """
    try:
        return catalog_service.create_schema(catalog_id, schema)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{catalog_id}/schemas/{schema_name}", response_model=Schema)
async def update_schema(catalog_id: str, schema_name: str, schema_update: SchemaUpdate):
    """
    更新 Schema 信息（仅支持本地创建的 Schema）
    外部连接同步的 Schema 不能修改
    """
    try:
        schema = catalog_service.update_schema(catalog_id, schema_name, schema_update)
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        return schema
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/schemas/{schema_name}")
async def delete_schema(catalog_id: str, schema_name: str):
    """
    删除 Schema（仅支持本地创建的 Schema）
    外部连接同步的 Schema 不能删除
    """
    success = catalog_service.delete_schema(catalog_id, schema_name)
    if not success:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"message": "Schema deleted successfully"}


# ==================== Asset 端点 ====================

@router.get("/{catalog_id}/schemas/{schema_name}/assets", response_model=List[Asset])
async def list_assets(catalog_id: str, schema_name: str):
    """
    获取 Schema 下的所有资产
    资产包括 Table、Volume、Agent、Note 等
    """
    return catalog_service.scan_assets(catalog_id, schema_name)


@router.post("/{catalog_id}/schemas/{schema_name}/assets", response_model=Asset)
async def create_asset(catalog_id: str, schema_name: str, asset_create: AssetCreate):
    """
    在 Schema 下创建新的资产
    支持创建 Volume、Table、Function 等类型
    会在对应的资产类型目录下生成 {name}.yaml 元数据文件
    """
    try:
        return catalog_service.create_asset(catalog_id, schema_name, asset_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{catalog_id}/schemas/{schema_name}/assets/{asset_name}")
async def delete_asset(catalog_id: str, schema_name: str, asset_name: str):
    """删除指定资产"""
    success = catalog_service.delete_asset(catalog_id, schema_name, asset_name)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


@router.get("/{catalog_id}/schemas/{schema_name}/tables/{table_name}/preview")
async def preview_table_data(
    catalog_id: str, 
    schema_name: str, 
    table_name: str,
    limit: int = 100,
    offset: int = 0
):
    """
    预览表数据
    仅支持外部连接的表，返回指定数量的行
    """
    try:
        return catalog_service.preview_table_data(catalog_id, schema_name, table_name, limit, offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Agent 端点 ====================

@router.get("/{catalog_id}/agents", response_model=List[Agent])
async def list_agents(catalog_id: str):
    """
    获取 Catalog 下的所有 Agent
    Agent 是 Catalog 的一级子项，与 Schema 同级
    """
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog_service.list_agents(catalog_id)


@router.post("/{catalog_id}/agents", response_model=Agent)
async def create_agent(catalog_id: str, agent: AgentCreate):
    """
    在 Catalog 下创建新的 Agent
    会在 agents/ 目录下创建 Agent 目录，包含 skills 和 prompts 子目录
    """
    try:
        return catalog_service.create_agent(catalog_id, agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{catalog_id}/agents/{agent_name}", response_model=Agent)
async def get_agent(catalog_id: str, agent_name: str):
    """获取指定 Agent 详情"""
    agent = catalog_service.get_agent(catalog_id, agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{catalog_id}/agents/{agent_name}", response_model=Agent)
async def update_agent(catalog_id: str, agent_name: str, agent_update: AgentUpdate):
    """更新指定 Agent 的信息"""
    try:
        agent = catalog_service.update_agent(catalog_id, agent_name, agent_update)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/agents/{agent_name}")
async def delete_agent(catalog_id: str, agent_name: str):
    """删除指定 Agent"""
    success = catalog_service.delete_agent(catalog_id, agent_name)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}


# ==================== Agent Prompts 端点 ====================

@router.get("/{catalog_id}/agents/{agent_name}/prompts", response_model=List[Prompt])
async def list_agent_prompts(catalog_id: str, agent_name: str):
    """获取 Agent 所有 Prompts 列表"""
    prompts = catalog_service.list_agent_prompts(catalog_id, agent_name)
    if prompts is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return prompts


@router.get("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}", response_model=Prompt)
async def get_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str):
    """获取 Agent Prompt 详情（包含内容和元数据）"""
    prompt = catalog_service.get_agent_prompt_detail(catalog_id, agent_name, prompt_name)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.post("/{catalog_id}/agents/{agent_name}/prompts")
async def create_agent_prompt(catalog_id: str, agent_name: str, prompt_create: PromptCreate):
    """创建 Agent Prompt（接受 JSON body）"""
    try:
        success = catalog_service.create_agent_prompt(catalog_id, agent_name, prompt_create)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": "Prompt created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}")
async def update_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str, prompt_update: PromptUpdate):
    """更新 Agent Prompt"""
    try:
        success = catalog_service.update_agent_prompt(catalog_id, agent_name, prompt_name, prompt_update)
        if not success:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return {"message": "Prompt updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}")
async def delete_agent_prompt(catalog_id: str, agent_name: str, prompt_name: str):
    """删除 Agent Prompt"""
    success = catalog_service.delete_agent_prompt(catalog_id, agent_name, prompt_name)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted successfully"}


@router.post("/{catalog_id}/agents/{agent_name}/prompts/{prompt_name}/toggle")
async def toggle_agent_prompt_enabled(catalog_id: str, agent_name: str, prompt_name: str, enabled: bool):
    """切换 Agent Prompt 启用状态（在 agent.yaml 的 enabled_prompts 中添加/移除）"""
    success = catalog_service.toggle_prompt_enabled(catalog_id, agent_name, prompt_name, enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt enabled status updated successfully", "enabled": enabled}


# ==================== Agent Skills 端点 ====================

@router.get("/{catalog_id}/agents/{agent_name}/skills/{skill_name}")
async def get_agent_skill(catalog_id: str, agent_name: str, skill_name: str):
    """获取 Agent Skill 内容"""
    content = catalog_service.get_agent_skill(catalog_id, agent_name, skill_name)
    if content is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"name": skill_name, "content": content}


@router.post("/{catalog_id}/agents/{agent_name}/skills/{skill_name}")
async def create_agent_skill(catalog_id: str, agent_name: str, skill_name: str, content: str = ""):
    """创建或更新 Agent Skill 文件"""
    success = catalog_service.add_agent_skill(catalog_id, agent_name, skill_name, content)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Skill created successfully"}


@router.delete("/{catalog_id}/agents/{agent_name}/skills/{skill_name}")
async def delete_agent_skill(catalog_id: str, agent_name: str, skill_name: str):
    """删除 Agent Skill"""
    success = catalog_service.delete_agent_skill(catalog_id, agent_name, skill_name)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill deleted successfully"}


@router.post("/{catalog_id}/agents/{agent_name}/skills/{skill_name}/toggle")
async def toggle_agent_skill_enabled(catalog_id: str, agent_name: str, skill_name: str, enabled: bool):
    """切换 Agent Skill 启用状态（在 agent.yaml 的 enabled_skills 中添加/移除）"""
    success = catalog_service.toggle_skill_enabled(catalog_id, agent_name, skill_name, enabled)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"message": "Skill enabled status updated successfully", "enabled": enabled}


# ==================== Model 端点（Schema 级别） ====================

@router.get("/{catalog_id}/schemas/{schema_name}/models", response_model=List[Model])
async def list_models(catalog_id: str, schema_name: str):
    """
    获取 Schema 下的所有 Model
    Model 是 Schema 下的资产类型，存放在 models/ 目录
    """
    catalog = catalog_service.get_catalog(catalog_id)
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog_service.list_models(catalog_id, schema_name)


@router.post("/{catalog_id}/schemas/{schema_name}/models", response_model=Model)
async def create_model(catalog_id: str, schema_name: str, model: ModelCreate):
    """
    在 Schema 下创建新的 Model
    会在 models/ 目录下创建 Model 配置文件
    """
    try:
        return catalog_service.create_model(catalog_id, schema_name, model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{catalog_id}/schemas/{schema_name}/models/{model_name}", response_model=Model)
async def get_model(catalog_id: str, schema_name: str, model_name: str):
    """获取指定 Model 详情"""
    model = catalog_service.get_model(catalog_id, schema_name, model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/{catalog_id}/schemas/{schema_name}/models/{model_name}", response_model=Model)
async def update_model(catalog_id: str, schema_name: str, model_name: str, model_update: ModelUpdate):
    """更新指定 Model 的信息"""
    try:
        model = catalog_service.update_model(catalog_id, schema_name, model_name, model_update)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        return model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{catalog_id}/schemas/{schema_name}/models/{model_name}")
async def delete_model(catalog_id: str, schema_name: str, model_name: str):
    """删除指定 Model"""
    success = catalog_service.delete_model(catalog_id, schema_name, model_name)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}
