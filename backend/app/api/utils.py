"""
API utility functions and decorators.
Provides unified error handling, response formatting, etc.
"""

from functools import wraps
from typing import Callable, Any, Optional
from fastapi import HTTPException


def handle_not_found(result: Any, message: str = "Resource not found"):
    """Handle resource not found cases."""
    if result is None:
        raise HTTPException(status_code=404, detail=message)
    return result


def handle_service_error(func: Callable):
    """Decorator: unified service layer exception handling."""
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
    """Generic CRUD route helper class."""
    
    @staticmethod
    def success_message(action: str, resource: str) -> dict:
        """Generate success message."""
        return {"message": f"{resource} {action} successfully"}
    
    @staticmethod
    def config_response(content: Optional[str], resource: str) -> dict:
        """Generate config response."""
        if content is None:
            raise HTTPException(status_code=404, detail=f"{resource} config not found")
        return {"content": content}
