"""
Agent models — Central registry, versioning, prompt templates (Gaps C9, M2, H19).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Index,
    UniqueConstraint, Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Agent(Base, UUIDMixin, TimestampMixin):
    """Central agent registry — Boss, Master, Sub-Brain, Sub-Execution."""
    __tablename__ = "agents"

    agent_key = Column(String(150), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    agent_type = Column(String(20), nullable=False)  # boss, master, sub_brain, sub_execution

    status = Column(String(20), nullable=False, default="active")  # active, inactive, maintenance, deprecated, error

    # Hierarchy
    parent_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"))

    # Categorization (for sub-agents)
    brain_category = Column(String(20))  # research, strategy, technical, analytics
    execution_category = Column(String(20))  # content, media, distribution, operations

    # LLM Configuration
    current_prompt_template_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="SET NULL"))
    model_id = Column(String(255), nullable=False)
    fallback_model_id = Column(String(255))

    llm_config = Column(JSONB, default={
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
    })

    # Capabilities
    capabilities = Column(JSONB, default=list)

    # Operational
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=300)
    requires_approval = Column(Boolean, default=False)
    risk_level = Column(String(20), default="low")  # low, medium, high, critical

    # Versioning
    version = Column(Integer, default=1)

    # Relationships
    parent = relationship("Agent", remote_side="Agent.id", backref="children")
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    memories = relationship("AgentMemory", back_populates="agent", cascade="all, delete-orphan")
    prompt_template = relationship("PromptTemplate", foreign_keys=[current_prompt_template_id])

    __table_args__ = (
        Index("idx_agents_type", "agent_type"),
        Index("idx_agents_parent", "parent_agent_id"),
        Index("idx_agents_status", "status"),
    )


class AgentVersion(Base, UUIDMixin):
    """Agent version history for rollback (Gap M2)."""
    __tablename__ = "agent_versions"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)

    prompt_template_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"))
    llm_config = Column(JSONB, nullable=False)
    capabilities = Column(JSONB, default=list)

    change_notes = Column(Text)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    agent = relationship("Agent", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="unique_agent_version"),
    )


class PromptTemplate(Base, UUIDMixin, TimestampMixin):
    """Database-managed prompt templates with Jinja2 support (Gap H19)."""
    __tablename__ = "prompt_templates"

    template_key = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Template content (Jinja2 format)
    template_content = Column(Text, nullable=False)
    variables = Column(JSONB, default=list)  # Expected template variables

    # Metadata
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    tags = Column(JSONB, default=list)

    # Performance
    avg_quality_score = Column(String(10))  # Stored as string to avoid float issues
    usage_count = Column(Integer, default=0)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("template_key", "version", name="unique_prompt_template_version"),
        Index("idx_prompt_templates_key", "template_key"),
        Index("idx_prompt_templates_active", "is_active"),
    )


class AgentTool(Base):
    """Many-to-many: which agents can use which tools."""
    __tablename__ = "agent_tools"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True)
    config_override = Column(JSONB, default=dict)
    is_required = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    agent = relationship("Agent", back_populates="tools")
    tool = relationship("Tool", back_populates="agent_tools")
