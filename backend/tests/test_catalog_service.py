"""
CatalogService 单元测试
测试基于文件系统的混合 Catalog 实现

目录结构:
App_Data/Catalogs/{catalog_name}/
├── config.yaml                    # Catalog 配置
├── agents/                        # Agent 目录
│   └── {agent_name}/
│       ├── agent.yaml             # Agent 配置
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

import yaml
import pytest
from datetime import datetime

from app.models.catalog import (
    CatalogCreate,
    SchemaCreate,
    SchemaSource,
    AssetType,
    ConnectionConfig,
    ConnectionType,
    AgentCreate,
    ModelCreate,
)
from app.core.constants import (
    CATALOG_CONFIG_FILE,
    SCHEMA_CONFIG_FILE,
    AGENT_CONFIG_FILE,
)
from app.services.catalog_service import CatalogService


class TestCatalogServiceInit:
    """测试 CatalogService 初始化"""
    
    def test_service_init_creates_catalogs_dir(self, temp_catalogs_dir, monkeypatch):
        """测试服务初始化时自动创建 Catalogs 目录"""
        from app.core.config import settings
        import shutil
        
        # 删除目录
        shutil.rmtree(temp_catalogs_dir, ignore_errors=True)
        assert not temp_catalogs_dir.exists()
        
        # 设置新的 CATALOGS_DIR
        monkeypatch.setattr(settings, 'CATALOGS_DIR', temp_catalogs_dir)
        
        # 创建新的 CatalogService 实例，并手动设置目录
        service = CatalogService()
        service.catalogs_dir = temp_catalogs_dir
        service._ensure_catalogs_dir()
        
        assert temp_catalogs_dir.exists()
        assert temp_catalogs_dir.is_dir()


class TestDiscoverCatalogs:
    """测试 Catalog 发现功能"""
    
    def test_discover_empty_catalogs(self, catalog_service_with_temp_dir):
        """测试空目录时返回空列表"""
        catalogs = catalog_service_with_temp_dir.discover_catalogs()
        assert catalogs == []
    
    def test_discover_catalog_with_config(self, catalog_service_with_temp_dir, sample_catalog):
        """测试发现带有 config.yaml 的 Catalog"""
        catalogs = catalog_service_with_temp_dir.discover_catalogs()
        
        assert len(catalogs) == 1
        catalog = catalogs[0]
        
        assert catalog.id == sample_catalog["name"]
        assert catalog.display_name == "测试 Catalog"
        assert catalog.description == "用于单元测试的 Catalog"
        assert "测试" in catalog.tags
        assert catalog.has_connections is True
        assert catalog.allow_custom_schema is True
    
    def test_discover_catalog_without_config(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试发现没有 config.yaml 的 Catalog（会自动创建默认配置）"""
        catalog_path = temp_catalogs_dir / "no_config_catalog"
        catalog_path.mkdir(parents=True, exist_ok=True)
        
        catalogs = catalog_service_with_temp_dir.discover_catalogs()
        
        assert len(catalogs) == 1
        catalog = catalogs[0]
        
        assert catalog.id == "no_config_catalog"
        assert catalog.display_name == "no_config_catalog"
        assert catalog.has_connections is False
        
        # 验证 config.yaml 被自动创建
        assert (catalog_path / CATALOG_CONFIG_FILE).exists()
    
    def test_discover_skips_hidden_folders(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试发现时跳过隐藏文件夹"""
        (temp_catalogs_dir / ".hidden_catalog").mkdir(parents=True, exist_ok=True)
        (temp_catalogs_dir / "normal_catalog").mkdir(parents=True, exist_ok=True)
        
        catalogs = catalog_service_with_temp_dir.discover_catalogs()
        
        assert len(catalogs) == 1
        assert catalogs[0].name == "normal_catalog"


class TestGetCatalog:
    """测试获取指定 Catalog"""
    
    def test_get_existing_catalog(self, catalog_service_with_temp_dir, sample_catalog):
        """测试获取存在的 Catalog"""
        catalog = catalog_service_with_temp_dir.get_catalog(sample_catalog["name"])
        
        assert catalog is not None
        assert catalog.id == sample_catalog["name"]
        assert catalog.display_name == "测试 Catalog"
    
    def test_get_nonexistent_catalog(self, catalog_service_with_temp_dir):
        """测试获取不存在的 Catalog 返回 None"""
        catalog = catalog_service_with_temp_dir.get_catalog("nonexistent")
        assert catalog is None


class TestCreateCatalog:
    """测试创建 Catalog"""
    
    def test_create_catalog_basic(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试创建基本 Catalog"""
        catalog_create = CatalogCreate(
            name="new_catalog",
            display_name="新建 Catalog",
            description="测试描述"
        )
        
        catalog = catalog_service_with_temp_dir.create_catalog(catalog_create)
        
        assert catalog.id == "new_catalog"
        assert catalog.display_name == "新建 Catalog"
        assert catalog.description == "测试描述"
        assert catalog.allow_custom_schema is True
        
        catalog_path = temp_catalogs_dir / "new_catalog"
        assert catalog_path.exists()
        assert (catalog_path / CATALOG_CONFIG_FILE).exists()
        assert (catalog_path / "agents").exists()
        assert (catalog_path / "schemas").exists()
    
    def test_create_catalog_with_connections(self, catalog_service_with_temp_dir, temp_catalogs_dir, monkeypatch):
        """测试创建带有数据库连接的 Catalog"""
        from app.models.metadata import SyncResult
        
        mock_sync_result = SyncResult(success=True, schemas_synced=1, tables_synced=2)
        monkeypatch.setattr(
            catalog_service_with_temp_dir, 
            '_sync_connection_metadata', 
            lambda *args, **kwargs: mock_sync_result
        )
        
        connections = [
            ConnectionConfig(
                type=ConnectionType.MYSQL,
                host="localhost",
                port=3306,
                db_name="test_db",
                sync_schema=True
            )
        ]
        
        catalog_create = CatalogCreate(
            name="connected_catalog",
            display_name="带连接的 Catalog",
            connections=connections
        )
        
        catalog = catalog_service_with_temp_dir.create_catalog(catalog_create)
        
        assert catalog.has_connections is True
        assert len(catalog.connections) == 1
    
    def test_create_catalog_duplicate_name(self, catalog_service_with_temp_dir, sample_catalog):
        """测试创建重复名称的 Catalog 抛出异常"""
        catalog_create = CatalogCreate(
            name=sample_catalog["name"],
            display_name="重复的 Catalog"
        )
        
        with pytest.raises(ValueError, match="已存在"):
            catalog_service_with_temp_dir.create_catalog(catalog_create)


class TestDeleteCatalog:
    """测试删除 Catalog"""
    
    def test_delete_existing_catalog(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试删除存在的 Catalog"""
        catalog_path = temp_catalogs_dir / sample_catalog["name"]
        assert catalog_path.exists()
        
        result = catalog_service_with_temp_dir.delete_catalog(sample_catalog["name"])
        
        assert result is True
        assert not catalog_path.exists()
    
    def test_delete_nonexistent_catalog(self, catalog_service_with_temp_dir):
        """测试删除不存在的 Catalog 返回 False"""
        result = catalog_service_with_temp_dir.delete_catalog("nonexistent")
        assert result is False


class TestSchemaOperations:
    """测试 Schema 相关操作"""
    
    def test_get_schemas(self, catalog_service_with_temp_dir, sample_catalog):
        """测试获取 Schema 列表"""
        schemas = catalog_service_with_temp_dir.get_schemas(sample_catalog["name"])
        
        assert len(schemas) >= 3
        
        local_schemas = [s for s in schemas if s.source == SchemaSource.LOCAL]
        schema_names = [s.name for s in local_schemas]
        assert "data" in schema_names
        assert "agents" in schema_names
        assert "notes" in schema_names
    
    def test_create_schema(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试创建 Schema"""
        schema_create = SchemaCreate(
            name="new_schema",
            owner="test_user",
            description="新建的 Schema"
        )
        
        schema = catalog_service_with_temp_dir.create_schema(sample_catalog["name"], schema_create)
        
        assert schema.name == "new_schema"
        assert schema.owner == "test_user"
        assert schema.source == SchemaSource.LOCAL
        assert schema.readonly is False
        
        schema_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "new_schema"
        assert schema_path.exists()
        assert (schema_path / SCHEMA_CONFIG_FILE).exists()
        assert (schema_path / "tables").exists()
        assert (schema_path / "volumes").exists()
        assert (schema_path / "models").exists()
        assert (schema_path / "functions").exists()
    
    def test_create_schema_nonexistent_catalog(self, catalog_service_with_temp_dir):
        """测试在不存在的 Catalog 下创建 Schema 抛出异常"""
        schema_create = SchemaCreate(name="test_schema")
        
        with pytest.raises(ValueError, match="不存在"):
            catalog_service_with_temp_dir.create_schema("nonexistent", schema_create)
    
    def test_create_duplicate_schema(self, catalog_service_with_temp_dir, sample_catalog):
        """测试创建重复的 Schema 抛出异常"""
        schema_create = SchemaCreate(name="data")
        
        with pytest.raises(ValueError, match="已存在"):
            catalog_service_with_temp_dir.create_schema(sample_catalog["name"], schema_create)
    
    def test_delete_schema(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试删除 Schema"""
        schema_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "data"
        assert schema_path.exists()
        
        result = catalog_service_with_temp_dir.delete_schema(sample_catalog["name"], "data")
        
        assert result is True
        assert not schema_path.exists()
    
    def test_delete_nonexistent_schema(self, catalog_service_with_temp_dir, sample_catalog):
        """测试删除不存在的 Schema 返回 False"""
        result = catalog_service_with_temp_dir.delete_schema(sample_catalog["name"], "nonexistent")
        assert result is False


class TestAssetOperations:
    """测试资产相关操作"""
    
    def test_scan_assets(self, catalog_service_with_temp_dir, sample_catalog):
        """测试扫描资产"""
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "data")
        
        assert len(assets) == 2
        asset_names = [a.name for a in assets]
        assert "sales" in asset_names
        assert "users" in asset_names
    
    def test_scan_assets_empty_schema(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试扫描空 Schema"""
        empty_schema_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "empty"
        empty_schema_path.mkdir(exist_ok=True, parents=True)
        
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "empty")
        assert assets == []
    
    def test_scan_assets_nonexistent_schema(self, catalog_service_with_temp_dir, sample_catalog):
        """测试扫描不存在的 Schema 返回空列表"""
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "nonexistent")
        assert assets == []
    
    def test_asset_type_detection_table(self, catalog_service_with_temp_dir, sample_catalog):
        """测试 Table 类型资产检测"""
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "data")
        
        for asset in assets:
            assert asset.asset_type == AssetType.TABLE
    
    def test_asset_type_detection_agent(self, catalog_service_with_temp_dir, sample_catalog):
        """测试 Agent 类型资产检测"""
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "agents")
        
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.AGENT
        assert assets[0].name == "test_agent"
    
    def test_asset_type_detection_note(self, catalog_service_with_temp_dir, sample_catalog):
        """测试 Note 类型资产检测"""
        assets = catalog_service_with_temp_dir.scan_assets(sample_catalog["name"], "notes")
        
        assert len(assets) == 1
        assert assets[0].asset_type == AssetType.NOTE
        assert assets[0].name == "readme"


class TestCatalogTree:
    """测试 Catalog 导航树"""
    
    def test_get_catalog_tree(self, catalog_service_with_temp_dir, sample_catalog):
        """测试获取完整导航树"""
        tree = catalog_service_with_temp_dir.get_catalog_tree()
        
        assert len(tree) == 1
        
        catalog_node = tree[0]
        assert catalog_node.id == sample_catalog["name"]
        assert catalog_node.node_type == "catalog"
        assert catalog_node.display_name == "测试 Catalog"
        
        # Agent 子节点
        agent_nodes = [n for n in catalog_node.children if n.node_type == "agent"]
        assert len(agent_nodes) == 1
        assert agent_nodes[0].name == "test_agent"
        
        # Schema 子节点
        schema_nodes = [n for n in catalog_node.children if n.node_type == "schema"]
        assert len(schema_nodes) >= 3
        
        schema_names = [child.name for child in schema_nodes]
        assert "data" in schema_names
        assert "agents" in schema_names
        assert "notes" in schema_names
    
    def test_tree_contains_assets(self, catalog_service_with_temp_dir, sample_catalog):
        """测试导航树包含资产节点"""
        tree = catalog_service_with_temp_dir.get_catalog_tree()
        catalog_node = tree[0]
        
        data_schema = None
        for child in catalog_node.children:
            if child.name == "data" and child.node_type == "schema":
                data_schema = child
                break
        
        assert data_schema is not None
        assert len(data_schema.children) == 2
        
        asset_names = [asset.name for asset in data_schema.children]
        assert "sales" in asset_names
        assert "users" in asset_names
    
    def test_tree_marks_connection_schemas_readonly(self, catalog_service_with_temp_dir, sample_catalog):
        """测试导航树中连接 Schema 被标记为只读"""
        tree = catalog_service_with_temp_dir.get_catalog_tree()
        catalog_node = tree[0]
        
        schema_nodes = [child for child in catalog_node.children if child.node_type == "schema"]
        connection_schemas = [child for child in schema_nodes if child.source == "connection"]
        
        assert len(connection_schemas) == 1
        assert connection_schemas[0].readonly is True
    
    def test_empty_tree(self, catalog_service_with_temp_dir):
        """测试空目录返回空导航树"""
        tree = catalog_service_with_temp_dir.get_catalog_tree()
        assert tree == []
    
    def test_tree_contains_agent_with_skills_and_prompts(self, catalog_service_with_temp_dir, sample_catalog):
        """测试导航树中 Agent 包含 skills 和 prompts 子节点"""
        tree = catalog_service_with_temp_dir.get_catalog_tree()
        catalog_node = tree[0]
        
        agent_node = None
        for child in catalog_node.children:
            if child.node_type == "agent" and child.name == "test_agent":
                agent_node = child
                break
        
        assert agent_node is not None
        
        child_names = [c.name for c in agent_node.children]
        assert "skills" in child_names
        assert "prompts" in child_names
        
        skills_node = [c for c in agent_node.children if c.name == "skills"][0]
        assert len(skills_node.children) >= 1
        
        prompts_node = [c for c in agent_node.children if c.name == "prompts"][0]
        assert len(prompts_node.children) >= 1


class TestLoadCatalogConfig:
    """测试配置文件加载"""
    
    def test_load_valid_config(self, catalog_service_with_temp_dir, sample_catalog):
        """测试加载有效的配置文件"""
        config = catalog_service_with_temp_dir._load_catalog_config(sample_catalog["path"])
        
        assert config is not None
        assert config.catalog_id == sample_catalog["name"]
        assert config.display_name == "测试 Catalog"
        assert len(config.connections) == 1
    
    def test_load_invalid_yaml(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试加载无效 YAML 配置文件返回 None"""
        catalog_path = temp_catalogs_dir / "invalid_catalog"
        catalog_path.mkdir(exist_ok=True)
        
        config_path = catalog_path / CATALOG_CONFIG_FILE
        config_path.write_text("{ invalid: yaml: content")
        
        config = catalog_service_with_temp_dir._load_catalog_config(catalog_path)
        assert config is None
    
    def test_load_missing_config(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试加载不存在的配置文件返回 None"""
        catalog_path = temp_catalogs_dir / "no_config"
        catalog_path.mkdir(exist_ok=True)
        
        config = catalog_service_with_temp_dir._load_catalog_config(catalog_path)
        assert config is None


class TestDetectAssetType:
    """测试资产类型检测"""
    
    def test_detect_parquet_as_table(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试 .parquet 文件识别为 Table"""
        test_file = temp_catalogs_dir / "test.parquet"
        test_file.touch()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_file)
        assert asset_type == AssetType.TABLE
    
    def test_detect_csv_as_table(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试 .csv 文件识别为 Table"""
        test_file = temp_catalogs_dir / "test.csv"
        test_file.touch()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_file)
        assert asset_type == AssetType.TABLE
    
    def test_detect_yaml_as_agent(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试 .yaml 文件识别为 Agent"""
        test_file = temp_catalogs_dir / "test.yaml"
        test_file.touch()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_file)
        assert asset_type == AssetType.AGENT
    
    def test_detect_md_as_note(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试 .md 文件识别为 Note"""
        test_file = temp_catalogs_dir / "test.md"
        test_file.touch()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_file)
        assert asset_type == AssetType.NOTE
    
    def test_detect_directory_as_volume(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试目录识别为 Volume"""
        test_dir = temp_catalogs_dir / "test_dir"
        test_dir.mkdir()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_dir)
        assert asset_type == AssetType.VOLUME
    
    def test_detect_unknown_as_volume(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试未知类型文件识别为 Volume"""
        test_file = temp_catalogs_dir / "test.unknown"
        test_file.touch()
        
        asset_type = catalog_service_with_temp_dir._detect_asset_type(test_file)
        assert asset_type == AssetType.VOLUME


class TestYamlConfigFormat:
    """测试 YAML 配置文件格式"""
    
    def test_config_saved_as_yaml(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试配置文件以 config.yaml 格式保存"""
        catalog_create = CatalogCreate(
            name="yaml_test_catalog",
            display_name="YAML 测试",
            description="测试 YAML 格式"
        )
        
        catalog_service_with_temp_dir.create_catalog(catalog_create)
        
        config_path = temp_catalogs_dir / "yaml_test_catalog" / CATALOG_CONFIG_FILE
        assert config_path.exists()
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        assert config_data["catalog_id"] == "yaml_test_catalog"
        assert config_data["display_name"] == "YAML 测试"
        assert config_data["description"] == "测试 YAML 格式"
    
    def test_yaml_supports_chinese(self, catalog_service_with_temp_dir, temp_catalogs_dir):
        """测试 YAML 配置支持中文"""
        catalog_create = CatalogCreate(
            name="chinese_catalog",
            display_name="中文显示名称",
            description="这是中文描述"
        )
        
        catalog_service_with_temp_dir.create_catalog(catalog_create)
        
        config_path = temp_catalogs_dir / "chinese_catalog" / CATALOG_CONFIG_FILE
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "中文显示名称" in content
        assert "这是中文描述" in content


class TestAgentOperations:
    """测试 Agent 相关操作"""
    
    def test_scan_agents(self, catalog_service_with_temp_dir, sample_catalog):
        """测试扫描 Agent"""
        agents = catalog_service_with_temp_dir.list_agents(sample_catalog["name"])
        
        assert len(agents) == 1
        assert agents[0].name == "test_agent"
        assert agents[0].description == "测试智能体"
    
    def test_create_agent(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试创建 Agent"""
        agent_create = AgentCreate(
            name="new_agent",
            description="新建的智能体",
            system_prompt="你是一个助手"
        )
        
        agent = catalog_service_with_temp_dir.create_agent(sample_catalog["name"], agent_create)
        
        assert agent.name == "new_agent"
        assert agent.description == "新建的智能体"
        
        agent_path = temp_catalogs_dir / sample_catalog["name"] / "agents" / "new_agent"
        assert agent_path.exists()
        assert (agent_path / AGENT_CONFIG_FILE).exists()
        assert (agent_path / "skills").exists()
        assert (agent_path / "prompts").exists()
    
    def test_create_duplicate_agent(self, catalog_service_with_temp_dir, sample_catalog):
        """测试创建重复的 Agent 抛出异常"""
        agent_create = AgentCreate(name="test_agent")
        
        with pytest.raises(ValueError, match="已存在"):
            catalog_service_with_temp_dir.create_agent(sample_catalog["name"], agent_create)
    
    def test_get_agent(self, catalog_service_with_temp_dir, sample_catalog):
        """测试获取指定 Agent"""
        agent = catalog_service_with_temp_dir.get_agent(sample_catalog["name"], "test_agent")
        
        assert agent is not None
        assert agent.name == "test_agent"
        assert len(agent.skills) >= 1
        assert len(agent.prompts) >= 1
    
    def test_delete_agent(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试删除 Agent"""
        agent_path = temp_catalogs_dir / sample_catalog["name"] / "agents" / "test_agent"
        assert agent_path.exists()
        
        result = catalog_service_with_temp_dir.delete_agent(sample_catalog["name"], "test_agent")
        
        assert result is True
        assert not agent_path.exists()


class TestModelOperations:
    """测试 Model 相关操作"""
    
    def test_create_model(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试创建 Model"""
        model_create = ModelCreate(
            name="gpt-4",
            description="GPT-4 模型",
            model_type="endpoint",
            endpoint_provider="openai",
            api_base_url="https://api.openai.com/v1",
            model_id="gpt-4"
        )
        
        model = catalog_service_with_temp_dir.create_model(sample_catalog["name"], "data", model_create)
        
        assert model.name == "gpt-4"
        assert model.description == "GPT-4 模型"
        assert model.model_type == "endpoint"
        
        model_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "data" / "models" / "gpt-4.yaml"
        assert model_path.exists()
    
    def test_scan_models(self, catalog_service_with_temp_dir, sample_catalog):
        """测试扫描 Schema 下的 Model"""
        model_create = ModelCreate(
            name="test-model",
            description="测试模型",
            model_type="endpoint",
            endpoint_provider="openai",
        )
        
        catalog_service_with_temp_dir.create_model(sample_catalog["name"], "data", model_create)
        
        models = catalog_service_with_temp_dir.list_models(sample_catalog["name"], "data")
        
        assert len(models) == 1
        assert models[0].name == "test-model"
    
    def test_delete_model(self, catalog_service_with_temp_dir, sample_catalog, temp_catalogs_dir):
        """测试删除 Model"""
        model_create = ModelCreate(name="to-delete", model_type="endpoint")
        
        catalog_service_with_temp_dir.create_model(sample_catalog["name"], "data", model_create)
        
        model_path = temp_catalogs_dir / sample_catalog["name"] / "schemas" / "data" / "models" / "to-delete.yaml"
        assert model_path.exists()
        
        result = catalog_service_with_temp_dir.delete_model(sample_catalog["name"], "data", "to-delete")
        
        assert result is True
        assert not model_path.exists()
