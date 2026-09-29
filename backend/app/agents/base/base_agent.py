"""
Base Agent abstract class — the foundation for Boss, Master, and Sub agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from app.llm.client import llm_client
from app.llm.providers.base import LLMConfig, LLMMessage, LLMResponse, LLMToolDefinition
from app.observability.logger import get_logger


@dataclass
class AgentContext:
    """Runtime context passed to every agent invocation."""
    tenant_id: UUID
    user_id: UUID
    task_id: UUID
    conversation_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None

    # Shared data from parent agent or campaign
    shared_context: dict[str, Any] = field(default_factory=dict)

    # Conversation history (trimmed to fit context window)
    message_history: list[LLMMessage] = field(default_factory=list)


@dataclass
class AgentResult:
    """Result returned by an agent after execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    artifacts: list[dict] = field(default_factory=list)
    tool_calls_made: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    sub_tasks: list[dict] = field(default_factory=list)

    # For delegation (Boss → Master)
    delegate_to: Optional[str] = None  # master agent key
    delegate_input: Optional[dict] = None


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system.

    Hierarchy:
      BaseAgent
        ├── BossAgent (intent classification, routing)
        ├── BaseMasterAgent (sub-agent orchestration)
        │     ├── LeadGenMaster
        │     ├── SEOMaster
        │     └── ...
        └── BaseSubAgent (actual work execution)
              ├── BaseSubBrainAgent (research, strategy)
              └── BaseSubExecutionAgent (content, distribution)
    """

    def __init__(
        self,
        agent_key: str,
        agent_type: str,
        name: str,
        description: str = "",
        model_id: Optional[str] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        self.agent_key = agent_key
        self.agent_type = agent_type  # boss, master, sub_brain, sub_execution
        self.name = name
        self.description = description
        self.model_id = model_id
        self.llm_config = llm_config or LLMConfig()
        self.logger = get_logger(f"agent.{agent_key}")

    @abstractmethod
    async def execute(self, context: AgentContext, input_data: dict[str, Any]) -> AgentResult:
        """Execute the agent's primary function. Must be implemented by all agents."""
        ...

    @abstractmethod
    def get_system_prompt(self, context: AgentContext) -> str:
        """Return the system prompt for this agent. Must be implemented."""
        ...

    def get_tools(self) -> list[LLMToolDefinition]:
        """Return tools available to this agent. Override in subclasses."""
        return []

    async def call_llm(
        self,
        messages: list[LLMMessage],
        context: AgentContext,
        tools: Optional[list[LLMToolDefinition]] = None,
        config_override: Optional[LLMConfig] = None,
    ) -> LLMResponse:
        """Call the LLM with this agent's configuration."""
        config = config_override or self.llm_config
        if self.model_id:
            config.model = self.model_id

        return await llm_client.generate(
            messages=messages,
            agent_type=self.agent_type,
            config_override=config,
            tools=tools or self.get_tools(),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            task_id=context.task_id,
        )

    def build_messages(
        self,
        context: AgentContext,
        user_input: str,
        additional_context: str = "",
    ) -> list[LLMMessage]:
        """Build the message list for an LLM call."""
        messages = [
            LLMMessage(role="system", content=self.get_system_prompt(context)),
        ]

        # Add conversation history if available
        if context.message_history:
            messages.extend(context.message_history)

        # Add additional context if provided
        if additional_context:
            messages.append(LLMMessage(
                role="system",
                content=f"Additional context:\n{additional_context}",
            ))

        # Add the user's current input
        messages.append(LLMMessage(role="user", content=user_input))

        return messages


class BaseMasterAgent(BaseAgent):
    """
    Base class for Master Agents (e.g., Lead Gen, SEO, Content).
    Handles sub-agent orchestration and delegation.
    """

    def __init__(self, **kwargs):
        super().__init__(agent_type="master", **kwargs)
        self._sub_agents: dict[str, BaseAgent] = {}

    def register_sub_agent(self, agent: BaseAgent) -> None:
        """Register a sub-agent under this master."""
        self._sub_agents[agent.agent_key] = agent
        self.logger.info("sub_agent_registered", sub_agent=agent.agent_key)

    def get_sub_agent(self, agent_key: str) -> Optional[BaseAgent]:
        """Get a registered sub-agent by key."""
        return self._sub_agents.get(agent_key)

    def list_sub_agents(self) -> list[str]:
        """List all registered sub-agent keys."""
        return list(self._sub_agents.keys())

    async def delegate_to_sub_agent(
        self,
        sub_agent_key: str,
        context: AgentContext,
        input_data: dict[str, Any],
    ) -> AgentResult:
        """Delegate work to a specific sub-agent."""
        sub_agent = self.get_sub_agent(sub_agent_key)
        if not sub_agent:
            return AgentResult(
                success=False,
                error=f"Sub-agent '{sub_agent_key}' not found in {self.agent_key}",
            )

        self.logger.info(
            "delegating_to_sub_agent",
            master=self.agent_key,
            sub_agent=sub_agent_key,
        )

        return await sub_agent.execute(context, input_data)


class BaseSubBrainAgent(BaseAgent):
    """Base class for Brain sub-agents (research, strategy, analytics)."""

    def __init__(self, **kwargs):
        super().__init__(agent_type="sub_brain", **kwargs)


class BaseSubExecutionAgent(BaseAgent):
    """Base class for Execution sub-agents (content, distribution, ops)."""

    def __init__(self, **kwargs):
        super().__init__(agent_type="sub_execution", **kwargs)
