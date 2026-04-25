"""
Catalog API 端点单元测试
测试 Catalog、Schema、Asset、Agent 相关的 REST API

新目录结构:
App_Data/Catalogs/{catalog_name}/
├── config.yaml                    # Catalog 配置
├── agents/                        # Agent 目录
│   └── {agent_name}/
│       ├── agent_spec.yaml             # Agent 配置
│       ├── memories/              # Memories 子目录
│       └── skills/                # Skills 子目录
└── schemas/                       # Schema 目录
    └── {schema_name}/
        ├── schema.yaml            # Schema 配置
        ├── models/                # Models 子目录
        ├── tables/                # Tables 子目录
        ├── functions/             # Functions 子目录
        └── volumes/               # Volumes 子目录
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

# 从全局常量导入配置文件名
from app.core.constants import (
    CATALOG_CONFIG_FILE,
    SCHEMA_CONFIG_FILE,
    AGENT_CONFIG_FILE,
)


class TestHealthEndpoints:
    """测试健康检查端点"""
    
    def test_root_endpoint(self, test_client):
        """测试根路径"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_health_endpoint(self, test_client):
        """测试健康检查端点"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_health_ready_endpoint(self, test_client):
        """测试就绪检查端点"""
        response = test_client.get("/api/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestCatalogEndpoints:
    """测试 Catalog 端点"""
    
    def test_list_catalogs_empty(self, test_client):
        """测试列出空 Catalog 列表"""
        response = test_client.get("/api/catalogs")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_list_catalogs_with_data(self, test_client, sample_catalog):
        """测试列出 Catalog 列表"""
        response = test_client.get("/api/catalogs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_catalog["name"]
        assert data[0]["display_name"] == "测试 Catalog"
    
    def test_create_catalog(self, test_client, temp_catalogs_dir):
        """测试创建 Catalog"""
        payload = {
            "name": "new_api_catalog",
            "display_name": "通过 API 创建的 Catalog",
            "description": "API 测试描述",
            "allow_custom_schema": True
        }
        
        response = test_client.post("/api/catalogs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "new_api_catalog"
        assert data["display_name"] == "通过 API 创建的 Catalog"
        
        # 验证文件夹被创建
        catalog_path = temp_catalogs_dir / "new_api_catalog"
        assert catalog_path.exists()
        
        # 验证 config.yaml 被创建
        assert (catalog_path / CATALOG_CONFIG_FILE).exists()
    
    def test_create_catalog_with_connections(self, test_client, temp_catalogs_dir):
        """测试创建带连接配置的 Catalog"""
        payload = {
            "name": "connected_catalog",
            "display_name": "带连接的 Catalog",
            "connections": [
                {
                    "type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "db_name": "test_db",
                    "sync_schema": True
                }
            ]
        }
        
        response = test_client.post("/api/catalogs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_connections"] is True
    
    def test_create_catalog_duplicate(self, test_client, sample_catalog):
        """测试创建重复名称的 Catalog"""
        payload = {
            "name": sample_catalog["name"],
            "display_name": "重复的 Catalog"
        }
        
        response = test_client.post("/api/catalogs", json=payload)
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_get_catalog(self, test_client, sample_catalog):
        """测试获取指定 Catalog"""
        response = test_client.get(f"/api/catalogs/{sample_catalog['name']}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_catalog["name"]
        assert data["display_name"] == "测试 Catalog"
    
    def test_get_catalog_not_found(self, test_client):
        """测试获取不存在的 Catalog"""
        response = test_client.get("/api/catalogs/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_delete_catalog(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试删除 Catalog"""
        catalog_path = temp_catalogs_dir / sample_catalog["name"]
        assert catalog_path.exists()
        
        response = test_client.delete(f"/api/catalogs/{sample_catalog['name']}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Catalog deleted successfully"
        assert not catalog_path.exists()
    
    def test_delete_catalog_not_found(self, test_client):
        """测试删除不存在的 Catalog"""
        response = test_client.delete("/api/catalogs/nonexistent")
        
        assert response.status_code == 404


class TestCatalogTreeEndpoint:
    """测试 Catalog 导航树端点"""
    
    def test_get_catalog_tree_empty(self, test_client):
        """测试获取空导航树"""
        response = test_client.get("/api/catalogs/tree")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_get_catalog_tree_with_data(self, test_client, sample_catalog):
        """测试获取带数据的导航树"""
        response = test_client.get("/api/catalogs/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        catalog_node = data[0]
        
        assert catalog_node["id"] == sample_catalog["name"]
        assert catalog_node["node_type"] == "catalog"
        assert catalog_node["display_name"] == "测试 Catalog"
        
        # 验证包含子节点（Agent 和 Schema）
        assert len(catalog_node["children"]) >= 4  # 1 agent + 4 schemas
    
    def test_catalog_tree_structure(self, test_client, sample_catalog):
        """测试导航树结构完整性"""
        response = test_client.get("/api/catalogs/tree")
        data = response.json()
        
        catalog_node = data[0]
        
        # 验证 Catalog 节点结构
        assert "id" in catalog_node
        assert "name" in catalog_node
        assert "display_name" in catalog_node
        assert "node_type" in catalog_node
        assert "children" in catalog_node
        assert "metadata" in catalog_node
        
        # 验证 Agent 和 Schema 节点
        agent_nodes = [n for n in catalog_node["children"] if n["node_type"] == "agent"]
        schema_nodes = [n for n in catalog_node["children"] if n["node_type"] == "schema"]
        
        assert len(agent_nodes) >= 1
        assert len(schema_nodes) >= 3
    
    def test_catalog_tree_contains_agent_with_skills_memories(self, test_client, sample_catalog):
        """测试导航树中 Agent 包含 skills 和 memories"""
        response = test_client.get("/api/catalogs/tree")
        data = response.json()
        
        catalog_node = data[0]
        agent_nodes = [n for n in catalog_node["children"] if n["node_type"] == "agent"]
        
        assert len(agent_nodes) >= 1
        agent = agent_nodes[0]
        
        # 验证 Agent 包含 skills 和 memories 子节点
        child_names = [c["name"] for c in agent["children"]]
        assert "skills" in child_names
        assert "memories" in child_names


class TestSchemaEndpoints:
    """测试 Schema 端点"""
    
    def test_list_schemas(self, test_client, sample_catalog):
        """测试列出 Schema 列表"""
        response = test_client.get(f"/api/catalogs/{sample_catalog['name']}/schemas")
        
        assert response.status_code == 200
        data = response.json()
        
        # 至少包含 4 个 Schema（在 schemas/ 目录下）
        assert len(data) >= 3
        
        schema_names = [s["name"] for s in data]
        assert "data" in schema_names
        assert "agents" in schema_names
        assert "notes" in schema_names
    
    def test_list_schemas_catalog_not_found(self, test_client):
        """测试列出不存在 Catalog 的 Schema"""
        response = test_client.get("/api/catalogs/nonexistent/schemas")
        
        assert response.status_code == 404
    
    def test_create_schema(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试创建 Schema（在 schemas/ 目录下）"""
        payload = {
            "name": "new_schema",
            "owner": "test_user",
            "description": "测试 Schema"
        }
        
        response = test_client.post(
            f"/api/catalogs/{sample_catalog['name']}/schemas",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new_schema"
        assert data["owner"] == "test_user"
        assert data["source"] == "local"
        
        # 验证文件夹被创建在 schemas/ 目录下
        schema_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "new_schema"
        assert schema_path.exists()
        
        # 验证 schema.yaml 被创建
        assert (schema_path / SCHEMA_CONFIG_FILE).exists()
    
    def test_create_schema_catalog_not_found(self, test_client):
        """测试在不存在的 Catalog 下创建 Schema"""
        payload = {"name": "test_schema"}
        
        response = test_client.post(
            "/api/catalogs/nonexistent/schemas",
            json=payload
        )
        
        assert response.status_code == 400
        assert "不存在" in response.json()["detail"]
    
    def test_create_schema_duplicate(self, test_client, sample_catalog):
        """测试创建重复的 Schema"""
        payload = {"name": "data"}  # 已存在
        
        response = test_client.post(
            f"/api/catalogs/{sample_catalog['name']}/schemas",
            json=payload
        )
        
        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]
    
    def test_delete_schema(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试删除 Schema"""
        schema_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "data"
        assert schema_path.exists()
        
        response = test_client.delete(
            f"/api/catalogs/{sample_catalog['name']}/schemas/data"
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Schema deleted successfully"
        assert not schema_path.exists()
    
    def test_delete_schema_not_found(self, test_client, sample_catalog):
        """测试删除不存在的 Schema"""
        response = test_client.delete(
            f"/api/catalogs/{sample_catalog['name']}/schemas/nonexistent"
        )
        
        assert response.status_code == 404


class TestAssetEndpoints:
    """测试 Asset 端点"""
    
    def test_list_assets(self, test_client, sample_catalog):
        """测试列出 Asset 列表（在 tables 子目录下）"""
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/data/assets"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 2  # sales.json 和 users.csv
        
        asset_names = [a["name"] for a in data]
        assert "sales" in asset_names
        assert "users" in asset_names
    
    def test_list_assets_empty_schema(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试列出空 Schema 的 Asset"""
        # 创建空 Schema（在 schemas/ 目录下）
        empty_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "empty"
        empty_path.mkdir(exist_ok=True, parents=True)
        
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/empty/assets"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_list_assets_nonexistent_schema(self, test_client, sample_catalog):
        """测试列出不存在 Schema 的 Asset"""
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/nonexistent/assets"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_asset_type_in_response(self, test_client, sample_catalog):
        """测试 Asset 类型正确返回"""
        # 测试 data schema - 应该是 table 类型
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/data/assets"
        )
        
        data = response.json()
        for asset in data:
            assert asset["asset_type"] == "table"
        
        # 测试 agents schema - 应该是 agent 类型
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/agents/assets"
        )
        
        data = response.json()
        for asset in data:
            assert asset["asset_type"] == "agent"
        
        # 测试 notes schema - 应该是 note 类型
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/notes/assets"
        )
        
        data = response.json()
        for asset in data:
            assert asset["asset_type"] == "note"
    
    def test_asset_metadata_in_response(self, test_client, sample_catalog):
        """测试 Asset 元数据正确返回"""
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/schemas/data/assets"
        )
        
        data = response.json()
        
        for asset in data:
            assert "metadata" in asset
            assert "is_directory" in asset["metadata"]
            assert asset["metadata"]["is_directory"] is False


class TestAgentEndpoints:
    """测试 Agent 端点"""
    
    def test_list_agents(self, test_client, sample_catalog):
        """测试列出 Agent 列表"""
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/agents"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["name"] == "test_agent"
    
    def test_create_agent(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试创建 Agent"""
        payload = {
            "name": "new_agent",
            "description": "通过 API 创建的 Agent",
            "system_prompt": "你是一个助手"
        }
        
        response = test_client.post(
            f"/api/catalogs/{sample_catalog['name']}/agents",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new_agent"
        assert data["description"] == "通过 API 创建的 Agent"
        
        # 验证文件夹被创建在 agents/ 目录下
        agent_path = temp_catalogs_dir / sample_catalog["name"] / "agents" / "new_agent"
        assert agent_path.exists()
        assert (agent_path / AGENT_CONFIG_FILE).exists()
    
    def test_get_agent(self, test_client, sample_catalog):
        """测试获取指定 Agent"""
        response = test_client.get(
            f"/api/catalogs/{sample_catalog['name']}/agents/test_agent"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_agent"
        assert len(data["skills"]) >= 1
        assert len(data["memories"]) >= 1
    
    def test_delete_agent(self, test_client, sample_catalog, temp_catalogs_dir):
        """测试删除 Agent"""
        agent_path = temp_catalogs_dir / sample_catalog["name"] / "agents" / "test_agent"
        assert agent_path.exists()
        
        response = test_client.delete(
            f"/api/catalogs/{sample_catalog['name']}/agents/test_agent"
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Agent deleted successfully"
        assert not agent_path.exists()


class TestValidation:
    """测试输入验证"""
    
    def test_create_catalog_empty_name(self, test_client):
        """测试创建空名称的 Catalog"""
        payload = {"name": ""}
        
        response = test_client.post("/api/catalogs", json=payload)
        
        assert response.status_code == 422  # Validation Error
    
    def test_create_schema_empty_name(self, test_client, sample_catalog):
        """测试创建空名称的 Schema"""
        payload = {"name": ""}
        
        response = test_client.post(
            f"/api/catalogs/{sample_catalog['name']}/schemas",
            json=payload
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_create_catalog_invalid_connection_type(self, test_client):
        """测试创建带无效连接类型的 Catalog"""
        payload = {
            "name": "invalid_catalog",
            "connections": [
                {
                    "type": "invalid_type",
                    "port": 3306,
                    "db_name": "test"
                }
            ]
        }
        
        response = test_client.post("/api/catalogs", json=payload)
        
        assert response.status_code == 422  # Validation Error
