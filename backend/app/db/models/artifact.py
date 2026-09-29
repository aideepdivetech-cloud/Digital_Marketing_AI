"""
Artifact and Asset Library models (Gaps H1, H14, H16).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin


class Artifact(Base, UUIDMixin):
    """Generated files and outputs from agent work."""
    __tablename__ = "artifacts"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    name = Column(String(500), nullable=False)
    artifact_type = Column(String(20), nullable=False)  # text, json, csv, image, pdf, html, etc.
    mime_type = Column(String(100))

    file_path = Column(String(1000))  # Path in MinIO
    file_size_bytes = Column(Integer)
    content_text = Column(Text)  # Inline for text artifacts
    content_json = Column(JSONB)  # Inline for JSON artifacts

    metadata_ = Column("metadata", JSONB, default=dict)
    checksum = Column(String(64))

    # Version control (Gap H16)
    version = Column(Integer, default=1)
    parent_artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"))
    is_latest = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    task = relationship("Task", back_populates="artifacts")
    campaign = relationship("Campaign", back_populates="artifacts")

    __table_args__ = (
        Index("idx_artifacts_tenant", "tenant_id"),
        Index("idx_artifacts_task", "task_id"),
        Index("idx_artifacts_campaign", "campaign_id"),
        Index("idx_artifacts_type", "artifact_type"),
    )


class AssetLibrary(Base, UUIDMixin):
    """Shared assets across agents within a campaign (Gap H14)."""
    __tablename__ = "asset_library"

    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"))

    asset_type = Column(String(100))
    name = Column(String(500), nullable=False)
    description = Column(Text)
    tags = Column(JSONB, default=list)

    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"))

    is_public = Column(Boolean, default=True)
    allowed_agent_ids = Column(JSONB, default=list)

    version = Column(Integer, default=1)
    parent_asset_id = Column(UUID(as_uuid=True), ForeignKey("asset_library.id"))

    created_by_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), server_default="NOW()")
