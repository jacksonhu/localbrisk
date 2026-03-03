"""
虚拟路径解析工具

将 CompositeBackend 管理的虚拟路径转换为真实的操作系统文件路径，
供自定义工具（如 OfficeReaderTool）直接使用。

CompositeBackend 的路由机制:
  虚拟路径 → _get_backend_and_key() → (backend, stripped_key)
  stripped_key → backend._resolve_path() → 真实的 OS 路径

示例:
  虚拟路径: /asset_bundles_myasset_volumes_localvolume/汇总.xlsx
  匹配路由: /asset_bundles_myasset_volumes_localvolume/
  stripped_key: /汇总.xlsx
  backend.root_dir: /Users/xxx/Downloads/analysis
  真实路径: /Users/xxx/Downloads/analysis/汇总.xlsx
"""

import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def resolve_virtual_path(composite_backend, virtual_path: str) -> str:
    """将 CompositeBackend 的虚拟路径解析为真实的文件系统路径。

    利用 CompositeBackend._get_backend_and_key() 做路由匹配，
    再通过 FilesystemBackend._resolve_path() 得到真实 OS 路径。

    Args:
        composite_backend: CompositeBackend（或 FilesystemBackend / LocalShellBackend）实例
        virtual_path: 虚拟路径，如 '/asset_bundles_myasset_volumes_localvolume/汇总.xlsx'

    Returns:
        真实的操作系统路径字符串

    Raises:
        ValueError: 路径遍历攻击（.. 等）被拒绝
        FileNotFoundError: 解析后的文件不存在
    """
    from deepagents.backends.filesystem import FilesystemBackend
    from deepagents.backends.composite import CompositeBackend as _CompositeBackend

    # 如果 backend 本身就是 FilesystemBackend（非组合模式），直接解析
    if isinstance(composite_backend, FilesystemBackend) and not isinstance(composite_backend, _CompositeBackend):
        resolved = composite_backend._resolve_path(virtual_path)
        return str(resolved)

    # CompositeBackend: 先路由匹配，再解析
    if isinstance(composite_backend, _CompositeBackend):
        backend, stripped_key = composite_backend._get_backend_and_key(virtual_path)

        if isinstance(backend, FilesystemBackend):
            resolved = backend._resolve_path(stripped_key)
            return str(resolved)

        # 其他类型的 backend（如远程存储），无法解析为本地路径
        logger.warning(
            f"Backend 类型 {type(backend).__name__} 不支持本地路径解析, "
            f"virtual_path={virtual_path}"
        )
        return virtual_path

    # 未知 backend 类型，返回原路径
    logger.warning(f"未知的 backend 类型: {type(composite_backend).__name__}")
    return virtual_path


def resolve_virtual_path_safe(composite_backend, virtual_path: str) -> Optional[str]:
    """安全版本的虚拟路径解析，出错时返回 None 而非抛异常。

    Args:
        composite_backend: CompositeBackend 实例
        virtual_path: 虚拟路径

    Returns:
        真实的文件系统路径，或 None（解析失败时）
    """
    try:
        return resolve_virtual_path(composite_backend, virtual_path)
    except Exception as e:
        logger.error(f"虚拟路径解析失败: {virtual_path}, error={e}")
        return None


def list_backend_routes(composite_backend) -> dict[str, str]:
    """列出 CompositeBackend 的所有路由及其真实根目录。

    用于调试和日志记录。

    Args:
        composite_backend: CompositeBackend 实例

    Returns:
        {虚拟前缀: 真实根目录} 的字典
    """
    from deepagents.backends.filesystem import FilesystemBackend
    from deepagents.backends.composite import CompositeBackend as _CompositeBackend

    result = {}

    if not isinstance(composite_backend, _CompositeBackend):
        if isinstance(composite_backend, FilesystemBackend):
            result["/"] = str(composite_backend.cwd)
        return result

    for prefix, backend in composite_backend.sorted_routes:
        if isinstance(backend, FilesystemBackend):
            result[prefix] = str(backend.cwd)
        else:
            result[prefix] = f"<{type(backend).__name__}>"

    # default backend
    default = composite_backend.default
    if isinstance(default, FilesystemBackend):
        result["(default)"] = str(default.cwd)

    return result
