"""
Abstract LLM provider interface — all providers must implement this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class LLMMessage:
    """A single message in an LLM conversation."""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMToolDefinition:
    """Definition of a tool that the LLM can call."""
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class LLMResponse:
    """Response from an LLM inference call."""
    content: str
    model: str
    provider: str

    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Performance
    inference_time_ms: int = 0
    tokens_per_second: float = 0.0

    # Tool calls (if any)
    tool_calls: list[dict] = field(default_factory=list)

    # Metadata
    finish_reason: str = "stop"
    was_cached: bool = False
    was_fallback: bool = False
    raw_response: Optional[dict] = None


@dataclass
class LLMConfig:
    """Configuration for an LLM inference call."""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    stop_sequences: list[str] = field(default_factory=list)
    response_format: Optional[str] = None  # "json" for JSON mode
    seed: Optional[int] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'ollama')."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig,
        tools: Optional[list[LLMToolDefinition]] = None,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig,
        tools: Optional[list[LLMToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response from the LLM, yielding chunks."""
        ...

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the LLM provider is accessible."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List all available models."""
        ...
