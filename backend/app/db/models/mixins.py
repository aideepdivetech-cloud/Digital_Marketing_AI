"""
Reusable SQLAlchemy mixins for common column patterns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Boolean, text
from sqlalchemy.dialects.postgresql import UUID


class UUIDMixin:
    """Adds a UUID primary key column."""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=text("NOW()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds soft-delete support via deleted_at column."""
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class TenantMixin:
    """Adds tenant_id column for multi-tenancy isolation."""
    # Note: The actual ForeignKey is defined in each model to avoid
    # circular import issues. This mixin just documents the pattern.
    pass
