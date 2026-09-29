"""
Campaign models — Multi-agent campaign orchestration (Gaps C9, H15).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, ForeignKey, Index,
    UniqueConstraint, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Campaign(Base, UUIDMixin, TimestampMixin):
    """Multi-agent campaigns spanning multiple Master Agents."""
    __tablename__ = "campaigns"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="draft")  # draft, planning, active, paused, completed, archived

    # Timeline
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))

    # Budget
    budget_amount = Column(Numeric(12, 2))
    spent_amount = Column(Numeric(12, 2), default=0)
    currency = Column(String(3), default="USD")

    # Shared context (Gap C10)
    context = Column(JSONB, nullable=False, default=dict)

    # Which masters are involved
    involved_masters = Column(JSONB, default=list)

    # Goals & KPIs
    goals = Column(JSONB, default=list)
    kpis = Column(JSONB, default=list)

    completed_at = Column(DateTime(timezone=True))

    # Relationships
    tenant = relationship("Tenant", back_populates="campaigns")
    tasks = relationship("Task", back_populates="campaign")
    context_entries = relationship("CampaignContext", back_populates="campaign", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="campaign")

    __table_args__ = (
        Index("idx_campaigns_tenant", "tenant_id"),
        Index("idx_campaigns_user", "user_id"),
        Index("idx_campaigns_status", "status"),
    )


class CampaignContext(Base, UUIDMixin, TimestampMixin):
    """Shared context data per campaign (Gap H15)."""
    __tablename__ = "campaign_context"

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    context_key = Column(String(255), nullable=False)
    context_value = Column(JSONB, nullable=False)
    version = Column(Integer, default=1)

    created_by_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    updated_by_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    campaign = relationship("Campaign", back_populates="context_entries")

    __table_args__ = (
        UniqueConstraint("campaign_id", "context_key", name="unique_campaign_context_key"),
    )
