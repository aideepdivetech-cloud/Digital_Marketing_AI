"""
LLM Client — unified interface with fallback chain and usage logging.
Boss Agent uses 3B model, sub-agents use 1B model, with 1B as fallback.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional
from uuid import UUID

from app.config import get_settings
from app.core.exceptions import AllModelsFailedError
from app.llm.providers.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMToolDefinition,
)
from app.llm.providers.ollama import OllamaProvider
from app.observability.logger import get_logger

logger = get_logger("app.llm.client")


class LLMClient:
    """
    Unified LLM client with fallback chain.

    Model assignment:
      - Boss Agent: llama3.2:3b (primary) → llama3.2:1b (fallback)
      - Sub-Agents: llama3.2:1b (primary) → llama3.2:1b (same, retry only)
    """

    def __init__(self):
        self._provider: BaseLLMProvider = OllamaProvider()
        self._settings = get_settings()

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the appropriate model ID based on agent type."""
        if agent_type == "boss":
            return self._settings.boss_agent_model
        return self._settings.sub_agent_model

    def get_fallback_model(self) -> str:
        """Get the fallback model ID."""
        return self._settings.fallback_model

    async def generate(
        self,
        messages: list[LLMMessage],
        agent_type: str = "sub_brain",
        config_override: Optional[LLMConfig] = None,
        tools: Optional[list[LLMToolDefinition]] = None,
        tenant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> LLMResponse:
        """
        Generate a response with automatic fallback.
        Tries primary model first, falls back to fallback model on failure.
        """
        primary_model = self.get_model_for_agent(agent_type)
        fallback_model = self.get_fallback_model()

        config = config_override or LLMConfig()
        config.model = primary_model

        models_to_try = [primary_model]
        if fallback_model != primary_model:
            models_to_try.append(fallback_model)

        last_error: Optional[Exception] = None

        for i, model in enumerate(models_to_try):
            config.model = model
            is_fallback = i > 0

            try:
                if is_fallback:
                    logger.warning("llm_fallback_attempt", model=model, primary=primary_model)

                response = await self._provider.generate(messages, config, tools)
                response.was_fallback = is_fallback

                # Log usage (async, non-blocking)
                await self._log_usage(
                    response=response,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    task_id=task_id,
                    agent_id=agent_id,
                )

                return response

            except Exception as e:
                last_error = e
                logger.error(
                    "llm_model_failed",
                    model=model,
                    error=str(e),
                    attempt=i + 1,
                    total_models=len(models_to_try),
                )

        raise AllModelsFailedError(models_tried=models_to_try)

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        agent_type: str = "sub_brain",
        config_override: Optional[LLMConfig] = None,
    ) -> AsyncIterator[str]:
        """Stream a response (no fallback for streaming — keeps it simple)."""
        model = self.get_model_for_agent(agent_type)
        config = config_override or LLMConfig()
        config.model = model

        async for chunk in self._provider.generate_stream(messages, config):
            yield chunk

    async def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings using the configured embedding model."""
        return await self._provider.generate_embeddings(texts)

    async def is_healthy(self) -> bool:
        """Check if the LLM provider is healthy."""
        return await self._provider.is_healthy()

    async def _log_usage(
        self,
        response: LLMResponse,
        tenant_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> None:
        """Log LLM usage to database (non-blocking, best-effort)."""
        try:
            from app.db.session import get_db_context
            from app.db.models.monitoring import LLMUsageLog

            async with get_db_context() as db:
                log_entry = LLMUsageLog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    task_id=task_id,
                    agent_id=agent_id,
                    model_id=response.model,
                    provider=response.provider,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    inference_time_ms=response.inference_time_ms,
                    tokens_per_second=response.tokens_per_second,
                    was_cached=response.was_cached,
                    was_fallback=response.was_fallback,
                )
                db.add(log_entry)
        except Exception as e:
            # Usage logging should never break the main flow
            logger.warning("usage_log_failed", error=str(e))


# Singleton instance
llm_client = LLMClient()
