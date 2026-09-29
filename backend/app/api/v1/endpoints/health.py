"""
Health check endpoints — system-wide service health.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.observability.logger import get_logger

router = APIRouter()
logger = get_logger("api.health")


@router.get("/detailed")
async def detailed_health():
    """Detailed health check — tests all connected services."""
    results = {}

    # Check PostgreSQL
    try:
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["postgres"] = {"status": "healthy"}
    except Exception as e:
        results["postgres"] = {"status": "unhealthy", "error": str(e)}

    # Check Redis
    try:
        from app.services.redis_service import redis_manager
        await redis_manager.client.ping()
        results["redis"] = {"status": "healthy"}
    except Exception as e:
        results["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check Ollama
    try:
        from app.llm.client import llm_client
        healthy = await llm_client.is_healthy()
        results["ollama"] = {"status": "healthy" if healthy else "unhealthy"}
    except Exception as e:
        results["ollama"] = {"status": "unhealthy", "error": str(e)}

    # Check MinIO
    try:
        from app.services.file_service import file_service
        from app.config import get_settings
        settings = get_settings()
        exists = file_service.client.bucket_exists(settings.minio_default_bucket)
        results["minio"] = {"status": "healthy" if exists else "degraded"}
    except Exception as e:
        results["minio"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(r["status"] == "healthy" for r in results.values())
    any_unhealthy = any(r["status"] == "unhealthy" for r in results.values())

    overall = "healthy" if all_healthy else ("unhealthy" if any_unhealthy else "degraded")

    return {
        "status": overall,
        "services": results,
    }
