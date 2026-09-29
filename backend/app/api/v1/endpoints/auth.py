"""
Authentication endpoints — register, login, refresh token.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.db.models.user import User
from app.db.models.tenant import Tenant
from app.db.session import get_db
from app.observability.logger import get_logger

router = APIRouter()
logger = get_logger("api.auth")


# ── Request/Response Schemas ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    tenant_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    tenant_id: str
    role: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    tenant_id: str


# ── Endpoints ──

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their tenant."""

    # Check if email already exists
    existing = await db.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise ConflictError(message="Email already registered")

    # Create tenant
    tenant = Tenant(
        id=uuid4(),
        slug=request.tenant_name.lower().replace(" ", "-").replace("_", "-"),
        name=request.tenant_name,
        status="trial",
        plan="free",
    )
    db.add(tenant)
    await db.flush()

    # Create user as tenant_admin
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role="tenant_admin",
        status="active",
        email_verified=False,
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    access_token = create_access_token(user.id, tenant.id, user.role)
    refresh_token = create_refresh_token(user.id, tenant.id)

    logger.info("user_registered", user_id=str(user.id), tenant_id=str(tenant.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and return tokens."""

    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise AuthenticationError(message="Invalid email or password")

    if user.status != "active":
        raise AuthenticationError(message=f"Account is {user.status}")

    # Generate tokens
    access_token = create_access_token(user.id, user.tenant_id, user.role)
    refresh_token = create_refresh_token(user.id, user.tenant_id)

    logger.info("user_logged_in", user_id=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token using a refresh token."""

    payload = verify_refresh_token(request.refresh_token)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        raise AuthenticationError(message="User not found or inactive")

    # Generate new tokens
    access_token = create_access_token(user.id, user.tenant_id, user.role)
    new_refresh_token = create_refresh_token(user.id, user.tenant_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )
