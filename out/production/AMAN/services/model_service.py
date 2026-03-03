"""
Model 服务 - 管理 Model
"""

import logging
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from app.core.constants import MODELS_DIR
from app.models.business_unit import Model, ModelCreate, ModelUpdate, EntityType
from app.services.base_service import BaseService

if TYPE_CHECKING:
    from app.services.catalog_service_new import CatalogService

logger = logging.getLogger(__name__)


class ModelService(BaseService):
    """Model 服务类"""
    
    def __init__(self, catalog_service: "CatalogService"):
        super().__init__()
        self.catalog_service = catalog_service
    
    # ==================== Model CRUD ====================
    
    def _get_models_dir(self, catalog_id: str, schema_name: str) -> Optional[Path]:
        """获取 Models 目录路径"""
        schema_path = self.catalog_service.get_schema_path(catalog_id, schema_name)
        return schema_path / MODELS_DIR if schema_path else None
    
    def _get_model_path(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[Path]:
        """获取 Model 文件路径"""
        models_dir = self._get_models_dir(catalog_id, schema_name)
        if not models_dir:
            return None
        model_path = models_dir / f"{model_name}.yaml"
        return model_path if model_path.exists() else None
    
    def _load_model(self, catalog_id: str, schema_name: str, model_path: Path) -> Optional[Model]:
        """加载 Model"""
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path.stem)
        
        return Model(
            id=f"{catalog_id}_{schema_name}_model_{model_path.stem}",
            name=model_path.stem,
            display_name=baseinfo.get("display_name") or model_path.stem,
            description=baseinfo.get("description"),
            tags=baseinfo.get("tags", []),
            schema_id=f"{catalog_id}_{schema_name}",
            entity_type=EntityType.MODEL,
            path=str(model_path),
            created_at=self._parse_datetime(baseinfo.get("created_at")),
            updated_at=self._parse_datetime(baseinfo.get("updated_at")),
            model_type=config.get("model_type", "endpoint"),
            local_provider=config.get("local_provider"),
            local_source=config.get("local_source"),
            volume_reference=config.get("volume_reference"),
            huggingface_repo=config.get("huggingface_repo"),
            huggingface_filename=config.get("huggingface_filename"),
            endpoint_provider=config.get("endpoint_provider"),
            api_base_url=config.get("api_base_url"),
            api_key=config.get("api_key"),
            model_id=config.get("model_id"),
        )
    
    def list_models(self, catalog_id: str, schema_name: str) -> List[Model]:
        """获取 Model 列表"""
        logger.debug(f"获取 Model 列表: {catalog_id}/{schema_name}")
        models_dir = self._get_models_dir(catalog_id, schema_name)
        if not models_dir or not models_dir.exists():
            return []
        models = self._scan_yaml_files(models_dir, lambda p: self._load_model(catalog_id, schema_name, p))
        logger.debug(f"发现 {len(models)} 个 Model")
        return models
    
    def get_model(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[Model]:
        """获取 Model"""
        logger.debug(f"获取 Model: {catalog_id}/{schema_name}/{model_name}")
        model_path = self._get_model_path(catalog_id, schema_name, model_name)
        if not model_path:
            # 尝试不存在时创建路径
            models_dir = self._get_models_dir(catalog_id, schema_name)
            if not models_dir:
                logger.debug(f"Models 目录不存在: {catalog_id}/{schema_name}")
                return None
            model_path = models_dir / f"{model_name}.yaml"
            if not model_path.exists():
                logger.debug(f"Model 不存在: {model_name}")
                return None
        return self._load_model(catalog_id, schema_name, model_path)
    
    def get_model_config_content(self, catalog_id: str, schema_name: str, model_name: str) -> Optional[str]:
        """获取 Model 配置内容"""
        models_dir = self._get_models_dir(catalog_id, schema_name)
        if not models_dir:
            return None
        return self._read_file(models_dir / f"{model_name}.yaml")
    
    def create_model(self, catalog_id: str, schema_name: str, data: ModelCreate) -> Model:
        """创建 Model"""
        logger.info(f"创建 Model: {catalog_id}/{schema_name}/{data.name}, type={data.model_type}")
        schema_path = self.catalog_service.get_schema_path(catalog_id, schema_name)
        if not schema_path:
            logger.warning(f"Schema 不存在: {catalog_id}/{schema_name}")
            raise ValueError(f"Schema '{schema_name}' 不存在")
        
        models_dir = schema_path / MODELS_DIR
        models_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = models_dir / f"{data.name}.yaml"
        if model_path.exists():
            logger.warning(f"Model 已存在: {data.name}")
            raise ValueError(f"Model '{data.name}' 已存在")
        
        baseinfo = self._create_baseinfo(data.name, data.display_name, data.description, data.tags, data.owner or "admin")
        
        config = {
            "baseinfo": baseinfo,
            "model_type": data.model_type.value if hasattr(data.model_type, 'value') else data.model_type,
        }
        
        # 添加可选字段
        optional_fields = [
            ("local_provider", data.local_provider),
            ("local_source", data.local_source),
            ("volume_reference", data.volume_reference),
            ("huggingface_repo", data.huggingface_repo),
            ("huggingface_filename", data.huggingface_filename),
            ("endpoint_provider", data.endpoint_provider),
            ("api_base_url", data.api_base_url),
            ("api_key", data.api_key),
            ("model_id", data.model_id),
        ]
        
        for key, value in optional_fields:
            if value:
                config[key] = value.value if hasattr(value, 'value') else value
        
        self._save_yaml(model_path, config)
        logger.info(f"Model 创建成功: {data.name}")
        return self._load_model(catalog_id, schema_name, model_path)
    
    def update_model(self, catalog_id: str, schema_name: str, model_name: str, update: ModelUpdate) -> Optional[Model]:
        """更新 Model"""
        logger.info(f"更新 Model: {catalog_id}/{schema_name}/{model_name}")
        models_dir = self._get_models_dir(catalog_id, schema_name)
        if not models_dir:
            return None
        
        model_path = models_dir / f"{model_name}.yaml"
        if not model_path.exists():
            logger.warning(f"Model 不存在: {model_name}")
            return None
        
        config = self._load_yaml(model_path) or {}
        baseinfo = self._extract_baseinfo(config, model_path.stem)
        
        baseinfo = self._update_baseinfo(baseinfo, update.display_name, update.description, update.tags)
        config["baseinfo"] = baseinfo
        
        # 更新可选字段
        if update.api_key is not None:
            config["api_key"] = update.api_key
        if update.api_base_url is not None:
            config["api_base_url"] = update.api_base_url
        if update.model_id is not None:
            config["model_id"] = update.model_id
        
        self._save_yaml(model_path, config)
        logger.info(f"Model 更新成功: {model_name}")
        return self._load_model(catalog_id, schema_name, model_path)
    
    def delete_model(self, catalog_id: str, schema_name: str, model_name: str) -> bool:
        """删除 Model"""
        logger.info(f"删除 Model: {catalog_id}/{schema_name}/{model_name}")
        models_dir = self._get_models_dir(catalog_id, schema_name)
        if not models_dir:
            return False
        result = self._delete_file(models_dir / f"{model_name}.yaml")
        if result:
            logger.info(f"Model 删除成功: {model_name}")
        else:
            logger.warning(f"Model 不存在: {model_name}")
        return result
