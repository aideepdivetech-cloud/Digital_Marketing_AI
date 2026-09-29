"""
Celery application configuration.
Used for scheduled tasks and heavy background processing.
Agent execution uses AsyncIO (not Celery) for I/O-bound work.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "digital_marketing_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_concurrency=settings.celery_worker_concurrency,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    worker_prefetch_multiplier=1,     # Process one task at a time per worker

    # Task settings
    task_soft_time_limit=settings.celery_task_soft_time_limit,
    task_time_limit=settings.celery_task_time_limit,
    task_acks_late=True,              # Acknowledge after completion (not before)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies

    # Queues
    task_default_queue="default",
    task_routes={
        "workers.scheduled_worker.*": {"queue": "scheduled"},
        "workers.heavy_worker.*": {"queue": "heavy"},
    },

    # Beat schedule (cron jobs)
    beat_schedule={
        "health-check-every-5-min": {
            "task": "workers.scheduled_worker.run_health_check",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-expired-sessions-hourly": {
            "task": "workers.scheduled_worker.cleanup_expired_sessions",
            "schedule": 3600.0,  # Every hour
        },
        "usage-aggregation-daily": {
            "task": "workers.scheduled_worker.aggregate_daily_usage",
            "schedule": 86400.0,  # Every 24 hours
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["workers"])
