"""
Tenant model — Multi-tenancy foundation (Gap C13).
"""

from __future__ import annotations

from sqlalchemy import Column, String, Integer, BigInteger, Numeric, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="trial")  # active, trial, suspended, cancelled
    plan = Column(String(20), nullable=False, default="free")  # free, starter, professional, enterprise

    # Quotas
    max_users = Column(Integer, default=5)
    max_concurrent_tasks = Column(Integer, default=20)
    max_llm_tokens_per_month = Column(BigInteger, default=1_000_000)
    max_storage_gb = Column(Numeric(10, 2), default=10.00)
    max_api_calls_per_month = Column(Integer, default=10_000)

    # Settings & branding
    settings = Column(JSONB, default=dict)
    branding = Column(JSONB, default=dict)

    # Billing
    trial_ends_at = Column(DateTime(timezone=True))
    subscription_ends_at = Column(DateTime(timezone=True))

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tenants_status", "status"),
    )
