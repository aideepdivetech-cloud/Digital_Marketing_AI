"""
API v1 router — aggregates all endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, conversations, tasks, agents

api_v1_router = APIRouter()

# Include sub-routers
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
api_v1_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_v1_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
