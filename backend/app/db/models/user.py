"""
User and Role models — Auth, RBAC, multi-tenant (Gaps C13, M3).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Index,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    email = Column(String(255), nullable=False)
    username = Column(String(100))
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(String(500))

    # Role & status
    role = Column(String(20), nullable=False, default="operator")  # super_admin, tenant_admin, manager, operator, viewer
    status = Column(String(20), nullable=False, default="pending_verification")  # active, inactive, suspended, pending_verification

    # Security
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255))

    # Preferences
    preferences = Column(JSONB, default=dict)
    timezone = Column(String(50), default="UTC")
    locale = Column(String(10), default="en")

    # Session tracking
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(INET)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", foreign_keys="Task.user_id")
    settings = relationship("UserSetting", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="unique_email_per_tenant"),
        Index("idx_users_tenant", "tenant_id"),
        Index("idx_users_email", "email"),
    )


class Role(Base, UUIDMixin):
    __tablename__ = "roles"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)  # NULL = system role
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    is_system = Column(Boolean, default=False)
    permissions = Column(JSONB, nullable=False, default=list)  # Array of permission strings

    created_at = Column(DateTime(timezone=True), server_default="NOW()")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default="NOW()")


class UserSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    setting_key = Column(String(255), nullable=False)
    setting_value = Column(JSONB, nullable=False)

    user = relationship("User", back_populates="settings")

    __table_args__ = (
        UniqueConstraint("user_id", "setting_key", name="unique_user_setting"),
    )
