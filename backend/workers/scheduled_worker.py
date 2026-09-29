"""
Scheduled Celery tasks — health checks, cleanup, usage aggregation.
"""

from __future__ import annotations

from workers.celery_app import celery_app


@celery_app.task(name="workers.scheduled_worker.run_health_check")
def run_health_check():
    """Periodic health check for all services."""
    import asyncio
    asyncio.run(_async_health_check())


async def _async_health_check():
    """Async health check implementation."""
    from app.observability.logger import get_logger
    logger = get_logger("worker.health")

    checks = {}

    # Check Ollama
    try:
        from app.llm.client import llm_client
        checks["ollama"] = await llm_client.is_healthy()
    except Exception:
        checks["ollama"] = False

    logger.info("health_check_completed", results=checks)
    return checks


@celery_app.task(name="workers.scheduled_worker.cleanup_expired_sessions")
def cleanup_expired_sessions():
    """Clean up expired sessions and stale locks."""
    import asyncio
    asyncio.run(_async_cleanup())


async def _async_cleanup():
    """Async cleanup implementation."""
    from datetime import datetime, timezone
    from sqlalchemy import update, delete
    from app.db.session import get_db_context
    from app.db.models.conversation import Session
    from app.db.models.monitoring import AgentLock
    from app.observability.logger import get_logger

    logger = get_logger("worker.cleanup")
    now = datetime.now(timezone.utc)

    async with get_db_context() as db:
        # Expire old sessions
        result = await db.execute(
            update(Session)
            .where(Session.expires_at < now, Session.status == "active")
            .values(status="expired", ended_at=now)
        )
        expired_sessions = result.rowcount

        # Release stale locks
        result = await db.execute(
            delete(AgentLock)
            .where(AgentLock.expires_at < now, AgentLock.is_active == True)
        )
        stale_locks = result.rowcount

    logger.info(
        "cleanup_completed",
        expired_sessions=expired_sessions,
        stale_locks=stale_locks,
    )


@celery_app.task(name="workers.scheduled_worker.aggregate_daily_usage")
def aggregate_daily_usage():
    """Aggregate daily LLM usage statistics."""
    import asyncio
    asyncio.run(_async_aggregate_usage())


async def _async_aggregate_usage():
    """Async usage aggregation."""
    from app.observability.logger import get_logger
    logger = get_logger("worker.usage")
    # TODO: Implement daily aggregation from llm_usage_log → usage_tracking
    logger.info("daily_usage_aggregation_placeholder")
