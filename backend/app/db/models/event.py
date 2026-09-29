"""
Event Bus models — Inter-agent communication (Gaps C10, H23).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin


class Event(Base, UUIDMixin):
    """Persisted events from the event bus for auditing and replay."""
    __tablename__ = "events"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    event_type = Column(String(100), nullable=False)
    source_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))

    payload = Column(JSONB, nullable=False, default=dict)

    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    subscriber_count = Column(Integer, default=0)

    correlation_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    processing_logs = relationship("EventProcessingLog", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_events_type_unprocessed", "event_type", "created_at"),
        Index("idx_events_campaign", "campaign_id"),
        Index("idx_events_correlation", "correlation_id"),
    )


class EventSubscription(Base, UUIDMixin):
    """Which agents subscribe to which event types."""
    __tablename__ = "event_subscriptions"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)

    filter_conditions = Column(JSONB, default=dict)
    handler_config = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        UniqueConstraint("agent_id", "event_type", name="unique_agent_event_subscription"),
    )


class EventProcessingLog(Base, UUIDMixin):
    """Track processing of events by each subscriber."""
    __tablename__ = "event_processing_log"

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    subscriber_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)

    status = Column(String(20), nullable=False, default="pending")
    triggered_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"))
    error_message = Column(Text)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    event = relationship("Event", back_populates="processing_logs")
