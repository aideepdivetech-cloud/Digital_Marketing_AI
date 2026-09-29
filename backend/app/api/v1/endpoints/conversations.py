"""
Conversation endpoints — chat with Boss Agent.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base.base_agent import AgentContext
from app.agents.boss.boss_agent import BossAgent
from app.db.models.conversation import Conversation, Message
from app.db.session import get_db
from app.observability.logger import get_logger

router = APIRouter()
logger = get_logger("api.conversations")


# ── Schemas ──

class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    conversation_id: str
    message_id: str
    role: str
    content: str
    agent_response: dict | None = None


# ── Endpoints ──

@router.post("/chat", response_model=MessageResponse)
async def chat(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the Boss Agent.
    Creates a new conversation if conversation_id is not provided.
    """
    # TODO: Get from JWT auth middleware
    tenant_id = uuid4()  # Placeholder
    user_id = uuid4()    # Placeholder

    # Get or create conversation
    conversation_id = None
    if request.conversation_id:
        conversation_id = UUID(request.conversation_id)
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            conversation_id = None

    if not conversation_id:
        conversation = Conversation(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            title=request.message[:100],
            message_count=0,
        )
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id

    # Save user message
    user_msg = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        sequence_number=(conversation.message_count or 0) + 1,
    )
    db.add(user_msg)

    # Execute Boss Agent
    task_id = uuid4()
    context = AgentContext(
        tenant_id=tenant_id,
        user_id=user_id,
        task_id=task_id,
        conversation_id=conversation_id,
    )

    boss = BossAgent()
    result = await boss.execute(context, {"query": request.message})

    # Build response content
    if result.success:
        output = result.output
        if isinstance(output, dict) and output.get("type") == "clarification_needed":
            response_content = output.get("question", "Could you provide more details?")
        elif result.delegate_to:
            master_name = output.get("task_title", result.delegate_to)
            response_content = (
                f"I've identified this as a **{master_name}** task and routed it to the "
                f"**{output.get('master_agent_key', result.delegate_to)}** Master Agent.\n\n"
                f"**Task:** {output.get('task_description', request.message)}\n"
                f"**Confidence:** {output.get('confidence', 'N/A')}\n"
                f"**Risk Level:** {output.get('risk_level', 'low')}"
            )
        else:
            response_content = str(output)
    else:
        response_content = f"I'm sorry, I encountered an error: {result.error}"

    # Save assistant message
    assistant_msg = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        role="assistant",
        content=response_content,
        sequence_number=(conversation.message_count or 0) + 2,
        tokens_used=result.tokens_used,
    )
    db.add(assistant_msg)

    # Update conversation
    conversation.message_count = (conversation.message_count or 0) + 2

    logger.info(
        "chat_processed",
        conversation_id=str(conversation_id),
        delegate_to=result.delegate_to,
    )

    return MessageResponse(
        conversation_id=str(conversation_id),
        message_id=str(assistant_msg.id),
        role="assistant",
        content=response_content,
        agent_response=result.output if result.success else None,
    )
