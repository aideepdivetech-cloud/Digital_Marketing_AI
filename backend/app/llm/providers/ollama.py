"""
Ollama LLM provider — communicates with the self-hosted Ollama server.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Optional

import httpx

from app.config import get_settings
from app.core.exceptions import LLMConnectionError, LLMTimeoutError
from app.llm.providers.base import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMResponse,
    LLMToolDefinition,
)
from app.observability.logger import get_logger

logger = get_logger("app.llm.ollama")


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(self):
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._timeout = httpx.Timeout(300.0, connect=10.0)

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage objects to Ollama API format."""
        formatted = []
        for msg in messages:
            m = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            formatted.append(m)
        return formatted

    def _format_tools(self, tools: list[LLMToolDefinition]) -> list[dict]:
        """Convert LLMToolDefinition objects to Ollama API format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]

    async def generate(
        self,
        messages: list[LLMMessage],
        config: LLMConfig,
        tools: Optional[list[LLMToolDefinition]] = None,
    ) -> LLMResponse:
        """Generate a response from Ollama."""
        start_time = time.monotonic()

        payload: dict[str, Any] = {
            "model": config.model,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "repeat_penalty": config.repeat_penalty,
            },
        }

        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences

        if config.seed is not None:
            payload["options"]["seed"] = config.seed

        if config.response_format == "json":
            payload["format"] = "json"

        if tools:
            payload["tools"] = self._format_tools(tools)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.ConnectError:
            logger.error("ollama_connection_failed", url=self._base_url)
            raise LLMConnectionError("ollama")
        except httpx.TimeoutException:
            logger.error("ollama_timeout", model=config.model)
            raise LLMTimeoutError(timeout_seconds=int(self._timeout.read))
        except httpx.HTTPStatusError as e:
            logger.error("ollama_http_error", status=e.response.status_code, detail=str(e))
            raise LLMConnectionError("ollama")

        # Parse response
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        message = data.get("message", {})
        content = message.get("content", "")

        # Token counts
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        total_tokens = prompt_tokens + completion_tokens

        # Tokens per second
        eval_duration_ns = data.get("eval_duration", 1)
        tps = (completion_tokens / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0

        # Tool calls
        tool_calls = message.get("tool_calls", [])

        logger.info(
            "llm_inference_complete",
            model=config.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            inference_ms=elapsed_ms,
            tps=round(tps, 1),
            has_tool_calls=bool(tool_calls),
        )

        return LLMResponse(
            content=content,
            model=config.model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            inference_time_ms=elapsed_ms,
            tokens_per_second=round(tps, 2),
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
            raw_response=data,
        )

    async def generate_stream(
        self,
        messages: list[LLMMessage],
        config: LLMConfig,
        tools: Optional[list[LLMToolDefinition]] = None,
    ) -> AsyncIterator[str]:
        """Stream a response from Ollama, yielding content chunks."""
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": self._format_messages(messages),
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p,
                "repeat_penalty": config.repeat_penalty,
            },
        }

        if config.response_format == "json":
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            message = data.get("message", {})
                            chunk = message.get("content", "")
                            if chunk:
                                yield chunk
                            if data.get("done", False):
                                return
        except httpx.ConnectError:
            raise LLMConnectionError("ollama")
        except httpx.TimeoutException:
            raise LLMTimeoutError(timeout_seconds=int(self._timeout.read))

    async def generate_embeddings(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """Generate embeddings using Ollama's embedding endpoint."""
        settings = get_settings()
        embedding_model = model or settings.embedding_model

        embeddings = []
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                for text in texts:
                    response = await client.post(
                        f"{self._base_url}/api/embed",
                        json={"model": embedding_model, "input": text},
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Ollama returns {"embeddings": [[...]]}
                    embedding = data.get("embeddings", [[]])[0]
                    embeddings.append(embedding)
        except httpx.ConnectError:
            raise LLMConnectionError("ollama")
        except httpx.TimeoutException:
            raise LLMTimeoutError(timeout_seconds=int(self._timeout.read))

        logger.info("embeddings_generated", model=embedding_model, count=len(embeddings))
        return embeddings

    async def is_healthy(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List all models available in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error("list_models_failed", error=str(e))
            return []
