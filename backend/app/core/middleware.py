"""
国际化中间件
根据请求头自动设置语言
"""

from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.i18n import SupportedLocale, set_locale


class I18nMiddleware(BaseHTTPMiddleware):
    """
    国际化中间件
    从请求头 Accept-Language 或自定义头 X-Language 中获取语言设置
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 优先从自定义头获取语言
        language = request.headers.get("X-Language")
        
        # 如果没有自定义头，从 Accept-Language 获取
        if not language:
            accept_language = request.headers.get("Accept-Language", "")
            language = self._parse_accept_language(accept_language)
        
        # 设置语言
        locale = self._get_locale(language)
        set_locale(locale)
        
        # 将语言信息存储到请求状态中
        request.state.locale = locale
        
        response = await call_next(request)
        
        # 在响应头中返回实际使用的语言
        response.headers["Content-Language"] = locale.value
        
        return response
    
    def _parse_accept_language(self, accept_language: str) -> str:
        """
        解析 Accept-Language 头
        
        Args:
            accept_language: Accept-Language 头的值
            
        Returns:
            语言代码
        """
        if not accept_language:
            return ""
        
        # 简单解析，取第一个语言
        # 格式: zh-CN,zh;q=0.9,en;q=0.8
        languages = accept_language.split(",")
        if languages:
            # 去掉权重部分
            first_lang = languages[0].split(";")[0].strip()
            return first_lang
        
        return ""
    
    def _get_locale(self, language: str) -> SupportedLocale:
        """
        根据语言代码获取支持的语言枚举
        
        Args:
            language: 语言代码
            
        Returns:
            SupportedLocale 枚举值
        """
        if not language:
            return SupportedLocale.ZH_CN
        
        # 标准化语言代码
        language = language.lower().replace("_", "-")
        
        # 匹配支持的语言
        if language.startswith("zh"):
            if "tw" in language or "hk" in language or "hant" in language:
                return SupportedLocale.ZH_TW
            return SupportedLocale.ZH_CN
        elif language.startswith("ja"):
            return SupportedLocale.JA
        elif language.startswith("en"):
            return SupportedLocale.EN
        
        # 默认返回中文
        return SupportedLocale.ZH_CN
