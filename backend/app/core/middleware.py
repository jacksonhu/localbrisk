"""
I18n middleware.
Automatically sets language based on request headers.
"""

from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.i18n import SupportedLocale, set_locale


class I18nMiddleware(BaseHTTPMiddleware):
    """
    Internationalization middleware.
    Detects language from Accept-Language or custom X-Language request header.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Prefer custom header for language
        language = request.headers.get("X-Language")
        
        # Fall back to Accept-Language if no custom header
        if not language:
            accept_language = request.headers.get("Accept-Language", "")
            language = self._parse_accept_language(accept_language)
        
        # Set locale
        locale = self._get_locale(language)
        set_locale(locale)
        
        # Store locale in request state
        request.state.locale = locale
        
        response = await call_next(request)
        
        # Return actual locale in response header
        response.headers["Content-Language"] = locale.value
        
        return response
    
    def _parse_accept_language(self, accept_language: str) -> str:
        """
        Parse Accept-Language header.
        
        Args:
            accept_language: Value of Accept-Language header
            
        Returns:
            Language code
        """
        if not accept_language:
            return ""
        
        # Simple parsing: take the first language
        # Format: zh-CN,zh;q=0.9,en;q=0.8
        languages = accept_language.split(",")
        if languages:
            # Strip quality weight
            first_lang = languages[0].split(";")[0].strip()
            return first_lang
        
        return ""
    
    def _get_locale(self, language: str) -> SupportedLocale:
        """
        Get supported locale enum from language code.
        
        Args:
            language: Language code
            
        Returns:
            SupportedLocale enum value
        """
        if not language:
            return SupportedLocale.ZH_CN
        
        # Normalize language code
        language = language.lower().replace("_", "-")
        
        # Match supported languages
        if language.startswith("zh"):
            if "tw" in language or "hk" in language or "hant" in language:
                return SupportedLocale.ZH_TW
            return SupportedLocale.ZH_CN
        elif language.startswith("ja"):
            return SupportedLocale.JA
        elif language.startswith("en"):
            return SupportedLocale.EN
        
        # Default to Chinese
        return SupportedLocale.ZH_CN
