"""
Base service class.
Provides common file operations, YAML handling, and baseinfo processing.
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
    """Base service class providing common file operation methods."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or settings.CATALOGS_DIR
        self._ensure_dir(self.base_dir)
    
    # ==================== Directory Operations ====================
    
    def _ensure_dir(self, path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
    
    def _remove_dir(self, path: Path) -> bool:
        """Remove directory."""
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True
    
    # ==================== File Operations ====================
    
    def _load_yaml(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load YAML file."""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML {path}: {e}")
            return None
    
    def _save_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """Save YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    
    def _read_file(self, path: Path) -> Optional[str]:
        """Read file content."""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None
    
    def _write_file(self, path: Path, content: str) -> None:
        """Write file content."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    
    def _delete_file(self, path: Path) -> bool:
        """Delete file."""
        if not path.exists():
            return False
        path.unlink()
        return True
    
    # ==================== BaseInfo Operations ====================
    
    @staticmethod
    def _now_iso() -> str:
        """Get current ISO time string."""
        return datetime.now().isoformat()
    
    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """Parse datetime value."""
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
        """Create standard baseinfo dictionary."""
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
        """Extract baseinfo from config, compatible with old and new formats."""
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
        """Update baseinfo fields."""
        if display_name is not None:
            baseinfo["display_name"] = display_name
        if description is not None:
            baseinfo["description"] = description
        if tags is not None:
            baseinfo["tags"] = tags
        baseinfo["updated_at"] = self._now_iso()
        return baseinfo
    
    # ==================== Scan Operations ====================
    
    def _scan_dir(
        self,
        directory: Path,
        filter_fn: Callable[[Path], bool] = None,
        loader_fn: Callable[[Path], Optional[T]] = None
    ) -> List[T]:
        """
        Scan directory and load entities.
        
        Args:
            directory: Directory path
            filter_fn: Filter function, returns True to keep
            loader_fn: Loader function, converts path to entity
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
        """Scan YAML files in directory."""
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
        """Scan subdirectories."""
        return self._scan_dir(
            directory,
            filter_fn=lambda p: p.is_dir(),
            loader_fn=loader_fn
        )
