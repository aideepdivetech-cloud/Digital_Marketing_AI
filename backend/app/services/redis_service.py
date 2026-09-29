"""
Redis service — connection management, caching, pub/sub, distributed locks.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings
from app.observability.logger import get_logger

logger = get_logger("app.services.redis")


class RedisManager:
    """Manages Redis connection pool and provides utility methods."""

    def __init__(self):
        self._pool: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        settings = get_settings()
        self._pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        # Test connection
        await self._pool.ping()
        logger.info("redis_pool_created", url=settings.redis_url)

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("redis_pool_closed")

    @property
    def client(self) -> aioredis.Redis:
        """Get the Redis client. Raises if not connected."""
        if not self._pool:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._pool

    # ── Cache Operations ──

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value (auto-deserializes JSON)."""
        value = await self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a cached value (auto-serializes to JSON)."""
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self.client.set(key, serialized, ex=ttl_seconds)

    async def cache_delete(self, key: str) -> None:
        """Delete a cached value."""
        await self.client.delete(key)

    async def cache_exists(self, key: str) -> bool:
        """Check if a cache key exists."""
        return bool(await self.client.exists(key))

    # ── Pub/Sub (Event Bus) ──

    async def publish(self, channel: str, message: dict) -> int:
        """Publish a message to a Redis channel."""
        serialized = json.dumps(message)
        return await self.client.publish(channel, serialized)

    def subscribe(self, *channels: str) -> aioredis.client.PubSub:
        """Create a pub/sub subscription."""
        pubsub = self.client.pubsub()
        return pubsub

    # ── Distributed Locks ──

    async def acquire_lock(
        self, lock_key: str, ttl_seconds: int = 300, value: str = "locked"
    ) -> bool:
        """Acquire a distributed lock. Returns True if acquired."""
        result = await self.client.set(lock_key, value, nx=True, ex=ttl_seconds)
        return result is not None

    async def release_lock(self, lock_key: str) -> None:
        """Release a distributed lock."""
        await self.client.delete(lock_key)

    async def extend_lock(self, lock_key: str, ttl_seconds: int = 300) -> bool:
        """Extend a lock's TTL."""
        return bool(await self.client.expire(lock_key, ttl_seconds))

    # ── Rate Limiting ──

    async def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window counter.
        Returns (is_allowed, remaining_requests).
        """
        current = await self.client.get(key)
        if current is None:
            await self.client.set(key, 1, ex=window_seconds)
            return True, max_requests - 1

        count = int(current)
        if count >= max_requests:
            return False, 0

        await self.client.incr(key)
        return True, max_requests - count - 1

    # ── Counter Operations ──

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return await self.client.incrby(key, amount)


# Singleton instance
redis_manager = RedisManager()
