"""
MySQL Database Connector
Implements metadata reading for MySQL/MariaDB databases
"""

from datetime import datetime
from typing import List, Optional
import logging

from app.models.business_unit import ConnectionConfig, ConnectionType
from app.models.metadata import SchemaMetadata, TableMetadata, ColumnMetadata
from .base import BaseConnector, ConnectorFactory

logger = logging.getLogger(__name__)

# MySQL system databases (usually not needed for sync)
MYSQL_SYSTEM_SCHEMAS = {
    "information_schema",
    "mysql",
    "performance_schema",
    "sys",
}


@ConnectorFactory.register(ConnectionType.MYSQL)
class MySQLConnector(BaseConnector):
    """
    MySQL Database Connector
    Uses PyMySQL driver to connect to MySQL/MariaDB databases
    """
    
    @property
    def connection_type(self) -> ConnectionType:
        return ConnectionType.MYSQL
    
    def connect(self) -> bool:
        """Establish MySQL connection"""
        try:
            import pymysql
            
            self._connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.db_name if self.config.db_name else None,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
            )
            logger.info(f"Successfully connected to MySQL: {self.config.host}:{self.config.port}")
            return True
        except ImportError:
            logger.error("PyMySQL driver not installed, please run: pip install pymysql")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close MySQL connection"""
        if self._connection:
            try:
                self._connection.close()
                logger.debug("MySQL connection closed")
            except Exception as e:
                logger.warning(f"Error closing MySQL connection: {e}")
            finally:
                self._connection = None
    
    def test_connection(self) -> bool:
        """Test MySQL connection"""
        try:
            if self._connection is None:
                return False
            self._connection.ping(reconnect=True)
            return True
        except Exception:
            return False
    
    def _execute_query(self, sql: str, params: tuple = None) -> List[dict]:
        """
        Execute SQL query
        
        Args:
            sql: SQL statement
            params: Query parameters (using parameterized queries to prevent SQL injection)
            
        Returns:
            List of query results
        """
        if self._connection is None:
            raise RuntimeError("Database not connected")
        
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def get_schemas(self) -> List[str]:
        """Get all database names (excluding system databases)"""
        sql = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME"
        
        results = self._execute_query(sql)
        schemas = [
            row["SCHEMA_NAME"]
            for row in results
            if row["SCHEMA_NAME"].lower() not in MYSQL_SYSTEM_SCHEMAS
        ]
        
        # If a specific database is configured, return only that database
        if self.config.db_name and self.config.db_name in schemas:
            return [self.config.db_name]
        
        return schemas
    
    def get_schema_metadata(self, schema_name: str) -> Optional[SchemaMetadata]:
        """Get metadata for specified database"""
        sql = """
            SELECT 
                SCHEMA_NAME,
                DEFAULT_CHARACTER_SET_NAME,
                DEFAULT_COLLATION_NAME
            FROM information_schema.SCHEMATA
            WHERE SCHEMA_NAME = %s
        """
        
        results = self._execute_query(sql, (schema_name,))
        if not results:
            return None
        
        row = results[0]
        return SchemaMetadata(
            name=row["SCHEMA_NAME"],
            catalog_name="",  # Set externally
            character_set=row["DEFAULT_CHARACTER_SET_NAME"],
            collation=row["DEFAULT_COLLATION_NAME"],
            connection_type=self.connection_type.value,
            connection_host=self.config.host,
            connection_port=self.config.port,
            synced_at=datetime.now(),
        )
    
    def get_tables(self, schema_name: str) -> List[str]:
        """Get all table names under specified database"""
        sql = """
            SELECT TABLE_NAME 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = %s
            AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
            ORDER BY TABLE_NAME
        """
        
        results = self._execute_query(sql, (schema_name,))
        return [row["TABLE_NAME"] for row in results]
    
    def get_table_metadata(self, schema_name: str, table_name: str) -> Optional[TableMetadata]:
        """Get metadata for specified table"""
        # Get table basic info
        sql = """
            SELECT 
                TABLE_NAME,
                TABLE_SCHEMA,
                TABLE_TYPE,
                ENGINE,
                TABLE_COMMENT,
                TABLE_ROWS,
                DATA_LENGTH,
                CREATE_TIME,
                UPDATE_TIME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        """
        
        results = self._execute_query(sql, (schema_name, table_name))
        if not results:
            return None
        
        row = results[0]
        
        # Get column metadata
        columns = self.get_columns(schema_name, table_name)
        
        # Get primary key info
        primary_keys = self._get_primary_keys(schema_name, table_name)
        
        # Get index info
        indexes = self._get_indexes(schema_name, table_name)
        
        # Get foreign key info
        foreign_keys = self._get_foreign_keys(schema_name, table_name)
        
        return TableMetadata(
            name=row["TABLE_NAME"],
            schema_name=row["TABLE_SCHEMA"],
            catalog_name="",  # Set externally
            table_type=row["TABLE_TYPE"],
            engine=row["ENGINE"],
            comment=row["TABLE_COMMENT"] if row["TABLE_COMMENT"] else None,
            row_count=row["TABLE_ROWS"],
            data_length=row["DATA_LENGTH"],
            create_time=row["CREATE_TIME"],
            update_time=row["UPDATE_TIME"],
            columns=columns,
            primary_keys=primary_keys,
            indexes=indexes,
            foreign_keys=foreign_keys,
        )
    
    def get_columns(self, schema_name: str, table_name: str) -> List[ColumnMetadata]:
        """Get all column metadata for specified table"""
        sql = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COLUMN_KEY,
                EXTRA,
                COLUMN_COMMENT,
                ORDINAL_POSITION,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        
        results = self._execute_query(sql, (schema_name, table_name))
        
        columns = []
        for row in results:
            column = ColumnMetadata(
                name=row["COLUMN_NAME"],
                data_type=row["COLUMN_TYPE"],  # Use full type like varchar(255)
                nullable=row["IS_NULLABLE"] == "YES",
                default_value=row["COLUMN_DEFAULT"],
                is_primary_key=row["COLUMN_KEY"] == "PRI",
                is_auto_increment="auto_increment" in (row["EXTRA"] or "").lower(),
                is_unique=row["COLUMN_KEY"] in ("PRI", "UNI"),
                comment=row["COLUMN_COMMENT"] if row["COLUMN_COMMENT"] else None,
                ordinal_position=row["ORDINAL_POSITION"],
                character_max_length=row["CHARACTER_MAXIMUM_LENGTH"],
                numeric_precision=row["NUMERIC_PRECISION"],
                numeric_scale=row["NUMERIC_SCALE"],
                extra={
                    "base_type": row["DATA_TYPE"],
                    "column_key": row["COLUMN_KEY"],
                    "extra": row["EXTRA"],
                },
            )
            columns.append(column)
        
        return columns
    
    def _get_primary_keys(self, schema_name: str, table_name: str) -> List[str]:
        """Get primary key column list"""
        sql = """
            SELECT COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = %s
            AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """
        
        results = self._execute_query(sql, (schema_name, table_name))
        return [row["COLUMN_NAME"] for row in results]
    
    def _get_indexes(self, schema_name: str, table_name: str) -> List[dict]:
        """Get index info"""
        sql = """
            SELECT 
                INDEX_NAME,
                NON_UNIQUE,
                COLUMN_NAME,
                SEQ_IN_INDEX,
                INDEX_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        
        results = self._execute_query(sql, (schema_name, table_name))
        
        # Group by index name
        indexes_dict = {}
        for row in results:
            idx_name = row["INDEX_NAME"]
            if idx_name not in indexes_dict:
                indexes_dict[idx_name] = {
                    "name": idx_name,
                    "unique": row["NON_UNIQUE"] == 0,
                    "type": row["INDEX_TYPE"],
                    "columns": [],
                }
            indexes_dict[idx_name]["columns"].append(row["COLUMN_NAME"])
        
        return list(indexes_dict.values())
    
    def _get_foreign_keys(self, schema_name: str, table_name: str) -> List[dict]:
        """Get foreign key info"""
        sql = """
            SELECT 
                kcu.CONSTRAINT_NAME,
                kcu.COLUMN_NAME,
                kcu.REFERENCED_TABLE_SCHEMA,
                kcu.REFERENCED_TABLE_NAME,
                kcu.REFERENCED_COLUMN_NAME,
                rc.UPDATE_RULE,
                rc.DELETE_RULE
            FROM information_schema.KEY_COLUMN_USAGE kcu
            JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                ON kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
                AND kcu.TABLE_SCHEMA = rc.CONSTRAINT_SCHEMA
            WHERE kcu.TABLE_SCHEMA = %s 
            AND kcu.TABLE_NAME = %s
            AND kcu.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION
        """
        
        results = self._execute_query(sql, (schema_name, table_name))
        
        # Group by foreign key name
        fk_dict = {}
        for row in results:
            fk_name = row["CONSTRAINT_NAME"]
            if fk_name not in fk_dict:
                fk_dict[fk_name] = {
                    "name": fk_name,
                    "columns": [],
                    "referenced_schema": row["REFERENCED_TABLE_SCHEMA"],
                    "referenced_table": row["REFERENCED_TABLE_NAME"],
                    "referenced_columns": [],
                    "on_update": row["UPDATE_RULE"],
                    "on_delete": row["DELETE_RULE"],
                }
            fk_dict[fk_name]["columns"].append(row["COLUMN_NAME"])
            fk_dict[fk_name]["referenced_columns"].append(row["REFERENCED_COLUMN_NAME"])
        
        return list(fk_dict.values())
    
    def preview_data(
        self, 
        schema_name: str, 
        table_name: str, 
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """
        Preview table data
        
        Args:
            schema_name: Schema name
            table_name: Table name
            limit: Row limit (最大 1000)
            offset: Offset
            
        Returns:
            contains columns 和 rows 的字典
        """
        # Limit maximum rows to return
        limit = min(limit, 1000)
        
        # Use backticks to escape identifiers to prevent SQL injection
        # Note: parameterized queries cannot be used here as table/column names cannot be parameters
        # But we ensure safety by validating table existence
        tables = self.get_tables(schema_name)
        if table_name not in tables:
            raise ValueError(f"Table does not exist: {schema_name}.{table_name}")
        
        # Get column info
        columns_meta = self.get_columns(schema_name, table_name)
        columns = [col.name for col in columns_meta]
        
        # Construct safe SQL (identifiers validated)
        sql = f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT %s OFFSET %s"
        
        rows = self._execute_query(sql, (limit, offset))
        
        # Get total row count (approximate)
        count_sql = f"SELECT COUNT(*) as cnt FROM `{schema_name}`.`{table_name}`"
        count_result = self._execute_query(count_sql)
        total = count_result[0]["cnt"] if count_result else 0
        
        return {
            "columns": columns,
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
