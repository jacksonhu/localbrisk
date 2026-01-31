"""
基础服务类
提供文件操作、YAML处理、baseinfo处理等公共功能
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, TypeVar, Generic, Callable

import yaml

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseService:
    """基础服务类，提供公共文件操作方法"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or settings.CATALOGS_DIR
        self._ensure_dir(self.base_dir)
    
    # ==================== 目录操作 ====================
    
    def _ensure_dir(self, path: Path) -> None:
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)
    
    def _remove_dir(self, path: Path) -> bool:
        """删除目录"""
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True
    
    # ==================== 文件操作 ====================
    
    def _load_yaml(self, path: Path) -> Optional[Dict[str, Any]]:
        """加载 YAML 文件"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载 YAML 失败 {path}: {e}")
            return None
    
    def _save_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """保存 YAML 文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    
    def _read_file(self, path: Path) -> Optional[str]:
        """读取文件内容"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {path}: {e}")
            return None
    
    def _write_file(self, path: Path, content: str) -> None:
        """写入文件内容"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _delete_file(self, path: Path) -> bool:
        """删除文件"""
        if not path.exists():
            return False
        path.unlink()
        return True
    
    # ==================== BaseInfo 操作 ====================
    
    @staticmethod
    def _now_iso() -> str:
        """获取当前 ISO 时间字符串"""
        return datetime.now().isoformat()
    
    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """解析日期时间"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return None
    
    def _create_baseinfo(
        self,
        name: str,
        display_name: str = None,
        description: str = None,
        tags: List[str] = None,
        owner: str = "admin"
    ) -> Dict[str, Any]:
        """创建标准 baseinfo 字典"""
        now = self._now_iso()
        return {
            "name": name,
            "display_name": display_name or name,
            "description": description or "",
            "tags": tags or [],
            "owner": owner,
            "created_at": now,
            "updated_at": now,
        }
    
    def _extract_baseinfo(self, config: Dict[str, Any], fallback_name: str = "") -> Dict[str, Any]:
        """从配置中提取 baseinfo，兼容新旧格式"""
        baseinfo = config.get("baseinfo", {})
        if not baseinfo:
            baseinfo = {
                "name": config.get("name") or config.get("catalog_id") or fallback_name,
                "display_name": config.get("display_name") or config.get("name") or fallback_name,
                "description": config.get("description") or config.get("comment") or "",
                "tags": config.get("tags", []),
                "owner": config.get("owner", "admin"),
                "created_at": config.get("created_at"),
                "updated_at": config.get("updated_at"),
            }
        return baseinfo
    
    def _update_baseinfo(
        self,
        baseinfo: Dict[str, Any],
        display_name: str = None,
        description: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """更新 baseinfo 字段"""
        if display_name is not None:
            baseinfo["display_name"] = display_name
        if description is not None:
            baseinfo["description"] = description
        if tags is not None:
            baseinfo["tags"] = tags
        baseinfo["updated_at"] = self._now_iso()
        return baseinfo
    
    # ==================== 扫描操作 ====================
    
    def _scan_dir(
        self,
        directory: Path,
        filter_fn: Callable[[Path], bool] = None,
        loader_fn: Callable[[Path], Optional[T]] = None
    ) -> List[T]:
        """
        扫描目录并加载实体
        
        Args:
            directory: 目录路径
            filter_fn: 过滤函数，返回 True 表示保留
            loader_fn: 加载函数，将路径转换为实体
        """
        if not directory.exists():
            return []
        
        results = []
        for item in directory.iterdir():
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            if filter_fn and not filter_fn(item):
                continue
            if loader_fn:
                entity = loader_fn(item)
                if entity:
                    results.append(entity)
        return results
    
    def _scan_yaml_files(
        self,
        directory: Path,
        loader_fn: Callable[[Path], Optional[T]] = None
    ) -> List[T]:
        """扫描目录下的 YAML 文件"""
        return self._scan_dir(
            directory,
            filter_fn=lambda p: p.is_file() and p.suffix == ".yaml",
            loader_fn=loader_fn
        )
    
    def _scan_subdirs(
        self,
        directory: Path,
        loader_fn: Callable[[Path], Optional[T]] = None
    ) -> List[T]:
        """扫描子目录"""
        return self._scan_dir(
            directory,
            filter_fn=lambda p: p.is_dir(),
            loader_fn=loader_fn
        )
