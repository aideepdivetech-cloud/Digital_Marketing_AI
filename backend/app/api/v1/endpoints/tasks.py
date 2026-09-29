"""
Task endpoints — create, list, get status, cancel.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import Task
from app.db.session import get_db
from app.core.exceptions import TaskNotFoundError
from app.observability.logger import get_logger

router = APIRouter()
logger = get_logger("api.tasks")


# ── Schemas ──

class TaskResponse(BaseModel):
    id: str
    title: str | None
    status: str
    priority: str
    progress_percentage: int
    current_step: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


# ── Endpoints ──

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List tasks for the current user."""
    # TODO: Filter by tenant_id and user_id from JWT
    query = select(Task).order_by(Task.created_at.desc())

    if status:
        query = query.where(Task.status == status)

    # Count total
    count_query = select(func.count()).select_from(Task)
    if status:
        count_query = count_query.where(Task.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(
        tasks=[
            TaskResponse(
                id=str(t.id),
                title=t.title,
                status=t.status,
                priority=t.priority,
                progress_percentage=t.progress_percentage or 0,
                current_step=t.current_step,
                created_at=str(t.created_at),
                started_at=str(t.started_at) if t.started_at else None,
                completed_at=str(t.completed_at) if t.completed_at else None,
            )
            for t in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific task by ID."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise TaskNotFoundError(task_id=task_id)

    return TaskResponse(
        id=str(task.id),
        title=task.title,
        status=task.status,
        priority=task.priority,
        progress_percentage=task.progress_percentage or 0,
        current_step=task.current_step,
        created_at=str(task.created_at),
        started_at=str(task.started_at) if task.started_at else None,
        completed_at=str(task.completed_at) if task.completed_at else None,
    )
