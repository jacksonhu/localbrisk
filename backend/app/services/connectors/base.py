"""
数据库连接器抽象基类
定义统一的数据库元数据读取接口，支持扩展其他数据库类型
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
import logging

from app.models.catalog import ConnectionConfig, ConnectionType
from app.models.metadata import SchemaMetadata, TableMetadata, ColumnMetadata

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    数据库连接器抽象基类
    所有数据库连接器必须继承此类并实现相应的方法
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        初始化连接器
        
        Args:
            config: 连接配置
        """
        self.config = config
        self._connection = None
    
    @property
    @abstractmethod
    def connection_type(self) -> ConnectionType:
        """返回连接器支持的数据库类型"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            是否连接成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """关闭数据库连接"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        测试连接是否正常
        
        Returns:
            连接是否正常
        """
        pass
    
    @abstractmethod
    def get_schemas(self) -> List[str]:
        """
        获取所有数据库/Schema 名称
        
        Returns:
            Schema 名称列表
        """
        pass
    
    @abstractmethod
    def get_schema_metadata(self, schema_name: str) -> Optional[SchemaMetadata]:
        """
        获取指定 Schema 的元数据
        
        Args:
            schema_name: Schema 名称
            
        Returns:
            SchemaMetadata 对象
        """
        pass
    
    @abstractmethod
    def get_tables(self, schema_name: str) -> List[str]:
        """
        获取指定 Schema 下的所有表名
        
        Args:
            schema_name: Schema 名称
            
        Returns:
            表名列表
        """
        pass
    
    @abstractmethod
    def get_table_metadata(self, schema_name: str, table_name: str) -> Optional[TableMetadata]:
        """
        获取指定表的元数据
        
        Args:
            schema_name: Schema 名称
            table_name: 表名
            
        Returns:
            TableMetadata 对象
        """
        pass
    
    @abstractmethod
    def get_columns(self, schema_name: str, table_name: str) -> List[ColumnMetadata]:
        """
        获取指定表的所有字段元数据
        
        Args:
            schema_name: Schema 名称
            table_name: 表名
            
        Returns:
            ColumnMetadata 列表
        """
        pass
    
    def preview_data(
        self, 
        schema_name: str, 
        table_name: str, 
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        预览表数据
        
        Args:
            schema_name: Schema 名称
            table_name: 表名
            limit: 返回行数限制
            offset: 偏移量
            
        Returns:
            包含 columns 和 rows 的字典
        """
        raise NotImplementedError("该连接器不支持数据预览")
    
    def get_full_metadata(self, schema_name: Optional[str] = None) -> List[SchemaMetadata]:
        """
        获取完整的元数据（Schema + Tables + Columns）
        
        Args:
            schema_name: 可选，指定只获取某个 Schema 的元数据
            
        Returns:
            SchemaMetadata 列表
        """
        schemas_metadata = []
        
        if schema_name:
            schema_names = [schema_name]
        else:
            schema_names = self.get_schemas()
        
        for name in schema_names:
            schema_meta = self.get_schema_metadata(name)
            if schema_meta:
                # 获取该 Schema 下的所有表
                tables = []
                for table_name in self.get_tables(name):
                    table_meta = self.get_table_metadata(name, table_name)
                    if table_meta:
                        tables.append(table_meta)
                
                schema_meta.tables = tables
                schema_meta.table_count = len(tables)
                schemas_metadata.append(schema_meta)
        
        return schemas_metadata
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
        return False


class ConnectorFactory:
    """
    连接器工厂类
    根据连接类型创建对应的连接器实例
    """
    
    _connectors: Dict[ConnectionType, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, connection_type: ConnectionType):
        """
        注册连接器类的装饰器
        
        Args:
            connection_type: 连接类型
        """
        def decorator(connector_class: Type[BaseConnector]):
            cls._connectors[connection_type] = connector_class
            logger.debug(f"注册连接器: {connection_type} -> {connector_class.__name__}")
            return connector_class
        return decorator
    
    @classmethod
    def create(cls, config: ConnectionConfig) -> Optional[BaseConnector]:
        """
        根据配置创建连接器实例
        
        Args:
            config: 连接配置
            
        Returns:
            BaseConnector 实例，如果不支持该类型则返回 None
        """
        connector_class = cls._connectors.get(config.type)
        if connector_class is None:
            logger.warning(f"不支持的连接类型: {config.type}")
            return None
        
        return connector_class(config)
    
    @classmethod
    def get_supported_types(cls) -> List[ConnectionType]:
        """
        获取所有支持的连接类型
        
        Returns:
            支持的连接类型列表
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def is_supported(cls, connection_type: ConnectionType) -> bool:
        """
        检查是否支持指定的连接类型
        
        Args:
            connection_type: 连接类型
            
        Returns:
            是否支持
        """
        return connection_type in cls._connectors
