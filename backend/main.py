"""
LocalBrisk Backend - FastAPI 主入口
本地化全能 AI 智能体工作站后端服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 首先初始化日志系统
from app.core.logging import setup_logging, get_logger
setup_logging()

from app.api import router as api_router
from app.core.config import settings
from app.core.middleware import I18nMiddleware
from app.core.i18n import t, SupportedLocale

logger = get_logger(__name__)

# 创建 FastAPI 应用实例
app = FastAPI(
    title="LocalBrisk Backend",
    description="本地化全能 AI 智能体工作站后端服务",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 配置 - 允许 Tauri 前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加国际化中间件
app.add_middleware(I18nMiddleware)

# 注册 API 路由
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    logger.debug("健康检查请求")
    return {"status": "ok", "message": "LocalBrisk Backend is running"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    logger.debug("健康检查请求")
    return {"status": "healthy", "message": t("health.healthy"), "version": "0.1.0"}


@app.get("/api/i18n/locales")
async def get_supported_locales():
    """获取支持的语言列表"""
    return {
        "locales": [
            {"code": "zh-CN", "name": "Simplified Chinese", "nativeName": "简体中文"},
            {"code": "en", "name": "English", "nativeName": "English"},
            {"code": "zh-TW", "name": "Traditional Chinese", "nativeName": "繁體中文"},
            {"code": "ja", "name": "Japanese", "nativeName": "日本語"},
        ],
        "default": "zh-CN"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"启动 LocalBrisk Backend, host={settings.HOST}, port={settings.PORT}, debug={settings.DEBUG}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
