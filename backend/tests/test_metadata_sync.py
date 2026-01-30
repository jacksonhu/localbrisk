"""
元数据同步服务单元测试

注意: MetadataSyncService 的 catalog_path 参数应该指向 schemas 目录
（即 App_Data/Catalogs/{catalog_name}/schemas/）
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import yaml

from app.models.catalog import ConnectionConfig, ConnectionType
from app.models.metadata import SchemaMetadata, TableMetadata, ColumnMetadata, SyncResult


def _reimport_metadata_sync_service():
    """重新导入 metadata_sync_service 模块"""
    for mod in list(sys.modules.keys()):
        if 'metadata_sync_service' in mod:
            del sys.modules[mod]
    from app.services.metadata_sync_service import MetadataSyncService
    return MetadataSyncService


@pytest.fixture
def temp_schemas_dir(tmp_path):
    """创建临时 schemas 目录（模拟 catalog/schemas/ 结构）"""
    schemas_dir = tmp_path / "test_catalog" / "schemas"
    schemas_dir.mkdir(parents=True)
    return schemas_dir


@pytest.fixture
def mock_connector():
    """创建模拟的数据库连接器"""
    connector = Mock()
    connector.connect.return_value = True
    connector.disconnect.return_value = None
    return connector


@pytest.fixture
def sample_schema_metadata():
    """创建示例 Schema 元数据"""
    return SchemaMetadata(
        name="test_db",
        catalog_name="test_catalog",
        character_set="utf8mb4",
        collation="utf8mb4_unicode_ci",
        connection_type="mysql",
        connection_host="localhost",
        connection_port=3306,
        synced_at=datetime.now(),
        table_count=2,
        tables=[
            TableMetadata(
                name="users",
                schema_name="test_db",
                catalog_name="test_catalog",
                table_type="BASE TABLE",
                engine="InnoDB",
                comment="用户表",
                row_count=100,
                create_time=datetime(2024, 1, 1, 10, 0, 0),
                columns=[
                    ColumnMetadata(
                        name="id",
                        data_type="int(11)",
                        nullable=False,
                        is_primary_key=True,
                        is_auto_increment=True,
                        ordinal_position=1,
                    ),
                    ColumnMetadata(
                        name="username",
                        data_type="varchar(50)",
                        nullable=False,
                        comment="用户名",
                        ordinal_position=2,
                    ),
                    ColumnMetadata(
                        name="email",
                        data_type="varchar(100)",
                        nullable=True,
                        ordinal_position=3,
                    ),
                ],
                primary_keys=["id"],
            ),
            TableMetadata(
                name="orders",
                schema_name="test_db",
                catalog_name="test_catalog",
                table_type="BASE TABLE",
                engine="InnoDB",
                comment="订单表",
                row_count=1000,
                create_time=datetime(2024, 1, 1, 10, 0, 0),
                columns=[
                    ColumnMetadata(
                        name="id",
                        data_type="bigint(20)",
                        nullable=False,
                        is_primary_key=True,
                        ordinal_position=1,
                    ),
                    ColumnMetadata(
                        name="user_id",
                        data_type="int(11)",
                        nullable=False,
                        ordinal_position=2,
                    ),
                ],
                primary_keys=["id"],
            ),
        ],
    )


class TestMetadataSyncService:
    """元数据同步服务测试"""
    
    def test_init(self, temp_schemas_dir):
        """测试服务初始化"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        assert service.catalog_path == temp_schemas_dir
        assert service.catalog_id == "test_catalog"
    
    def test_save_schema_metadata(self, temp_schemas_dir, sample_schema_metadata):
        """测试保存 Schema 元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        # 保存元数据
        schema_dir = service._save_schema_metadata(sample_schema_metadata)
        
        # 验证 Schema 目录已创建
        assert schema_dir.exists()
        assert schema_dir.name == "test_db"
        
        # 验证 schema.yaml 已创建
        meta_path = schema_dir / "schema.yaml"
        assert meta_path.exists()
        
        # 读取并验证内容
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        
        assert meta["name"] == "test_db"
        assert meta["source"] == "connection"
        assert meta["connection_type"] == "mysql"
        assert meta["readonly"] is True
        
        # 验证表文件已创建（在 tables 子目录下）
        tables_dir = schema_dir / "tables"
        assert tables_dir.exists()
        users_table = tables_dir / "users.yaml"
        orders_table = tables_dir / "orders.yaml"
        assert users_table.exists()
        assert orders_table.exists()
    
    def test_save_table_metadata(self, temp_schemas_dir, sample_schema_metadata):
        """测试保存表元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        schema_dir = temp_schemas_dir / "test_db"
        schema_dir.mkdir()
        
        table_meta = sample_schema_metadata.tables[0]  # users 表
        table_path = service._save_table_metadata(schema_dir, table_meta)
        
        # 验证文件已创建在 tables 子目录下
        assert table_path.exists()
        assert table_path.name == "users.yaml"
        assert table_path.parent.name == "tables"
        
        # 读取并验证内容
        with open(table_path, "r", encoding="utf-8") as f:
            table_data = yaml.safe_load(f)
        
        assert table_data["name"] == "users"
        assert table_data["comment"] == "用户表"
        assert len(table_data["columns"]) == 3
        assert table_data["columns"][0]["name"] == "id"
        assert table_data["columns"][0]["is_primary_key"] is True
    
    def test_load_schema_metadata(self, temp_schemas_dir):
        """测试加载 Schema 元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        # 创建 Schema 目录和 schema.yaml
        schema_dir = temp_schemas_dir / "test_db"
        schema_dir.mkdir()
        
        meta_data = {
            "name": "test_db",
            "source": "connection",
            "connection_type": "mysql",
        }
        
        with open(schema_dir / "schema.yaml", "w", encoding="utf-8") as f:
            yaml.dump(meta_data, f)
        
        # 加载并验证
        loaded = service.load_schema_metadata("test_db")
        assert loaded is not None
        assert loaded["name"] == "test_db"
        assert loaded["source"] == "connection"
    
    def test_load_table_metadata(self, temp_schemas_dir):
        """测试加载表元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        # 创建 Schema 目录和表文件（在 tables 子目录下）
        schema_dir = temp_schemas_dir / "test_db"
        tables_dir = schema_dir / "tables"
        tables_dir.mkdir(parents=True)
        
        table_data = {
            "name": "users",
            "columns": [{"name": "id", "data_type": "int"}],
        }
        
        with open(tables_dir / "users.yaml", "w", encoding="utf-8") as f:
            yaml.dump(table_data, f)
        
        # 加载并验证
        loaded = service.load_table_metadata("test_db", "users")
        assert loaded is not None
        assert loaded["name"] == "users"
        assert len(loaded["columns"]) == 1
    
    def test_get_synced_schemas(self, temp_schemas_dir):
        """测试获取已同步的 Schema 列表"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        # 创建一个连接同步的 Schema
        conn_schema = temp_schemas_dir / "conn_db"
        conn_schema.mkdir()
        with open(conn_schema / "schema.yaml", "w") as f:
            yaml.dump({"name": "conn_db", "source": "connection"}, f)
        
        # 创建一个本地 Schema
        local_schema = temp_schemas_dir / "local_db"
        local_schema.mkdir()
        with open(local_schema / "schema.yaml", "w") as f:
            yaml.dump({"name": "local_db", "source": "local"}, f)
        
        # 创建一个没有 schema.yaml 的目录
        no_meta = temp_schemas_dir / "no_meta"
        no_meta.mkdir()
        
        # 获取已同步的 Schema
        synced = service.get_synced_schemas()
        
        assert len(synced) == 1
        assert "conn_db" in synced
        assert "local_db" not in synced
    
    def test_sync_connection_success(self, temp_schemas_dir, sample_schema_metadata):
        """测试同步连接成功的情况"""
        # 重新导入以确保 patch 正确工作
        MetadataSyncService = _reimport_metadata_sync_service()
        
        # 设置模拟连接器
        mock_connector = Mock()
        mock_connector.connect.return_value = True
        mock_connector.disconnect.return_value = None
        mock_connector.get_full_metadata.return_value = [sample_schema_metadata]
        
        with patch("app.services.metadata_sync_service.ConnectorFactory") as mock_factory:
            mock_factory.create.return_value = mock_connector
            
            service = MetadataSyncService(temp_schemas_dir, "test_catalog")
            
            connection = ConnectionConfig(
                type=ConnectionType.MYSQL,
                host="localhost",
                port=3306,
                db_name="test_db",
                username="root",
                password="password",
                sync_schema=True,
            )
            
            result = service.sync_connection(connection)
        
        # 验证结果
        assert result.success is True
        assert result.schemas_synced == 1
        assert result.tables_synced == 2
        assert result.columns_synced == 5  # 3 + 2
        
        # 验证文件已创建
        schema_dir = temp_schemas_dir / "test_db"
        assert schema_dir.exists()
        assert (schema_dir / "schema.yaml").exists()
        # 表文件在 tables 子目录下
        tables_dir = schema_dir / "tables"
        assert tables_dir.exists()
        assert (tables_dir / "users.yaml").exists()
        assert (tables_dir / "orders.yaml").exists()
    
    @patch("app.services.metadata_sync_service.ConnectorFactory")
    def test_sync_connection_skip_when_sync_disabled(self, mock_factory, temp_schemas_dir):
        """测试禁用同步时跳过"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        connection = ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test_db",
            sync_schema=False,  # 禁用同步
        )
        
        result = service.sync_connection(connection)
        
        # 验证结果
        assert result.success is True
        assert result.schemas_synced == 0
        
        # 验证未调用连接器
        mock_factory.create.assert_not_called()
    
    @patch("app.services.metadata_sync_service.ConnectorFactory")
    def test_sync_connection_unsupported_type(self, mock_factory, temp_schemas_dir):
        """测试不支持的连接类型"""
        mock_factory.create.return_value = None  # 不支持的类型返回 None
        
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        connection = ConnectionConfig(
            type=ConnectionType.POSTGRESQL,  # 假设还未实现
            host="localhost",
            port=5432,
            db_name="test_db",
            sync_schema=True,
        )
        
        result = service.sync_connection(connection)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "不支持的连接类型" in result.errors[0]
    
    @patch("app.services.metadata_sync_service.ConnectorFactory")
    def test_sync_connection_failed_to_connect(self, mock_factory, temp_schemas_dir, mock_connector):
        """测试连接失败的情况"""
        mock_connector.connect.return_value = False
        mock_factory.create.return_value = mock_connector
        
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        
        connection = ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test_db",
            sync_schema=True,
        )
        
        result = service.sync_connection(connection)
        
        assert result.success is False
        assert "无法连接到数据库" in result.errors[0]


class TestYamlOutput:
    """测试 YAML 输出格式"""
    
    def test_chinese_characters_preserved(self, temp_schemas_dir, sample_schema_metadata):
        """测试中文字符正确保存"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        service._save_schema_metadata(sample_schema_metadata)
        
        # 读取表文件验证中文（表文件在 tables 子目录下）
        users_path = temp_schemas_dir / "test_db" / "tables" / "users.yaml"
        with open(users_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证中文没有被转义
        assert "用户表" in content
        assert "\\u" not in content  # 没有 unicode 转义
    
    def test_yaml_format_readability(self, temp_schemas_dir, sample_schema_metadata):
        """测试 YAML 格式的可读性"""
        from app.services.metadata_sync_service import MetadataSyncService
        service = MetadataSyncService(temp_schemas_dir, "test_catalog")
        service._save_schema_metadata(sample_schema_metadata)
        
        # 读取文件
        meta_path = temp_schemas_dir / "test_db" / "schema.yaml"
        with open(meta_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 验证格式（应该是多行，缩进格式）
        assert "\n" in content
        lines = content.split("\n")
        assert len(lines) > 1  # 多行
