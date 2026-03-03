"""
AssetBundle 服务 - 管理 AssetBundle 及其 Asset
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from app.core.constants import (
    ASSET_BUNDLE_CONFIG_FILE, ASSET_FILE_SUFFIX,
    TABLES_DIR, VOLUMES_DIR, FUNCTIONS_DIR, NOTES_DIR,
    BUNDLE_ASSET_TYPE_TO_DIR,
)
from app.models.business_unit import (
    AssetBundle, AssetBundleCreate, AssetBundleUpdate,
    ConnectionConfig, EntityType,
    Asset, AssetCreate, AssetType,
)
from app.models.metadata import SyncResult
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.business_unit_service import BusinessUnitService

logger = logging.getLogger(__name__)


# Asset 类型目录映射
ASSET_TYPE_DIRS = {
    AssetType.TABLE: TABLES_DIR,
    AssetType.VOLUME: VOLUMES_DIR,
    AssetType.AGENT: "agents",
    AssetType.NOTE: NOTES_DIR,
}


class AssetBundleService(BaseService):
    """AssetBundle 服务类"""
    
    def __init__(self, business_unit_service: "BusinessUnitService"):
        super().__init__()
        self.business_unit_service = business_unit_service
    
    # ==================== 路径方法 ====================
    
    def _get_bundle_path(self, business_unit_id: str, bundle_name: str) -> Optional[Path]:
        """获取 AssetBundle 路径"""
        return self.business_unit_service.get_asset_bundle_path(business_unit_id, bundle_name)
    
    def _get_config_file_path(self, bundle_path: Path) -> Path:
        """获取配置文件路径"""
        return bundle_path / ASSET_BUNDLE_CONFIG_FILE
    
    def _get_type_dir(self, asset_type: AssetType) -> str:
        """获取 Asset 类型目录名"""
        if isinstance(asset_type, str):
            return ASSET_TYPE_DIRS.get(AssetType(asset_type), asset_type + "s")
        return ASSET_TYPE_DIRS.get(asset_type, str(asset_type.value) + "s")
    
    # ==================== AssetBundle CRUD ====================
    
    def scan_asset_bundles(self, bu_path: Path, business_unit_id: str) -> List[AssetBundle]:
        """扫描 AssetBundle"""
        logger.debug(f"扫描 AssetBundle: {business_unit_id}")
        bundles_dir = self.business_unit_service.get_asset_bundles_dir(bu_path)
        bundles = self._scan_subdirs(bundles_dir, lambda p: self._load_bundle(business_unit_id, p))
        logger.debug(f"发现 {len(bundles)} 个 AssetBundle")
        return bundles
    
    def _load_bundle(self, business_unit_id: str, bundle_path: Path) -> Optional[AssetBundle]:
        """加载 AssetBundle"""
        logger.debug(f"加载 AssetBundle: {bundle_path.name}")
        config = self._load_yaml(self._get_config_file_path(bundle_path)) or {}
        baseinfo = self._extract_baseinfo(config, bundle_path.name)
        
        connection = ConnectionConfig(**config["connection"]) if config.get("connection") else None
        
        bundle_type = config.get("bundle_type", "local")
        
        return AssetBundle(
            id=f"{business_unit_id}_{bundle_path.name}",
            name=bundle_path.name,
            display_name=baseinfo.get("display_name") or bundle_path.name,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            owner=baseinfo.get("owner", "admin"),
            business_unit_id=business_unit_id,
            entity_type=EntityType.ASSET_BUNDLE,
            bundle_type=bundle_type,
            connection=connection,
            path=str(bundle_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            synced_at=self._parse_datetime(config.get("synced_at")),
        )
    
    def get_asset_bundles(self, business_unit_id: str) -> List[AssetBundle]:
        """获取 AssetBundle 列表"""
        bu = self.business_unit_service.get_business_unit(business_unit_id)
        return bu.asset_bundles if bu else []
    
    def get_asset_bundle_config_content(self, business_unit_id: str, bundle_name: str) -> Optional[str]:
        """获取 AssetBundle 配置内容"""
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            return None
        return self._read_file(self._get_config_file_path(bundle_path))
    
    def create_asset_bundle(self, business_unit_id: str, data: AssetBundleCreate) -> AssetBundle:
        """创建 AssetBundle"""
        logger.info(f"创建 AssetBundle: {business_unit_id}/{data.name}")
        bu_path = self.business_unit_service.get_business_unit_path(business_unit_id)
        if not bu_path.exists():
            logger.warning(f"BusinessUnit 不存在: {business_unit_id}")
            raise ValueError(f"BusinessUnit '{business_unit_id}' 不存在")
        
        bundle_type = data.bundle_type or "local"
        if bundle_type == "external" and not data.connection:
            raise ValueError("External 类型必须配置数据库连接")
        
        bundles_dir = self.business_unit_service.get_asset_bundles_dir(bu_path)
        bundles_dir.mkdir(parents=True, exist_ok=True)
        
        bundle_path = bundles_dir / data.name
        if bundle_path.exists():
            logger.warning(f"AssetBundle 已存在: {data.name}")
            raise ValueError(f"AssetBundle '{data.name}' 已存在")
        
        # 创建目录结构（不再创建 models 目录，Model 已移到 Agent 下）
        bundle_path.mkdir(parents=True, exist_ok=True)
        for dir_name in ["tables", "functions", "volumes"]:
            (bundle_path / dir_name).mkdir(exist_ok=True)
        
        # 创建配置
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        config = {"baseinfo": baseinfo, "bundle_type": bundle_type}
        
        connection = data.connection if bundle_type == "external" else None
        if connection:
            config["connection"] = connection.model_dump()
            # 同步外部元数据
            logger.info(f"同步外部元数据: {data.name}")
            sync_result = self._sync_metadata(bundle_path, business_unit_id, data.name, connection)
            if sync_result.success:
                config["synced_at"] = self._now_iso()
                logger.info(f"元数据同步成功: {data.name}")
            else:
                logger.warning(f"元数据同步失败: {sync_result.errors}")
        
        self._save_yaml(bundle_path / ASSET_BUNDLE_CONFIG_FILE, config)
        logger.info(f"AssetBundle 创建成功: {data.name}")
        return self._load_bundle(business_unit_id, bundle_path)
    
    def update_asset_bundle(self, business_unit_id: str, bundle_name: str, update: AssetBundleUpdate) -> Optional[AssetBundle]:
        """更新 AssetBundle"""
        logger.info(f"更新 AssetBundle: {business_unit_id}/{bundle_name}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            logger.warning(f"AssetBundle 不存在: {bundle_name}")
            return None
        
        config_path = self._get_config_file_path(bundle_path)
        config = self._load_yaml(config_path) or {}
        baseinfo = self._extract_baseinfo(config, bundle_path.name)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        bundle_type = config.get("bundle_type", "local")
        if update.connection is not None and bundle_type == "external":
            config["connection"] = update.connection.model_dump()
        
        config["baseinfo"] = baseinfo
        self._save_yaml(config_path, config)
        logger.info(f"AssetBundle 更新成功: {bundle_name}")
        return self._load_bundle(business_unit_id, bundle_path)
    
    def delete_asset_bundle(self, business_unit_id: str, bundle_name: str) -> bool:
        """删除 AssetBundle"""
        logger.info(f"删除 AssetBundle: {business_unit_id}/{bundle_name}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        result = self._remove_dir(bundle_path) if bundle_path else False
        if result:
            logger.info(f"AssetBundle 删除成功: {bundle_name}")
        else:
            logger.warning(f"AssetBundle 不存在: {bundle_name}")
        return result
    
    def _sync_metadata(self, bundle_path: Path, business_unit_id: str, bundle_name: str, connection: ConnectionConfig) -> SyncResult:
        """同步 AssetBundle 元数据"""
        from app.services.metadata_sync_service import MetadataSyncService
        sync_service = MetadataSyncService(bundle_path, business_unit_id, bundle_name)
        return sync_service.sync_connection(connection)
    
    def sync_asset_bundle_metadata(self, business_unit_id: str, bundle_name: str) -> SyncResult:
        """手动同步 AssetBundle 元数据"""
        logger.info(f"手动同步 AssetBundle 元数据: {business_unit_id}/{bundle_name}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            logger.warning(f"AssetBundle 不存在: {bundle_name}")
            return SyncResult(success=False, errors=[f"AssetBundle '{bundle_name}' 不存在"])
        
        config = self._load_yaml(self._get_config_file_path(bundle_path))
        if not config or not config.get("connection"):
            return SyncResult(success=False, errors=["AssetBundle 没有配置数据库连接"])
        
        connection = ConnectionConfig(**config["connection"])
        result = self._sync_metadata(bundle_path, business_unit_id, bundle_name, connection)
        
        if result.success:
            config["synced_at"] = self._now_iso()
            self._save_yaml(self._get_config_file_path(bundle_path), config)
            logger.info(f"元数据同步成功: {bundle_name}")
        else:
            logger.warning(f"元数据同步失败: {result.errors}")
        
        return result
    
    # ==================== Asset 操作 ====================
    
    def scan_assets(self, business_unit_id: str, bundle_name: str) -> List[Asset]:
        """扫描 AssetBundle 下的资产"""
        logger.debug(f"扫描 Asset: {business_unit_id}/{bundle_name}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            return []
        
        config = self._load_yaml(self._get_config_file_path(bundle_path))
        bundle_type = config.get("bundle_type", "local") if config else "local"
        is_external = bundle_type == "external"
        
        assets = []
        for asset_type, dir_name in ASSET_TYPE_DIRS.items():
            type_dir = bundle_path / dir_name
            if type_dir.exists() and type_dir.is_dir():
                assets.extend(self._scan_asset_dir(business_unit_id, bundle_name, type_dir, asset_type, is_external))
        
        # 函数目录
        functions_dir = bundle_path / FUNCTIONS_DIR
        if functions_dir.exists():
            assets.extend(self._scan_asset_dir(business_unit_id, bundle_name, functions_dir, AssetType.AGENT, is_external))
        
        logger.debug(f"发现 {len(assets)} 个 Asset")
        return assets
    
    def _scan_asset_dir(self, business_unit_id: str, bundle_name: str, type_dir: Path, asset_type: AssetType, is_external: bool) -> List[Asset]:
        """扫描资产目录"""
        assets = []
        for item in type_dir.iterdir():
            if item.name.startswith(".") or item.suffix != ".yaml":
                continue
            
            config = self._load_yaml(item) or {}
            baseinfo = self._extract_baseinfo(config, item.stem)
            
            metadata = {k: v for k, v in config.items() if k not in ["baseinfo", "name", "created_at", "updated_at"]}
            metadata["source"] = "synced" if is_external else "local"
            
            assets.append(Asset(
                id=f"{business_unit_id}_{bundle_name}_{item.stem}",
                name=baseinfo.get("name") or item.stem,
                display_name=baseinfo.get("display_name") or item.stem,
                description=baseinfo.get("description"),
                tags=baseinfo.get("tags", []),
                bundle_id=f"{business_unit_id}_{bundle_name}",
                asset_type=asset_type,
                entity_type=EntityType(asset_type.value) if asset_type.value in [e.value for e in EntityType] else EntityType.TABLE,
                path=str(item),
                metadata=metadata,
                created_at=self._parse_datetime(baseinfo.get("created_at")),
                updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            ))
        return assets
    
    def get_asset_config_content(self, business_unit_id: str, bundle_name: str, asset_name: str) -> Optional[str]:
        """获取 Asset 配置内容"""
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            return None
        
        for dir_name in list(ASSET_TYPE_DIRS.values()) + [FUNCTIONS_DIR]:
            asset_file = bundle_path / dir_name / f"{asset_name}{ASSET_FILE_SUFFIX}"
            content = self._read_file(asset_file)
            if content is not None:
                return content
        return None
    
    def create_asset(self, business_unit_id: str, bundle_name: str, data: AssetCreate) -> Asset:
        """创建 Asset"""
        logger.info(f"创建 Asset: {business_unit_id}/{bundle_name}/{data.name}, type={data.asset_type}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            logger.warning(f"AssetBundle 不存在: {bundle_name}")
            raise FileNotFoundError(f"AssetBundle '{bundle_name}' 不存在")
        
        type_dir = bundle_path / self._get_type_dir(data.asset_type)
        type_dir.mkdir(parents=True, exist_ok=True)
        
        asset_path = type_dir / f"{data.name}.yaml"
        if asset_path.exists():
            logger.warning(f"Asset 已存在: {data.name}")
            raise ValueError(f"资产 '{data.name}' 已存在")
        
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        
        asset_config = {
            "baseinfo": baseinfo,
            "asset_type": data.asset_type.value if hasattr(data.asset_type, 'value') else data.asset_type,
            "source": "local",
        }
        
        # 类型特有字段
        if data.asset_type == AssetType.VOLUME or data.asset_type == "volume":
            asset_config["volume_type"] = data.volume_type or "local"
            if data.volume_type == "local":
                asset_config["storage_location"] = data.storage_location
            elif data.volume_type == "s3":
                asset_config.update({
                    "s3_endpoint": data.s3_endpoint,
                    "s3_bucket": data.s3_bucket,
                    "s3_access_key": data.s3_access_key,
                    "s3_secret_key": data.s3_secret_key,
                })
        elif data.asset_type == AssetType.TABLE or data.asset_type == "table":
            asset_config["format"] = data.format
            asset_config["columns"] = []
        
        self._save_yaml(asset_path, asset_config)
        
        logger.info(f"Asset 创建成功: {data.name}")
        return Asset(
            id=f"{business_unit_id}_{bundle_name}_{data.name}",
            name=data.name,
            display_name=baseinfo["display_name"],
            description=baseinfo["description"],
            tags=baseinfo["tags"],
            bundle_id=f"{business_unit_id}_{bundle_name}",
            asset_type=data.asset_type,
            path=str(asset_path),
            metadata={"source": "local"},
            created_at=self._parse_datetime(baseinfo["created_at"]),
            updated_at=self._parse_datetime(baseinfo["updated_at"]),
        )
    
    def delete_asset(self, business_unit_id: str, bundle_name: str, asset_name: str) -> bool:
        """删除 Asset"""
        logger.info(f"删除 Asset: {business_unit_id}/{bundle_name}/{asset_name}")
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            return False
        
        for dir_name in list(ASSET_TYPE_DIRS.values()) + [FUNCTIONS_DIR]:
            asset_path = bundle_path / dir_name / f"{asset_name}.yaml"
            if asset_path.exists():
                asset_path.unlink()
                logger.info(f"Asset 删除成功: {asset_name}")
                return True
        
        logger.warning(f"Asset 不存在: {asset_name}")
        return False
    
    def preview_table_data(self, business_unit_id: str, bundle_name: str, table_name: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """预览表数据"""
        logger.debug(f"预览表数据: {business_unit_id}/{bundle_name}/{table_name}")
        from app.services.connectors import ConnectorFactory
        
        bundle_path = self._get_bundle_path(business_unit_id, bundle_name)
        if not bundle_path:
            raise ValueError(f"AssetBundle '{bundle_name}' 不存在")
        
        config = self._load_yaml(self._get_config_file_path(bundle_path))
        bundle_type = config.get("bundle_type") if config else None
        if bundle_type != "external":
            raise ValueError("只有 External 类型的 AssetBundle 支持数据预览")
        
        if not config.get("connection"):
            raise ValueError("AssetBundle 没有配置数据库连接")
        
        connection = ConnectionConfig(**config["connection"])
        connector = ConnectorFactory.create(connection)
        if not connector:
            raise ValueError(f"不支持的连接类型: {connection.type}")
        
        try:
            if not connector.connect():
                raise ValueError("无法连接到数据库")
            result = connector.preview_data(connection.db_name, table_name, limit, offset)
            logger.debug(f"表数据预览成功: {table_name}")
            return result
        finally:
            connector.disconnect()
