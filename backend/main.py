"""
LocalBrisk Backend - FastAPI Main Entry
Local-first all-in-one AI agent workstation backend service.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging system first
from app.core.logging import setup_logging, get_logger
setup_logging()

from app.api import router as api_router
from app.core.config import settings
from app.core.middleware import I18nMiddleware
from app.core.i18n import t, SupportedLocale
from compute_engine import init_duckdb_service, close_duckdb_service

logger = get_logger(__name__)

# Create FastAPI application instance
app = FastAPI(
    title="LocalBrisk Backend",
    description="Local-first all-in-one AI agent workstation backend service",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS configuration - allow Tauri frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add i18n middleware
app.add_middleware(I18nMiddleware)

# Register API routes
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def _startup_init_compute_engine():
    """Initialize persistent DuckDB instance on service startup."""
    try:
        init_duckdb_service(settings.DUCKDB_PATH)
        logger.info(f"DuckDB initialized: {settings.DUCKDB_PATH}")
    except Exception as e:
        logger.exception(f"DuckDB initialization failed: {e}")
        raise


@app.on_event("shutdown")
async def _shutdown_close_compute_engine():
    """Release DuckDB connection on service shutdown."""
    close_duckdb_service()


@app.get("/")
async def root():
    """Root path - health check."""
    logger.debug("Health check request")
    return {"status": "ok", "message": "LocalBrisk Backend is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check request")
    return {"status": "healthy", "message": t("health.healthy"), "version": "0.1.0"}


@app.get("/api/i18n/locales")
async def get_supported_locales():
    """Get supported language list."""
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
    
    logger.info(f"Starting LocalBrisk Backend, host={settings.HOST}, port={settings.PORT}, debug={settings.DEBUG}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
