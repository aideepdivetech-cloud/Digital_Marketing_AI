"""
Notification, Approval, and Credential models (Gaps H3, H5, H12).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index,
    UniqueConstraint, LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Notification(Base, UUIDMixin):
    """User notifications — in-app, email, WebSocket (Gap H3)."""
    __tablename__ = "notifications"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    type = Column(String(30), nullable=False)  # info, warning, error, success, task_complete, etc.
    channel = Column(String(20), nullable=False, default="in_app")  # in_app, email, websocket, sms, webhook

    title = Column(String(500), nullable=False)
    message = Column(Text)
    action_url = Column(String(1000))

    # Related entities
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"))
    approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id", ondelete="SET NULL"))

    metadata_ = Column("metadata", JSONB, default=dict)

    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_unread", "user_id", "is_read"),
    )


class Approval(Base, UUIDMixin):
    """HITL approval workflow — ALWAYS ASK model (Gap H12)."""
    __tablename__ = "approvals"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    entity_type = Column(String(100), nullable=False)  # task, campaign, artifact, action
    entity_id = Column(UUID(as_uuid=True), nullable=False)

    requested_by_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    approver_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Approval details
    approval_level = Column(Integer, default=1)
    max_approval_levels = Column(Integer, default=1)
    risk_level = Column(String(10), nullable=False, default="low")  # low, medium, high, critical

    # Content for review
    title = Column(String(500), nullable=False)
    description = Column(Text)
    context = Column(JSONB, default=dict)
    preview_data = Column(JSONB)

    # Status
    status = Column(String(20), nullable=False, default="pending")  # pending, approved, rejected, expired, auto_approved
    decision = Column(Text)
    decision_notes = Column(Text)

    # Timing
    requested_at = Column(DateTime(timezone=True), server_default="NOW()")
    responded_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Auto-approval rules
    auto_approve_conditions = Column(JSONB)

    __table_args__ = (
        Index("idx_approvals_pending", "tenant_id", "status"),
    )


class CredentialsVault(Base, UUIDMixin, TimestampMixin):
    """Encrypted credential storage for third-party APIs (Gap H5)."""
    __tablename__ = "credentials_vault"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    service_name = Column(String(255), nullable=False)  # hubspot, meta_ads, etc.
    credential_name = Column(String(255), nullable=False)
    credential_type = Column(String(20), nullable=False)  # api_key, oauth_token, password, certificate, webhook_secret

    # AES-256 encrypted value
    encrypted_value = Column(LargeBinary, nullable=False)
    encryption_key_id = Column(String(100), nullable=False)  # Key rotation support

    # Metadata
    metadata_ = Column("metadata", JSONB, default=dict)
    scopes = Column(JSONB, default=list)

    # Lifecycle
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    last_rotated_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "service_name", "credential_name",
                         name="unique_credential"),
    )
