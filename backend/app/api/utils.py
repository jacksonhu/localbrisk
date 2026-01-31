"""
API 通用工具函数和装饰器
提供统一的错误处理、响应格式化等功能
"""

from functools import wraps
from typing import Callable, Any, Optional
from fastapi import HTTPException


def handle_not_found(result: Any, message: str = "Resource not found"):
    """处理资源不存在的情况"""
    if result is None:
        raise HTTPException(status_code=404, detail=message)
    return result


def handle_service_error(func: Callable):
    """装饰器：统一处理服务层异常"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
    return wrapper


class CRUDRouter:
    """通用 CRUD 路由辅助类"""
    
    @staticmethod
    def success_message(action: str, resource: str) -> dict:
        """生成成功消息"""
        return {"message": f"{resource} {action} successfully"}
    
    @staticmethod
    def config_response(content: Optional[str], resource: str) -> dict:
        """生成配置响应"""
        if content is None:
            raise HTTPException(status_code=404, detail=f"{resource} config not found")
        return {"content": content}
