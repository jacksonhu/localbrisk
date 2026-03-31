"""
Database Connector Abstract Base Class
Defines unified database metadata reading interface, extensible for other database types
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type
import logging

from app.models.business_unit import ConnectionConfig, ConnectionType
from app.models.metadata import SchemaMetadata, TableMetadata, ColumnMetadata

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Database Connector Abstract Base Class
    All database connectors must inherit this class and implement its methods
    """
    
    def __init__(self, config: ConnectionConfig):
        """
        Initialize connector
        
        Args:
            config: Connection config
        """
        self.config = config
        self._connection = None
    
    @property
    @abstractmethod
    def connection_type(self) -> ConnectionType:
        """Return the database type supported by this connector"""
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            Whether connection succeeded
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if connection is healthy
        
        Returns:
            Whether connection is healthy
        """
        pass
    
    @abstractmethod
    def get_schemas(self) -> List[str]:
        """
        Get all database/schema names
        
        Returns:
            List of schema names
        """
        pass
    
    @abstractmethod
    def get_schema_metadata(self, schema_name: str) -> Optional[SchemaMetadata]:
        """
        Get metadata for specified schema
        
        Args:
            schema_name: Schema name
            
        Returns:
            SchemaMetadata object
        """
        pass
    
    @abstractmethod
    def get_tables(self, schema_name: str) -> List[str]:
        """
        Get all table names under specified schema
        
        Args:
            schema_name: Schema name
            
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    def get_table_metadata(self, schema_name: str, table_name: str) -> Optional[TableMetadata]:
        """
        Get metadata for specified table
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            TableMetadata 对象
        """
        pass
    
    @abstractmethod
    def get_columns(self, schema_name: str, table_name: str) -> List[ColumnMetadata]:
        """
        Get all column metadata for specified table
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            List of ColumnMetadata
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
        Preview table data
        
        Args:
            schema_name: Schema name
            table_name: Table name
            limit: Row limit
            offset: Offset
            
        Returns:
            contains columns 和 rows 的字典
        """
        raise NotImplementedError("This connector does not support data preview")
    
    def get_full_metadata(self, schema_name: Optional[str] = None) -> List[SchemaMetadata]:
        """
        Get full metadata (Schema + Tables + Columns)
        
        Args:
            schema_name: Optional, specify to get metadata for only one schema
            
        Returns:
            List of SchemaMetadata
        """
        schemas_metadata = []
        
        if schema_name:
            schema_names = [schema_name]
        else:
            schema_names = self.get_schemas()
        
        for name in schema_names:
            schema_meta = self.get_schema_metadata(name)
            if schema_meta:
                # Get all tables under this schema
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
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False


class ConnectorFactory:
    """
    Connector factory class
    Creates connector instances based on connection type
    """
    
    _connectors: Dict[ConnectionType, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, connection_type: ConnectionType):
        """
        Decorator for registering connector classes
        
        Args:
            connection_type: Connection type
        """
        def decorator(connector_class: Type[BaseConnector]):
            cls._connectors[connection_type] = connector_class
            logger.debug(f"Registering connector: {connection_type} -> {connector_class.__name__}")
            return connector_class
        return decorator
    
    @classmethod
    def create(cls, config: ConnectionConfig) -> Optional[BaseConnector]:
        """
        Create connector instance from config
        
        Args:
            config: Connection config
            
        Returns:
            BaseConnector 实例, Returns None if the type is not supported
        """
        connector_class = cls._connectors.get(config.type)
        if connector_class is None:
            logger.warning(f"Unsupported connection type: {config.type}")
            return None
        
        return connector_class(config)
    
    @classmethod
    def get_supported_types(cls) -> List[ConnectionType]:
        """
        Get所有支持的Connection type
        
        Returns:
            支持的Connection type列表
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def is_supported(cls, connection_type: ConnectionType) -> bool:
        """
        CheckWhether supported指定的Connection type
        
        Args:
            connection_type: Connection type
            
        Returns:
            Whether supported
        """
        return connection_type in cls._connectors
