"""
测试配置文件
提供测试用的 fixtures 和共享配置

目录结构:
App_Data/Catalogs/{catalog_name}/
├── config.yaml                    # Catalog 配置
├── agents/                        # Agent 目录
│   └── {agent_name}/
│       ├── agent_spec.yaml             # Agent 配置
│       ├── prompts/               # Prompts 子目录
│       └── skills/                # Skills 子目录
└── schemas/                       # Schema 目录
    └── {schema_name}/
        ├── schema.yaml            # Schema 配置
        ├── models/                # Models 子目录
        ├── tables/                # Tables 子目录
        ├── functions/             # Functions 子目录
        └── volumes/               # Volumes 子目录
"""

import pytest
import tempfile
import shutil
import yaml
import sys
from pathlib import Path
from datetime import datetime

from fastapi.testclient import TestClient

# 从全局常量导入配置文件名
from app.core.constants import (
    CATALOG_CONFIG_FILE,
    AGENT_CONFIG_FILE,
    SCHEMA_CONFIG_FILE,
)


def _clear_catalog_modules():
    """清理所有 catalog 相关模块，确保重新导入"""
    modules_to_clear = [
        'app.services.catalog_service',
        'app.api.endpoints.catalog',
        'app.api.router',
        'main',
    ]
    for mod_name in list(sys.modules.keys()):
        if mod_name in modules_to_clear or mod_name.startswith('app.'):
            del sys.modules[mod_name]


@pytest.fixture(autouse=True, scope="function")
def cleanup_modules(request):
    """
    自动清理模块缓存
    只在 test_catalog_api.py 中运行时清理，其他测试不清理
    """
    # 只有在 API 测试中才清理模块
    if "test_catalog_api" in request.node.nodeid:
        _clear_catalog_modules()
        yield
        _clear_catalog_modules()
    elif "test_metadata_sync" in request.node.nodeid:
        # 对于 metadata_sync 测试，不清理模块但确保 patch 正确工作
        yield
    else:
        yield


def _create_sample_catalog_data(catalogs_dir: Path):
    """
    辅助函数：创建示例 Catalog 数据
    包含完整的目录结构：agents/ 和 schemas/
    """
    catalog_name = "test_catalog"
    catalog_path = catalogs_dir / catalog_name
    catalog_path.mkdir(parents=True, exist_ok=True)
    
    # 创建 Catalog 配置文件 (config.yaml)
    config = {
        "catalog_id": catalog_name,
        "display_name": "测试 Catalog",
        "connections": [
            {
                "type": "mysql",
                "host": "127.0.0.1",
                "port": 3306,
                "db_name": "test_db",
                "sync_schema": True
            }
        ],
        "allow_custom_schema": True,
        "description": "用于单元测试的 Catalog",
        "tags": ["测试", "单元测试"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    with open(catalog_path / CATALOG_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    # ==================== 创建 agents 目录结构 ====================
    agents_dir = catalog_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    
    # 创建测试 Agent
    test_agent_dir = agents_dir / "test_agent"
    test_agent_dir.mkdir(exist_ok=True)
    
    agent_config = {
        "description": "测试智能体",
        "system_prompt": "你是一个测试助手",
        "model_reference": "data.gpt-4",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    with open(test_agent_dir / AGENT_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(agent_config, f, default_flow_style=False, allow_unicode=True)
    
    # 创建 skills 子目录
    skills_dir = test_agent_dir / "skills"
    skills_dir.mkdir(exist_ok=True)
    (skills_dir / "search.py").write_text('# 搜索技能')
    
    # 创建 prompts 子目录
    prompts_dir = test_agent_dir / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    (prompts_dir / "system.md").write_text('# 系统提示词')
    
    # ==================== 创建 schemas 目录结构 ====================
    schemas_dir = catalog_path / "schemas"
    schemas_dir.mkdir(exist_ok=True)
    
    # Schema 1: data（本地 Schema）
    data_schema_dir = schemas_dir / "data"
    data_schema_dir.mkdir(exist_ok=True)
    
    data_schema_config = {
        "source": "local",
        "owner": "admin",
        "description": "数据 Schema",
        "sync_remote_tables": False,
        "created_at": datetime.now().isoformat()
    }
    with open(data_schema_dir / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data_schema_config, f, default_flow_style=False, allow_unicode=True)
    
    # 创建 data schema 的子目录
    for dir_name in ["tables", "volumes", "models", "functions"]:
        (data_schema_dir / dir_name).mkdir(exist_ok=True)
    
    # 在 tables 目录下创建资产文件
    (data_schema_dir / "tables" / "sales.json").write_text('{"data": []}')
    (data_schema_dir / "tables" / "users.csv").write_text('id,name\n1,test')
    
    # Schema 2: agents（本地 Schema，用于存放 agent 配置）
    agents_schema_dir = schemas_dir / "agents"
    agents_schema_dir.mkdir(exist_ok=True)
    
    agents_schema_config = {
        "source": "local",
        "owner": "admin",
        "description": "智能体配置 Schema",
        "created_at": datetime.now().isoformat()
    }
    with open(agents_schema_dir / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(agents_schema_config, f, default_flow_style=False, allow_unicode=True)
    
    (agents_schema_dir / "agents").mkdir(exist_ok=True)
    (agents_schema_dir / "agents" / "test_agent_spec.yaml").write_text('name: test_agent\ntype: chat')
    
    # Schema 3: notes（本地 Schema）
    notes_schema_dir = schemas_dir / "notes"
    notes_schema_dir.mkdir(exist_ok=True)
    
    notes_schema_config = {
        "source": "local",
        "owner": "admin",
        "description": "笔记 Schema",
        "created_at": datetime.now().isoformat()
    }
    with open(notes_schema_dir / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(notes_schema_config, f, default_flow_style=False, allow_unicode=True)
    
    (notes_schema_dir / "notes").mkdir(exist_ok=True)
    (notes_schema_dir / "notes" / "readme.md").write_text('# 测试笔记')
    
    # Schema 4: test_db（连接同步 Schema）
    connection_schema_dir = schemas_dir / "test_db"
    connection_schema_dir.mkdir(exist_ok=True)
    
    connection_schema_config = {
        "name": "test_db",
        "catalog_name": catalog_name,
        "source": "connection",
        "connection_type": "mysql",
        "connection_host": "127.0.0.1",
        "connection_port": 3306,
        "readonly": True,
        "synced_at": datetime.now().isoformat(),
    }
    with open(connection_schema_dir / SCHEMA_CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(connection_schema_config, f, default_flow_style=False, allow_unicode=True)
    
    (connection_schema_dir / "tables").mkdir(exist_ok=True)
    
    # 创建表元数据文件
    table_meta = {
        "name": "users",
        "schema_name": "test_db",
        "catalog_name": catalog_name,
        "table_type": "BASE TABLE",
        "engine": "InnoDB",
        "comment": "用户表",
        "row_count": 100,
        "create_time": datetime.now().isoformat(),
        "columns": [
            {"name": "id", "data_type": "int(11)", "is_primary_key": True, "ordinal_position": 1},
            {"name": "username", "data_type": "varchar(50)", "is_primary_key": False, "ordinal_position": 2},
        ],
        "primary_keys": ["id"],
        "source": "connection",
        "readonly": True,
    }
    with open(connection_schema_dir / "tables" / "users.yaml", "w", encoding="utf-8") as f:
        yaml.dump(table_meta, f, default_flow_style=False, allow_unicode=True)
    
    return {
        "name": catalog_name,
        "path": catalog_path,
        "config": config
    }


@pytest.fixture(scope="function")
def temp_catalogs_dir():
    """
    创建临时 Catalogs 目录用于测试
    每个测试函数独立使用，测试结束后自动清理
    """
    temp_dir = tempfile.mkdtemp(prefix="localbrisk_test_")
    catalogs_dir = Path(temp_dir) / "App_Data" / "Catalogs"
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    
    yield catalogs_dir
    
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def catalog_service_with_temp_dir(temp_catalogs_dir, monkeypatch):
    """
    创建使用临时目录的 CatalogService 实例
    """
    from app.core.config import settings
    
    monkeypatch.setattr(settings, 'CATALOGS_DIR', temp_catalogs_dir)
    
    from app.services.catalog_service import CatalogService
    service = CatalogService()
    
    yield service


@pytest.fixture(scope="function")
def test_client(temp_catalogs_dir, monkeypatch):
    """
    创建使用临时目录的 TestClient 实例
    用于测试 API 端点
    """
    from app.core.config import settings
    
    monkeypatch.setattr(settings, 'CATALOGS_DIR', temp_catalogs_dir)
    
    from main import app
    from app.services.catalog_service import catalog_service
    
    # 确保 catalog_service 使用正确的临时目录
    catalog_service.catalogs_dir = temp_catalogs_dir
    catalog_service._ensure_catalogs_dir()
    
    client = TestClient(app)
    
    yield client


@pytest.fixture(scope="function")
def sample_catalog(temp_catalogs_dir, test_client):
    """
    创建示例 Catalog 用于测试
    包含配置文件 (config.yaml)、agents/ 和 schemas/ 目录
    注意：此 fixture 依赖 test_client，确保先初始化 test_client
    """
    # 在临时目录中创建示例数据
    sample_data = _create_sample_catalog_data(temp_catalogs_dir)
    
    # 重新导入以确保 catalog_service 看到新创建的数据
    from app.services.catalog_service import catalog_service
    catalog_service.catalogs_dir = temp_catalogs_dir
    
    return sample_data


@pytest.fixture(scope="function")
def test_client_with_sample_catalog(temp_catalogs_dir, monkeypatch):
    """
    创建使用临时目录的 TestClient 实例，并预置 sample_catalog 数据
    用于需要预置数据的 API 测试
    """
    from app.core.config import settings
    
    monkeypatch.setattr(settings, 'CATALOGS_DIR', temp_catalogs_dir)
    
    sample_data = _create_sample_catalog_data(temp_catalogs_dir)
    
    from main import app
    from app.services.catalog_service import catalog_service
    
    catalog_service.catalogs_dir = temp_catalogs_dir
    catalog_service._ensure_catalogs_dir()
    
    client = TestClient(app)
    
    yield client, sample_data, temp_catalogs_dir
