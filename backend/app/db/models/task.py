"""
Task models — Persistent queue, dependencies, steps, dead letter queue 
(Gaps C1, C2, C3, C12, H10, H12, H17).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, SmallInteger, Boolean, DateTime, Text,
    ForeignKey, Index, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Task(Base, UUIDMixin, TimestampMixin):
    """Main task tracking — persistent queue entry + execution state."""
    __tablename__ = "tasks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"))
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))

    # Task info
    title = Column(String(500))
    description = Column(Text)

    # Agent assignment
    assigned_boss_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    assigned_master_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    assigned_sub_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    # Status & priority
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(10), nullable=False, default="normal")  # critical, high, normal, low

    # Data
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    error_message = Column(Text)
    error_details = Column(JSONB)
    error_stack = Column(Text)

    # Progress
    progress_percentage = Column(SmallInteger, default=0)
    current_step = Column(String(500))
    steps_total = Column(Integer, default=0)
    steps_completed = Column(Integer, default=0)

    # Timing
    queued_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

    # Retry (Gap C3)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_retry_at = Column(DateTime(timezone=True))
    next_retry_at = Column(DateTime(timezone=True))

    # Concurrency lock key
    master_agent_lock_key = Column(String(200))

    # Approval (Gap H12) — ALWAYS ASK model
    requires_approval = Column(Boolean, default=False)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id", ondelete="SET NULL"))

    # Recovery (Gap H10)
    resumed_from_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    interrupted_at = Column(DateTime(timezone=True))

    # Observability (Gap H17)
    correlation_id = Column(UUID(as_uuid=True))

    # Metadata
    metadata_ = Column("metadata", JSONB, default=dict)

    # Relationships
    user = relationship("User", back_populates="tasks", foreign_keys=[user_id])
    conversation = relationship("Conversation", back_populates="tasks")
    campaign = relationship("Campaign", back_populates="tasks")
    parent_task = relationship("Task", remote_side="Task.id", foreign_keys=[parent_task_id])
    steps = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "TaskDependency",
        back_populates="task",
        foreign_keys="TaskDependency.task_id",
        cascade="all, delete-orphan",
    )
    queue_entry = relationship("TaskQueue", back_populates="task", uselist=False)
    artifacts = relationship("Artifact", back_populates="task")
    approval = relationship("Approval", foreign_keys=[approval_id])
    tool_executions = relationship("ToolExecution", back_populates="task")

    __table_args__ = (
        CheckConstraint("progress_percentage >= 0 AND progress_percentage <= 100", name="check_progress_range"),
        Index("idx_tasks_tenant", "tenant_id"),
        Index("idx_tasks_user", "user_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_priority_queued", "priority", "queued_at"),
        Index("idx_tasks_master_agent", "assigned_master_agent_id"),
        Index("idx_tasks_correlation", "correlation_id"),
        Index("idx_tasks_campaign", "campaign_id"),
        Index("idx_tasks_parent", "parent_task_id"),
    )


class TaskDependency(Base, UUIDMixin):
    """Task dependency DAG (Gap C2)."""
    __tablename__ = "task_dependencies"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(20), default="blocking")  # blocking, optional, data_pass
    data_mapping = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    task = relationship("Task", back_populates="dependencies", foreign_keys=[task_id])
    depends_on = relationship("Task", foreign_keys=[depends_on_task_id])

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="unique_task_dependency"),
    )


class TaskStep(Base, UUIDMixin):
    """Granular progress steps within a task (Gap H7)."""
    __tablename__ = "task_steps"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    status = Column(String(20), nullable=False, default="pending")
    input_data = Column(JSONB, default=dict)
    output_data = Column(JSONB, default=dict)
    error_message = Column(Text)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    task = relationship("Task", back_populates="steps")

    __table_args__ = (
        Index("idx_task_steps_task", "task_id", "step_number"),
    )


class TaskQueue(Base, UUIDMixin):
    """Persistent queue entries (Gap C1) — PostgreSQL-backed, not in-memory."""
    __tablename__ = "task_queue"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    target_master_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    priority = Column(String(10), nullable=False, default="normal")

    position = Column(Integer)  # Queue position

    enqueued_at = Column(DateTime(timezone=True), server_default="NOW()")
    scheduled_for = Column(DateTime(timezone=True))  # Delayed execution

    is_processing = Column(Boolean, default=False)
    processing_started_at = Column(DateTime(timezone=True))
    processing_node = Column(String(255))  # Which worker picked it up

    task = relationship("Task", back_populates="queue_entry")

    __table_args__ = (
        Index(
            "idx_task_queue_next",
            "target_master_agent_id", "priority", "position",
        ),
    )


class DeadLetterQueue(Base, UUIDMixin):
    """Permanently failed tasks (Gap C3)."""
    __tablename__ = "dead_letter_queue"

    original_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    failure_reason = Column(Text, nullable=False)
    error_details = Column(JSONB)
    retry_count = Column(Integer)

    original_input = Column(JSONB)
    partial_output = Column(JSONB)

    can_manual_retry = Column(Boolean, default=True)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at = Column(DateTime(timezone=True))

    moved_at = Column(DateTime(timezone=True), server_default="NOW()")
