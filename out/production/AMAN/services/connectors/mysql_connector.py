"""
MySQL 数据库连接器
实现 MySQL/MariaDB 数据库的元数据读取
"""

from datetime import datetime
from typing import List, Optional
import logging

from app.models.business_unit import ConnectionConfig, ConnectionType
from app.models.metadata import SchemaMetadata, TableMetadata, ColumnMetadata
from .base import BaseConnector, ConnectorFactory

logger = logging.getLogger(__name__)

# MySQL 系统数据库列表（通常不需要同步）
MYSQL_SYSTEM_SCHEMAS = {
    "information_schema",
    "mysql",
    "performance_schema",
    "sys",
}


@ConnectorFactory.register(ConnectionType.MYSQL)
class MySQLConnector(BaseConnector):
    """
    MySQL 数据库连接器
    使用 PyMySQL 驱动连接 MySQL/MariaDB 数据库
    """
    
    @property
    def connection_type(self) -> ConnectionType:
        return ConnectionType.MYSQL
    
    def connect(self) -> bool:
        """建立 MySQL 连接"""
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
            logger.info(f"成功连接到 MySQL: {self.config.host}:{self.config.port}")
            return True
        except ImportError:
            logger.error("未安装 PyMySQL 驱动，请运行: pip install pymysql")
            return False
        except Exception as e:
            logger.error(f"连接 MySQL 失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """关闭 MySQL 连接"""
        if self._connection:
            try:
                self._connection.close()
                logger.debug("MySQL 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭 MySQL 连接时出错: {e}")
            finally:
                self._connection = None
    
    def test_connection(self) -> bool:
        """测试 MySQL 连接"""
        try:
            if self._connection is None:
                return False
            self._connection.ping(reconnect=True)
            return True
        except Exception:
            return False
    
    def _execute_query(self, sql: str, params: tuple = None) -> List[dict]:
        """
        执行 SQL 查询
        
        Args:
            sql: SQL 语句
            params: 查询参数（使用参数化查询防止 SQL 注入）
            
        Returns:
            查询结果列表
        """
        if self._connection is None:
            raise RuntimeError("数据库未连接")
        
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def get_schemas(self) -> List[str]:
        """获取所有数据库名称（排除系统数据库）"""
        sql = "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME"
        
        results = self._execute_query(sql)
        schemas = [
            row["SCHEMA_NAME"]
            for row in results
            if row["SCHEMA_NAME"].lower() not in MYSQL_SYSTEM_SCHEMAS
        ]
        
        # 如果配置了特定数据库，只返回该数据库
        if self.config.db_name and self.config.db_name in schemas:
            return [self.config.db_name]
        
        return schemas
    
    def get_schema_metadata(self, schema_name: str) -> Optional[SchemaMetadata]:
        """获取指定数据库的元数据"""
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
            catalog_name="",  # 将在外部设置
            character_set=row["DEFAULT_CHARACTER_SET_NAME"],
            collation=row["DEFAULT_COLLATION_NAME"],
            connection_type=self.connection_type.value,
            connection_host=self.config.host,
            connection_port=self.config.port,
            synced_at=datetime.now(),
        )
    
    def get_tables(self, schema_name: str) -> List[str]:
        """获取指定数据库下的所有表名"""
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
        """获取指定表的元数据"""
        # 获取表基本信息
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
        
        # 获取字段元数据
        columns = self.get_columns(schema_name, table_name)
        
        # 获取主键信息
        primary_keys = self._get_primary_keys(schema_name, table_name)
        
        # 获取索引信息
        indexes = self._get_indexes(schema_name, table_name)
        
        # 获取外键信息
        foreign_keys = self._get_foreign_keys(schema_name, table_name)
        
        return TableMetadata(
            name=row["TABLE_NAME"],
            schema_name=row["TABLE_SCHEMA"],
            catalog_name="",  # 将在外部设置
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
        """获取指定表的所有字段元数据"""
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
                data_type=row["COLUMN_TYPE"],  # 使用完整类型如 varchar(255)
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
        """获取主键字段列表"""
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
        """获取索引信息"""
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
        
        # 按索引名分组
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
        """获取外键信息"""
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
        
        # 按外键名分组
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
        预览表数据
        
        Args:
            schema_name: Schema 名称
            table_name: 表名
            limit: 返回行数限制（最大 1000）
            offset: 偏移量
            
        Returns:
            包含 columns 和 rows 的字典
        """
        # 限制最大返回行数
        limit = min(limit, 1000)
        
        # 使用反引号转义标识符，防止 SQL 注入
        # 注意：这里不能使用参数化查询，因为表名和列名不能作为参数
        # 但我们通过验证表是否存在来确保安全性
        tables = self.get_tables(schema_name)
        if table_name not in tables:
            raise ValueError(f"表不存在: {schema_name}.{table_name}")
        
        # 获取列信息
        columns_meta = self.get_columns(schema_name, table_name)
        columns = [col.name for col in columns_meta]
        
        # 构造安全的 SQL（标识符已验证）
        sql = f"SELECT * FROM `{schema_name}`.`{table_name}` LIMIT %s OFFSET %s"
        
        rows = self._execute_query(sql, (limit, offset))
        
        # 获取总行数（近似值）
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
