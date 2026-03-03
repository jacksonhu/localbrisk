"""
国际化 (i18n) 模块
支持多语言的后端服务
"""

from typing import Dict, Optional
from enum import Enum


class SupportedLocale(str, Enum):
    """支持的语言"""
    ZH_CN = "zh-CN"
    EN = "en"
    ZH_TW = "zh-TW"
    JA = "ja"


# 语言包
TRANSLATIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "zh-CN": {
        "common": {
            "success": "成功",
            "error": "错误",
            "not_found": "未找到",
            "unauthorized": "未授权",
            "forbidden": "禁止访问",
            "bad_request": "请求无效",
            "internal_error": "服务器内部错误",
        },
        "health": {
            "healthy": "服务健康",
            "unhealthy": "服务不健康",
        },
        "catalog": {
            "created": "Catalog 创建成功",
            "updated": "Catalog 更新成功",
            "deleted": "Catalog 删除成功",
            "not_found": "Catalog 不存在",
            "already_exists": "Catalog 已存在",
        },
        "schema": {
            "created": "Schema 创建成功",
            "updated": "Schema 更新成功",
            "deleted": "Schema 删除成功",
            "not_found": "Schema 不存在",
            "already_exists": "Schema 已存在",
        },
        "table": {
            "created": "Table 创建成功",
            "updated": "Table 更新成功",
            "deleted": "Table 删除成功",
            "not_found": "Table 不存在",
            "already_exists": "Table 已存在",
        },
        "model": {
            "connection_failed": "模型连接失败",
            "inference_error": "模型推理错误",
            "not_loaded": "模型未加载",
        },
    },
    "en": {
        "common": {
            "success": "Success",
            "error": "Error",
            "not_found": "Not found",
            "unauthorized": "Unauthorized",
            "forbidden": "Forbidden",
            "bad_request": "Bad request",
            "internal_error": "Internal server error",
        },
        "health": {
            "healthy": "Service is healthy",
            "unhealthy": "Service is unhealthy",
        },
        "catalog": {
            "created": "Catalog created successfully",
            "updated": "Catalog updated successfully",
            "deleted": "Catalog deleted successfully",
            "not_found": "Catalog not found",
            "already_exists": "Catalog already exists",
        },
        "schema": {
            "created": "Schema created successfully",
            "updated": "Schema updated successfully",
            "deleted": "Schema deleted successfully",
            "not_found": "Schema not found",
            "already_exists": "Schema already exists",
        },
        "table": {
            "created": "Table created successfully",
            "updated": "Table updated successfully",
            "deleted": "Table deleted successfully",
            "not_found": "Table not found",
            "already_exists": "Table already exists",
        },
        "model": {
            "connection_failed": "Model connection failed",
            "inference_error": "Model inference error",
            "not_loaded": "Model not loaded",
        },
    },
}

# 默认语言
DEFAULT_LOCALE = SupportedLocale.ZH_CN


class I18n:
    """国际化工具类"""
    
    def __init__(self, locale: SupportedLocale = DEFAULT_LOCALE):
        self._locale = locale
    
    @property
    def locale(self) -> SupportedLocale:
        return self._locale
    
    @locale.setter
    def locale(self, value: SupportedLocale):
        if value in SupportedLocale:
            self._locale = value
    
    def t(self, key: str, locale: Optional[SupportedLocale] = None) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键，格式为 "category.key"，如 "common.success"
            locale: 可选，指定语言，不传则使用实例语言
            
        Returns:
            翻译后的文本，如果未找到则返回原始键
        """
        target_locale = locale or self._locale
        
        # 尝试获取翻译
        translations = TRANSLATIONS.get(target_locale.value, {})
        
        # 如果目标语言没有找到，回退到英语
        if not translations:
            translations = TRANSLATIONS.get(SupportedLocale.EN.value, {})
        
        # 解析键
        parts = key.split(".")
        if len(parts) != 2:
            return key
        
        category, message_key = parts
        
        category_translations = translations.get(category, {})
        return category_translations.get(message_key, key)
    
    def get_all_translations(self) -> Dict[str, Dict[str, str]]:
        """获取当前语言的所有翻译"""
        return TRANSLATIONS.get(self._locale.value, TRANSLATIONS.get(SupportedLocale.EN.value, {}))


# 全局 i18n 实例
_i18n_instance: Optional[I18n] = None


def get_i18n(locale: Optional[SupportedLocale] = None) -> I18n:
    """
    获取国际化实例
    
    Args:
        locale: 可选，指定语言
        
    Returns:
        I18n 实例
    """
    global _i18n_instance
    
    if _i18n_instance is None:
        _i18n_instance = I18n(locale or DEFAULT_LOCALE)
    elif locale:
        _i18n_instance.locale = locale
    
    return _i18n_instance


def t(key: str, locale: Optional[SupportedLocale] = None) -> str:
    """
    便捷函数：获取翻译文本
    
    Args:
        key: 翻译键
        locale: 可选，指定语言
        
    Returns:
        翻译后的文本
    """
    return get_i18n().t(key, locale)


def set_locale(locale: SupportedLocale) -> None:
    """
    设置全局语言
    
    Args:
        locale: 目标语言
    """
    get_i18n(locale)
