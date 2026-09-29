"""
Tool models — Central Tool Hub registry (Gaps C4, C11).
"""

from __future__ import annotations

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.models.mixins import UUIDMixin, TimestampMixin


class Tool(Base, UUIDMixin, TimestampMixin):
    """Central tool registry shared across all agents."""
    __tablename__ = "tools"

    tool_key = Column(String(150), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100))  # content, web, data, communication, analysis, third_party

    # Schema (Gap C4 — Tool contract)
    parameters_schema = Column(JSONB, nullable=False, default=dict)
    returns_schema = Column(JSONB, default=dict)
    required_params = Column(JSONB, default=list)

    # Hosting
    host_type = Column(String(20), nullable=False, default="self_hosted")  # self_hosted, third_party, sandbox
    endpoint_url = Column(String(500))
    requires_sandbox = Column(Boolean, default=False)  # Gap C15

    # Status
    status = Column(String(20), nullable=False, default="available")  # available, unavailable, deprecated, testing
    config = Column(JSONB, default=dict)

    # Rate limiting (Gap L1 — outbound API rate limiting)
    rate_limit_per_minute = Column(Integer)
    rate_limit_per_hour = Column(Integer)
    rate_limit_per_day = Column(Integer)

    # Cost
    cost_per_call_usd = Column(Numeric(10, 6), default=0)

    version = Column(String(50), default="1.0.0")

    # Relationships
    agent_tools = relationship("AgentTool", back_populates="tool", cascade="all, delete-orphan")
    executions = relationship("ToolExecution", back_populates="tool")


class ToolExecution(Base, UUIDMixin):
    """Log of every tool call execution."""
    __tablename__ = "tool_executions"

    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"))
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False)

    status = Column(String(20), nullable=False, default="pending")  # pending, running, success, failed, timeout, retrying

    input_parameters = Column(JSONB, nullable=False, default=dict)
    output_result = Column(JSONB)
    error_message = Column(Text)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time_ms = Column(Integer)

    retry_count = Column(Integer, default=0)
    cost_usd = Column(Numeric(10, 6), default=0)
    correlation_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime(timezone=True), server_default="NOW()")

    task = relationship("Task", back_populates="tool_executions")
    tool = relationship("Tool", back_populates="executions")

    __table_args__ = (
        Index("idx_tool_exec_task", "task_id"),
        Index("idx_tool_exec_correlation", "correlation_id"),
    )
