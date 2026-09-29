"""
FastAPI Application Entry Point — Digital Marketing AI Platform.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppException
from app.observability.logger import get_logger, setup_logging

settings = get_settings()
logger = get_logger("app.main")


# ── Lifespan (startup/shutdown) ──

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    # ── Startup ──
    setup_logging()
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )

    # Initialize Redis connection pool
    from app.services.redis_service import redis_manager
    await redis_manager.connect()
    logger.info("redis_connected")

    # Initialize MinIO buckets
    from app.services.file_service import file_service
    await file_service.ensure_buckets()
    logger.info("minio_initialized")

    logger.info("application_started")

    yield

    # ── Shutdown ──
    logger.info("application_shutting_down")

    # Close Redis
    await redis_manager.disconnect()
    logger.info("redis_disconnected")

    # Close DB engine
    from app.db.session import engine
    await engine.dispose()
    logger.info("database_disconnected")

    logger.info("application_stopped")


# ── Create FastAPI App ──

app = FastAPI(
    title="Digital Marketing AI Platform",
    description="AI-powered digital marketing agent platform with 12 Master Agents and 400+ Sub-Agents",
    version=settings.app_version,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)


# ── CORS Middleware ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ──

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom application exceptions."""
    logger.warning(
        "app_exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — logs full stack trace."""
    logger.exception(
        "unhandled_exception",
        error=str(exc),
        path=str(request.url),
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        },
    )


# ── API Routes ──

from app.api.v1.router import api_v1_router  # noqa: E402

app.include_router(api_v1_router, prefix="/api/v1")


# ── Health Check (root) ──

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.is_development else None,
    }
