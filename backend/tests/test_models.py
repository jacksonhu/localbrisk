"""
Catalog 数据模型单元测试
测试 Pydantic 模型的验证和序列化
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.catalog import (
    ConnectionConfig,
    ConnectionType,
    CatalogConfig,
    CatalogCreate,
    Catalog,
    Schema,
    SchemaCreate,
    SchemaSource,
    Asset,
    AssetType,
    CatalogTreeNode,
    Table,
    Volume,
    Agent,
    Note,
)


class TestConnectionConfig:
    """测试 ConnectionConfig 模型"""
    
    def test_valid_mysql_connection(self):
        """测试有效的 MySQL 连接配置"""
        config = ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test_db"
        )
        
        assert config.type == ConnectionType.MYSQL
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.db_name == "test_db"
        assert config.sync_schema is True  # 默认值
    
    def test_valid_postgresql_connection(self):
        """测试有效的 PostgreSQL 连接配置"""
        config = ConnectionConfig(
            type=ConnectionType.POSTGRESQL,
            port=5432,
            db_name="postgres_db",
            username="admin",
            password="secret"
        )
        
        assert config.type == ConnectionType.POSTGRESQL
        assert config.host == "127.0.0.1"  # 默认值
        assert config.username == "admin"
        assert config.password == "secret"
    
    def test_default_host(self):
        """测试默认 host 值"""
        config = ConnectionConfig(
            type=ConnectionType.SQLITE,
            port=0,
            db_name="local.db"
        )
        
        assert config.host == "127.0.0.1"
    
    def test_invalid_connection_type(self):
        """测试无效的连接类型"""
        with pytest.raises(ValidationError):
            ConnectionConfig(
                type="invalid_type",
                port=3306,
                db_name="test"
            )


class TestCatalogConfig:
    """测试 CatalogConfig 模型"""
    
    def test_valid_config(self):
        """测试有效的配置"""
        config = CatalogConfig(
            catalog_id="test_catalog",
            display_name="测试 Catalog"
        )
        
        assert config.catalog_id == "test_catalog"
        assert config.display_name == "测试 Catalog"
        assert config.connections == []
        assert config.allow_custom_schema is True
        assert config.tags == []
    
    def test_config_with_connections(self):
        """测试带连接的配置"""
        connections = [
            ConnectionConfig(
                type=ConnectionType.MYSQL,
                port=3306,
                db_name="test"
            )
        ]
        
        config = CatalogConfig(
            catalog_id="connected_catalog",
            display_name="带连接的 Catalog",
            connections=connections
        )
        
        assert len(config.connections) == 1
        assert config.connections[0].type == ConnectionType.MYSQL
    
    def test_config_with_all_fields(self):
        """测试包含所有字段的配置"""
        now = datetime.now()
        config = CatalogConfig(
            catalog_id="full_catalog",
            display_name="完整配置",
            connections=[],
            allow_custom_schema=False,
            description="完整描述",
            tags=["tag1", "tag2"],
            created_at=now,
            updated_at=now
        )
        
        assert config.description == "完整描述"
        assert config.tags == ["tag1", "tag2"]
        assert config.allow_custom_schema is False
        assert config.created_at == now


class TestCatalogCreate:
    """测试 CatalogCreate 模型"""
    
    def test_minimal_create(self):
        """测试最小创建请求"""
        create = CatalogCreate(name="test")
        
        assert create.name == "test"
        assert create.display_name is None
        assert create.allow_custom_schema is True
        assert create.connections == []
    
    def test_full_create(self):
        """测试完整创建请求"""
        create = CatalogCreate(
            name="full_catalog",
            display_name="完整 Catalog",
            owner="admin",
            description="描述",
            allow_custom_schema=False,
            connections=[
                ConnectionConfig(
                    type=ConnectionType.DUCKDB,
                    port=0,
                    db_name="duck.db"
                )
            ]
        )
        
        assert create.name == "full_catalog"
        assert create.display_name == "完整 Catalog"
        assert create.owner == "admin"
        assert create.allow_custom_schema is False
    
    def test_name_validation_empty(self):
        """测试名称验证 - 空名称"""
        with pytest.raises(ValidationError):
            CatalogCreate(name="")
    
    def test_name_validation_too_long(self):
        """测试名称验证 - 名称过长"""
        with pytest.raises(ValidationError):
            CatalogCreate(name="a" * 101)


class TestCatalog:
    """测试 Catalog 模型"""
    
    def test_valid_catalog(self):
        """测试有效的 Catalog"""
        now = datetime.now()
        catalog = Catalog(
            id="test",
            name="test",
            display_name="测试",
            owner="admin",
            path="/test/path",
            created_at=now,
            updated_at=now
        )
        
        assert catalog.id == "test"
        assert catalog.name == "test"
        assert catalog.schemas == []
        assert catalog.has_connections is False
    
    def test_catalog_with_schemas(self):
        """测试带 Schema 的 Catalog"""
        now = datetime.now()
        schema = Schema(
            id="test_schema",
            name="schema1",
            catalog_id="test",
            owner="admin",
            created_at=now
        )
        
        catalog = Catalog(
            id="test",
            name="test",
            display_name="测试",
            owner="admin",
            path="/test/path",
            created_at=now,
            updated_at=now,
            schemas=[schema]
        )
        
        assert len(catalog.schemas) == 1
        assert catalog.schemas[0].name == "schema1"


class TestSchema:
    """测试 Schema 模型"""
    
    def test_local_schema(self):
        """测试本地 Schema"""
        now = datetime.now()
        schema = Schema(
            id="test_schema",
            name="local_schema",
            catalog_id="test_catalog",
            owner="admin",
            source=SchemaSource.LOCAL,
            path="/test/path",
            created_at=now
        )
        
        assert schema.source == SchemaSource.LOCAL
        assert schema.readonly is False
        assert schema.connection_name is None
    
    def test_connection_schema(self):
        """测试连接 Schema"""
        now = datetime.now()
        schema = Schema(
            id="conn_schema",
            name="remote_schema",
            catalog_id="test_catalog",
            owner="admin",
            source=SchemaSource.CONNECTION,
            connection_name="mysql://localhost:3306/db",
            readonly=True,
            created_at=now
        )
        
        assert schema.source == SchemaSource.CONNECTION
        assert schema.readonly is True
        assert schema.connection_name is not None


class TestSchemaCreate:
    """测试 SchemaCreate 模型"""
    
    def test_minimal_create(self):
        """测试最小创建请求"""
        create = SchemaCreate(name="test_schema")
        
        assert create.name == "test_schema"
        assert create.owner is None
        assert create.description is None
    
    def test_name_validation_empty(self):
        """测试名称验证 - 空名称"""
        with pytest.raises(ValidationError):
            SchemaCreate(name="")
    
    def test_name_validation_too_long(self):
        """测试名称验证 - 名称过长"""
        with pytest.raises(ValidationError):
            SchemaCreate(name="a" * 101)


class TestAsset:
    """测试 Asset 模型"""
    
    def test_table_asset(self):
        """测试 Table 类型资产"""
        now = datetime.now()
        asset = Asset(
            id="test_asset",
            name="sales",
            schema_id="test_schema",
            asset_type=AssetType.TABLE,
            path="/test/sales.parquet",
            created_at=now
        )
        
        assert asset.asset_type == AssetType.TABLE
        assert asset.metadata == {}
    
    def test_asset_with_metadata(self):
        """测试带元数据的资产"""
        now = datetime.now()
        asset = Asset(
            id="test_asset",
            name="data",
            schema_id="test_schema",
            asset_type=AssetType.VOLUME,
            path="/test/data",
            metadata={
                "is_directory": True,
                "file_count": 10
            },
            created_at=now
        )
        
        assert asset.metadata["is_directory"] is True
        assert asset.metadata["file_count"] == 10


class TestCatalogTreeNode:
    """测试 CatalogTreeNode 模型"""
    
    def test_basic_node(self):
        """测试基本节点"""
        node = CatalogTreeNode(
            id="test",
            name="test",
            display_name="测试",
            node_type="catalog"
        )
        
        assert node.id == "test"
        assert node.children == []
        assert node.readonly is False
    
    def test_node_with_children(self):
        """测试带子节点的节点"""
        child = CatalogTreeNode(
            id="child",
            name="child",
            display_name="子节点",
            node_type="schema"
        )
        
        parent = CatalogTreeNode(
            id="parent",
            name="parent",
            display_name="父节点",
            node_type="catalog",
            children=[child]
        )
        
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"
    
    def test_nested_tree(self):
        """测试嵌套树结构"""
        asset = CatalogTreeNode(
            id="asset",
            name="data.csv",
            display_name="data.csv",
            node_type="table"
        )
        
        schema = CatalogTreeNode(
            id="schema",
            name="data",
            display_name="data",
            node_type="schema",
            children=[asset]
        )
        
        catalog = CatalogTreeNode(
            id="catalog",
            name="test",
            display_name="测试",
            node_type="catalog",
            children=[schema]
        )
        
        assert catalog.children[0].children[0].name == "data.csv"


class TestSpecificModels:
    """测试特定类型模型"""
    
    def test_table_model(self):
        """测试 Table 模型"""
        table = Table(
            id="test_table",
            name="sales",
            schema_id="test_schema",
            path="/test/sales.parquet",
            format="parquet"
        )
        
        assert table.format == "parquet"
        assert table.columns == []
        assert table.readonly is False
    
    def test_table_invalid_format(self):
        """测试 Table 模型 - 无效格式"""
        with pytest.raises(ValidationError):
            Table(
                id="test",
                name="test",
                schema_id="test",
                path="/test",
                format="invalid"
            )
    
    def test_volume_model(self):
        """测试 Volume 模型"""
        volume = Volume(
            id="test_volume",
            name="documents",
            schema_id="test_schema",
            path="/test/documents"
        )
        
        assert volume.volume_type == "local"  # 默认值为 local
        assert volume.file_count == 0
    
    def test_agent_model(self):
        """测试 Agent 模型"""
        now = datetime.now()
        agent = Agent(
            id="test_agent",
            name="chat_agent",
            catalog_id="test_catalog",
            description="聊天 Agent",
            path="/test/agents/chat_agent",
            created_at=now
        )
        
        assert agent.description == "聊天 Agent"
        assert agent.catalog_id == "test_catalog"
    
    def test_note_model(self):
        """测试 Note 模型"""
        now = datetime.now()
        note = Note(
            id="test_note",
            name="readme",
            schema_id="test_schema",
            content="# README",
            file_path="/test/readme.md",
            created_at=now,
            updated_at=now
        )
        
        assert note.content == "# README"


class TestEnums:
    """测试枚举类型"""
    
    def test_connection_type_values(self):
        """测试连接类型枚举值"""
        assert ConnectionType.MYSQL.value == "mysql"
        assert ConnectionType.POSTGRESQL.value == "postgresql"
        assert ConnectionType.SQLITE.value == "sqlite"
        assert ConnectionType.DUCKDB.value == "duckdb"
    
    def test_schema_source_values(self):
        """测试 Schema 来源枚举值"""
        assert SchemaSource.LOCAL.value == "local"
        assert SchemaSource.CONNECTION.value == "connection"
    
    def test_asset_type_values(self):
        """测试资产类型枚举值"""
        assert AssetType.TABLE.value == "table"
        assert AssetType.VOLUME.value == "volume"
        assert AssetType.AGENT.value == "agent"
        assert AssetType.NOTE.value == "note"
