"""
Agent endpoints — list agents, get agent details, agent status.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import Agent
from app.db.session import get_db
from app.observability.logger import get_logger

router = APIRouter()
logger = get_logger("api.agents")


# ── Schemas ──

class AgentResponse(BaseModel):
    id: str
    agent_key: str
    name: str
    description: str | None
    agent_type: str
    status: str
    parent_agent_id: str | None
    capabilities: list | None
    risk_level: str | None


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int


# ── Endpoints ──

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    agent_type: Optional[str] = Query(None, description="Filter by type: boss, master, sub_brain, sub_execution"),
    status: Optional[str] = Query(None, description="Filter by status"),
    parent_id: Optional[str] = Query(None, description="Filter by parent agent ID"),
    db: AsyncSession = Depends(get_db),
):
    """List all registered agents."""
    query = select(Agent)

    if agent_type:
        query = query.where(Agent.agent_type == agent_type)
    if status:
        query = query.where(Agent.status == status)
    if parent_id:
        query = query.where(Agent.parent_agent_id == parent_id)

    query = query.order_by(Agent.agent_type, Agent.agent_key)
    result = await db.execute(query)
    agents = result.scalars().all()

    return AgentListResponse(
        agents=[
            AgentResponse(
                id=str(a.id),
                agent_key=a.agent_key,
                name=a.name,
                description=a.description,
                agent_type=a.agent_type,
                status=a.status,
                parent_agent_id=str(a.parent_agent_id) if a.parent_agent_id else None,
                capabilities=a.capabilities,
                risk_level=a.risk_level,
            )
            for a in agents
        ],
        total=len(agents),
    )


@router.get("/{agent_key}")
async def get_agent(agent_key: str, db: AsyncSession = Depends(get_db)):
    """Get a specific agent by key."""
    result = await db.execute(
        select(Agent).where(Agent.agent_key == agent_key)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        from app.core.exceptions import AgentNotFoundError
        raise AgentNotFoundError(agent_key)

    return AgentResponse(
        id=str(agent.id),
        agent_key=agent.agent_key,
        name=agent.name,
        description=agent.description,
        agent_type=agent.agent_type,
        status=agent.status,
        parent_agent_id=str(agent.parent_agent_id) if agent.parent_agent_id else None,
        capabilities=agent.capabilities,
        risk_level=agent.risk_level,
    )
