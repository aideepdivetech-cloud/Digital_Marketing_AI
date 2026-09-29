"""
JWT token management — access tokens, refresh tokens, verification.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Utilities ──

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Utilities ──

def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    role: str,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID, tenant_id: UUID) -> str:
    """Create a JWT refresh token with longer expiry."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises on invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            raise TokenExpiredError()
        raise InvalidTokenError()


def verify_access_token(token: str) -> dict[str, Any]:
    """Decode an access token and verify it's the correct type."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidTokenError()
    return payload


def verify_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token and verify it's the correct type."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise InvalidTokenError()
    return payload
