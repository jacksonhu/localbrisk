"""
数据库连接器单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.models.catalog import ConnectionConfig, ConnectionType
from app.services.connectors.base import BaseConnector, ConnectorFactory
from app.services.connectors.mysql_connector import MySQLConnector, MYSQL_SYSTEM_SCHEMAS


class TestConnectorFactory:
    """连接器工厂测试"""
    
    def test_mysql_connector_registered(self):
        """测试 MySQL 连接器已注册"""
        assert ConnectorFactory.is_supported(ConnectionType.MYSQL)
    
    def test_get_supported_types(self):
        """测试获取支持的类型"""
        types = ConnectorFactory.get_supported_types()
        assert ConnectionType.MYSQL in types
    
    def test_create_mysql_connector(self):
        """测试创建 MySQL 连接器"""
        config = ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test",
            username="root",
            password="password",
        )
        
        connector = ConnectorFactory.create(config)
        
        assert connector is not None
        assert isinstance(connector, MySQLConnector)
        assert connector.config == config
    
    def test_create_unsupported_type(self):
        """测试创建不支持的类型返回 None"""
        # 假设 SQLITE 还没有实现连接器
        # 如果已经实现了，这个测试需要调整
        config = ConnectionConfig(
            type=ConnectionType.SQLITE,
            port=0,
            db_name="test.db",
        )
        
        connector = ConnectorFactory.create(config)
        
        # 如果 SQLITE 没有注册，应该返回 None
        if not ConnectorFactory.is_supported(ConnectionType.SQLITE):
            assert connector is None


class TestMySQLConnector:
    """MySQL 连接器测试"""
    
    @pytest.fixture
    def mysql_config(self):
        """MySQL 配置"""
        return ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test_db",
            username="root",
            password="password",
        )
    
    @pytest.fixture
    def mock_pymysql(self):
        """模拟 PyMySQL 模块"""
        with patch.dict("sys.modules", {"pymysql": MagicMock()}):
            import sys
            mock = sys.modules["pymysql"]
            mock.cursors = MagicMock()
            mock.cursors.DictCursor = dict
            yield mock
    
    def test_connection_type(self, mysql_config):
        """测试连接类型"""
        connector = MySQLConnector(mysql_config)
        assert connector.connection_type == ConnectionType.MYSQL
    
    def test_connect_success(self, mysql_config, mock_pymysql):
        """测试成功连接"""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        result = connector.connect()
        
        assert result is True
        assert connector._connection == mock_conn
        mock_pymysql.connect.assert_called_once()
    
    def test_connect_failure(self, mysql_config, mock_pymysql):
        """测试连接失败"""
        mock_pymysql.connect.side_effect = Exception("Connection refused")
        
        connector = MySQLConnector(mysql_config)
        result = connector.connect()
        
        assert result is False
        assert connector._connection is None
    
    def test_disconnect(self, mysql_config, mock_pymysql):
        """测试断开连接"""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        connector.connect()
        connector.disconnect()
        
        mock_conn.close.assert_called_once()
        assert connector._connection is None
    
    def test_test_connection(self, mysql_config, mock_pymysql):
        """测试连接检测"""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        connector.connect()
        
        result = connector.test_connection()
        
        assert result is True
        mock_conn.ping.assert_called_once_with(reconnect=True)
    
    def test_get_schemas_excludes_system_dbs(self, mysql_config, mock_pymysql):
        """测试获取 Schema 排除系统数据库"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"SCHEMA_NAME": "information_schema"},
            {"SCHEMA_NAME": "mysql"},
            {"SCHEMA_NAME": "performance_schema"},
            {"SCHEMA_NAME": "sys"},
            {"SCHEMA_NAME": "test_db"},
            {"SCHEMA_NAME": "user_db"},
        ]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        connector.connect()
        
        schemas = connector.get_schemas()
        
        # 应该只返回 test_db（配置的数据库）
        assert len(schemas) == 1
        assert "test_db" in schemas
        
        # 系统数据库应该被排除
        for sys_db in MYSQL_SYSTEM_SCHEMAS:
            assert sys_db not in schemas
    
    def test_get_tables(self, mysql_config, mock_pymysql):
        """测试获取表列表"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"TABLE_NAME": "users"},
            {"TABLE_NAME": "orders"},
            {"TABLE_NAME": "products"},
        ]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        connector.connect()
        
        tables = connector.get_tables("test_db")
        
        assert len(tables) == 3
        assert "users" in tables
        assert "orders" in tables
        assert "products" in tables
    
    def test_get_columns(self, mysql_config, mock_pymysql):
        """测试获取字段列表"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "COLUMN_NAME": "id",
                "DATA_TYPE": "int",
                "COLUMN_TYPE": "int(11)",
                "IS_NULLABLE": "NO",
                "COLUMN_DEFAULT": None,
                "COLUMN_KEY": "PRI",
                "EXTRA": "auto_increment",
                "COLUMN_COMMENT": "主键",
                "ORDINAL_POSITION": 1,
                "CHARACTER_MAXIMUM_LENGTH": None,
                "NUMERIC_PRECISION": 10,
                "NUMERIC_SCALE": 0,
            },
            {
                "COLUMN_NAME": "username",
                "DATA_TYPE": "varchar",
                "COLUMN_TYPE": "varchar(50)",
                "IS_NULLABLE": "NO",
                "COLUMN_DEFAULT": None,
                "COLUMN_KEY": "",
                "EXTRA": "",
                "COLUMN_COMMENT": "用户名",
                "ORDINAL_POSITION": 2,
                "CHARACTER_MAXIMUM_LENGTH": 50,
                "NUMERIC_PRECISION": None,
                "NUMERIC_SCALE": None,
            },
        ]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn
        
        connector = MySQLConnector(mysql_config)
        connector.connect()
        
        columns = connector.get_columns("test_db", "users")
        
        assert len(columns) == 2
        
        # 验证第一个字段
        id_col = columns[0]
        assert id_col.name == "id"
        assert id_col.data_type == "int(11)"
        assert id_col.nullable is False
        assert id_col.is_primary_key is True
        assert id_col.is_auto_increment is True
        
        # 验证第二个字段
        username_col = columns[1]
        assert username_col.name == "username"
        assert username_col.data_type == "varchar(50)"
        assert username_col.comment == "用户名"
    
    def test_context_manager(self, mysql_config, mock_pymysql):
        """测试上下文管理器"""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        
        with MySQLConnector(mysql_config) as connector:
            assert connector._connection == mock_conn
        
        mock_conn.close.assert_called_once()


class TestBaseConnector:
    """基类连接器测试"""
    
    def test_get_full_metadata(self):
        """测试获取完整元数据"""
        # 创建一个模拟的连接器实现
        class MockConnector(BaseConnector):
            @property
            def connection_type(self):
                return ConnectionType.MYSQL
            
            def connect(self):
                return True
            
            def disconnect(self):
                pass
            
            def test_connection(self):
                return True
            
            def get_schemas(self):
                return ["db1", "db2"]
            
            def get_schema_metadata(self, schema_name):
                from app.models.metadata import SchemaMetadata
                return SchemaMetadata(
                    name=schema_name,
                    catalog_name="test",
                    connection_type="mysql",
                )
            
            def get_tables(self, schema_name):
                return ["table1", "table2"]
            
            def get_table_metadata(self, schema_name, table_name):
                from app.models.metadata import TableMetadata
                return TableMetadata(
                    name=table_name,
                    schema_name=schema_name,
                    catalog_name="test",
                )
            
            def get_columns(self, schema_name, table_name):
                return []
        
        config = ConnectionConfig(
            type=ConnectionType.MYSQL,
            host="localhost",
            port=3306,
            db_name="test",
        )
        
        connector = MockConnector(config)
        metadata = connector.get_full_metadata()
        
        assert len(metadata) == 2
        assert metadata[0].name == "db1"
        assert metadata[1].name == "db2"
        assert len(metadata[0].tables) == 2
