"""
Monitoring, usage tracking, and operations models 
(Gaps C7, C14, H11, H17, H20, H21, N3, N12).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index,
    UniqueConstraint, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


# ── Agent Memory (Gap H2) ──

class AgentMemory(Base, UUIDMixin, TimestampMixin):
    """Persistent agent memory — key-value store per agent per user."""
    __tablename__ = "agent_memory"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    memory_key = Column(String(255), nullable=False)
    memory_value = Column(JSONB, nullable=False)
    memory_type = Column(String(20), default="short_term")  # short_term, long_term, episodic

    content_text = Column(Text)  # For embedding generation

    # TTL
    expires_at = Column(DateTime(timezone=True))

    # Access tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True))

    agent = relationship("Agent", back_populates="memories")

    __table_args__ = (
        UniqueConstraint("agent_id", "user_id", "memory_key", name="unique_agent_memory"),
        Index("idx_agent_memory_lookup", "agent_id", "user_id", "memory_key"),
    )


# ── Usage Tracking (Gaps C14, H11) ──

class UsageTracking(Base, UUIDMixin):
    """Rate limiting and quota tracking per tenant/user."""
    __tablename__ = "usage_tracking"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    resource_type = Column(String(50), nullable=False)  # llm_tokens, llm_calls, tool_calls, api_calls, etc.
    quantity = Column(Numeric(15, 4), nullable=False, default=0)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        Index("idx_usage_tracking_lookup", "tenant_id", "user_id", "resource_type", "period_start"),
    )


class LLMUsageLog(Base, UUIDMixin):
    """LLM inference call log (Gap H11)."""
    __tablename__ = "llm_usage_log"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))

    model_id = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)

    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)

    inference_time_ms = Column(Integer)
    tokens_per_second = Column(Numeric(10, 2))

    prompt_hash = Column(String(64))
    was_cached = Column(Boolean, default=False)
    was_fallback = Column(Boolean, default=False)

    cost_usd = Column(Numeric(10, 6), default=0)
    correlation_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        Index("idx_llm_usage_tenant_time", "tenant_id", "created_at"),
        Index("idx_llm_usage_task", "task_id"),
    )


# ── System Health (Gap C7) ──

class SystemHealth(Base, UUIDMixin):
    """Health check results per component."""
    __tablename__ = "system_health"

    component = Column(String(100), nullable=False)  # llm_server, database, redis, worker_1
    status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy, unknown
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    metadata_ = Column("metadata", JSONB, default=dict)

    checked_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        Index("idx_health_component_time", "component", "checked_at"),
    )


class AgentHeartbeat(Base, UUIDMixin):
    """Worker heartbeat tracking (Gap C7)."""
    __tablename__ = "agent_heartbeats"

    worker_id = Column(String(255), unique=True, nullable=False)
    hostname = Column(String(255))

    status = Column(String(20), nullable=False)  # healthy, degraded, unhealthy, unknown
    active_tasks = Column(Integer, default=0)
    metrics = Column(JSONB, default=dict)

    last_heartbeat_at = Column(DateTime(timezone=True), server_default="NOW()")
    started_at = Column(DateTime(timezone=True), server_default="NOW()")


# ── Webhooks (Gap H21) ──

class Webhook(Base, UUIDMixin):
    """Inbound webhook registrations for external services."""
    __tablename__ = "webhooks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    source = Column(String(100), nullable=False)  # shopify, stripe, hubspot
    endpoint_slug = Column(String(255), unique=True, nullable=False)

    secret = Column(String(255))
    signature_header = Column(String(100))

    is_active = Column(Boolean, default=True)
    event_mapping = Column(JSONB, default=dict)
    triggered_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    total_received = Column(Integer, default=0)
    last_received_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")


class WebhookEvent(Base, UUIDMixin):
    """Received webhook payloads."""
    __tablename__ = "webhook_events"

    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)

    event_type = Column(String(255))
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB)

    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    received_at = Column(DateTime(timezone=True), server_default="NOW()")


# ── Scheduled Tasks (Gap H20) ──

class ScheduledTask(Base, UUIDMixin, TimestampMixin):
    """Recurring tasks via Celery Beat (Gap H20)."""
    __tablename__ = "scheduled_tasks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    name = Column(String(500), nullable=False)
    description = Column(Text)

    cron_expression = Column(String(100))
    timezone = Column(String(50), default="UTC")

    target_master_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    task_template = Column(JSONB, nullable=False)

    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    run_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_scheduled_next", "next_run_at"),
    )


# ── Feedback (Gap N3) ──

class Feedback(Base, UUIDMixin):
    """User feedback on agent outputs."""
    __tablename__ = "feedback"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    entity_type = Column(String(100), nullable=False)  # task_output, artifact, message
    entity_id = Column(UUID(as_uuid=True), nullable=False)

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))

    rating = Column(String(20), nullable=False)  # excellent, good, neutral, poor, unusable
    numeric_score = Column(Numeric(3, 2))
    comments = Column(Text)
    tags = Column(JSONB, default=list)

    used_for_improvement = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        Index("idx_feedback_agent", "agent_id"),
        Index("idx_feedback_entity", "entity_type", "entity_id"),
    )


# ── Audit Log (Gap H17) ──

class AuditLog(Base, UUIDMixin):
    """Full audit trail for all system changes."""
    __tablename__ = "audit_log"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))

    action = Column(String(200), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(UUID(as_uuid=True))

    changes = Column(JSONB)  # Before/after
    details = Column(JSONB, default=dict)

    ip_address = Column(String(45))
    user_agent = Column(Text)
    correlation_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    __table_args__ = (
        Index("idx_audit_tenant_time", "tenant_id", "created_at"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )


# ── Feature Flags (Gap N12) ──

class FeatureFlag(Base, UUIDMixin, TimestampMixin):
    """Feature toggles for gradual rollout."""
    __tablename__ = "feature_flags"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))  # NULL = global

    flag_key = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, default=False)

    enabled_for_percent = Column(Integer, default=0)
    enabled_for_users = Column(JSONB, default=list)
    disabled_for_users = Column(JSONB, default=list)

    description = Column(Text)
    metadata_ = Column("metadata", JSONB, default=dict)

    __table_args__ = (
        UniqueConstraint("tenant_id", "flag_key", name="unique_feature_flag"),
    )


# ── System Config ──

class SystemConfig(Base):
    """Dynamic system configuration (key-value)."""
    __tablename__ = "system_config"

    key = Column(String(255), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at = Column(DateTime(timezone=True), server_default="NOW()")


# ── Agent Locks (Concurrency) ──

class AgentLock(Base, UUIDMixin):
    """Per-master concurrency locks for task processing."""
    __tablename__ = "agent_locks"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    master_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    lock_key = Column(String(200), unique=True, nullable=False)  # Format: tenant:user:master

    acquired_at = Column(DateTime(timezone=True), server_default="NOW()")
    expires_at = Column(DateTime(timezone=True))
    released_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("idx_agent_locks_active", "lock_key"),
    )


# ── Moderation Log (Gap C16) ──

class ModerationLog(Base, UUIDMixin):
    """Content safety filter results."""
    __tablename__ = "moderation_log"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))

    content_type = Column(String(100))  # input, output
    content_hash = Column(String(64))
    content_preview = Column(Text)

    is_flagged = Column(Boolean, default=False)
    flags = Column(JSONB, default=list)  # ['toxic', 'bias', 'pii', 'unsafe']
    confidence_scores = Column(JSONB, default=dict)

    action_taken = Column(String(100))  # blocked, sanitized, flagged, allowed

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")


# ── Customer Profiles (Gap C9 — CDP) ──

class CustomerProfile(Base, UUIDMixin, TimestampMixin):
    """Unified customer profiles for CDP Master Agent."""
    __tablename__ = "customer_profiles"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    external_id = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))

    profile_data = Column(JSONB, nullable=False, default=dict)
    attributes = Column(JSONB, default=dict)

    # GDPR (Gap M17)
    consent = Column(JSONB, default=dict)
    consent_updated_at = Column(DateTime(timezone=True))

    segments = Column(JSONB, default=list)
    tags = Column(JSONB, default=list)

    lifecycle_stage = Column(String(100))
    lead_score = Column(Integer)

    deletion_requested = Column(Boolean, default=False)
    deletion_requested_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_customer_profiles_tenant", "tenant_id"),
        Index("idx_customer_profiles_email", "tenant_id", "email"),
    )
