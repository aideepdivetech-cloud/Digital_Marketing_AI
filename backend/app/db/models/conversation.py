"""
Conversation and Message models — Chat sessions with Boss Agent.
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Session(Base, UUIDMixin):
    """User sessions with lifecycle management (Gap M11)."""
    __tablename__ = "sessions"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    session_token = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active, idle, expired, closed

    device_info = Column(JSONB, default=dict)
    ip_address = Column(String(45))  # IPv6 max length

    started_at = Column(DateTime(timezone=True), server_default="NOW()")
    last_activity_at = Column(DateTime(timezone=True), server_default="NOW()")
    expires_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
    )


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Chat conversation sessions."""
    __tablename__ = "conversations"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"))

    title = Column(String(500))
    summary = Column(Text)  # Auto-generated summary for long conversations (Gap H22)

    metadata_ = Column("metadata", JSONB, default=dict)
    is_active = Column(Boolean, default=True)

    message_count = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.sequence_number")
    tasks = relationship("Task", back_populates="conversation")

    __table_args__ = (
        Index("idx_conversations_user", "user_id"),
        Index("idx_conversations_tenant", "tenant_id"),
    )


class Message(Base, UUIDMixin):
    """Individual messages in a conversation."""
    __tablename__ = "messages"

    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)

    role = Column(String(20), nullable=False)  # user, assistant, system, tool, function
    content = Column(Text, nullable=False)

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"))
    tool_call_id = Column(UUID(as_uuid=True))

    # Multi-modal support (Gap M10)
    attachments = Column(JSONB, default=list)

    metadata_ = Column("metadata", JSONB, default=dict)
    tokens_used = Column(Integer)

    sequence_number = Column(Integer, nullable=False)
    correlation_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "sequence_number"),
        Index("idx_messages_correlation", "correlation_id"),
    )
