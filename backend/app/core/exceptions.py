"""
Custom exception classes for the Digital Marketing AI Platform.
All exceptions inherit from a base class for consistent error handling.
"""

from __future__ import annotations

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ── Auth Exceptions ──

class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(message=message, status_code=401, error_code="AUTH_FAILED", details=details)


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        super().__init__(message=message, status_code=403, error_code="FORBIDDEN", details=details)


class TokenExpiredError(AuthenticationError):
    def __init__(self):
        super().__init__(message="Token has expired", details={"reason": "expired"})


class InvalidTokenError(AuthenticationError):
    def __init__(self):
        super().__init__(message="Invalid token", details={"reason": "invalid"})


# ── Resource Exceptions ──

class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        details = {"resource": resource}
        if resource_id:
            details["id"] = str(resource_id)
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", details: Optional[dict] = None):
        super().__init__(message=message, status_code=409, error_code="CONFLICT", details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[dict] = None):
        super().__init__(message=message, status_code=422, error_code="VALIDATION_ERROR", details=details)


# ── Rate Limiting ──

class RateLimitError(AppException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after},
        )


# ── Agent Exceptions ──

class AgentError(AppException):
    def __init__(self, message: str = "Agent error", agent_id: Optional[str] = None, details: Optional[dict] = None):
        d = details or {}
        if agent_id:
            d["agent_id"] = agent_id
        super().__init__(message=message, status_code=500, error_code="AGENT_ERROR", details=d)


class AgentNotFoundError(NotFoundError):
    def __init__(self, agent_key: str):
        super().__init__(resource="Agent", resource_id=agent_key)


class AgentBusyError(AppException):
    def __init__(self, agent_key: str):
        super().__init__(
            message=f"Agent '{agent_key}' is currently processing another task",
            status_code=409,
            error_code="AGENT_BUSY",
            details={"agent_key": agent_key},
        )


# ── Task Exceptions ──

class TaskError(AppException):
    def __init__(self, message: str = "Task error", task_id: Optional[str] = None, details: Optional[dict] = None):
        d = details or {}
        if task_id:
            d["task_id"] = task_id
        super().__init__(message=message, status_code=500, error_code="TASK_ERROR", details=d)


class TaskNotFoundError(NotFoundError):
    def __init__(self, task_id: str):
        super().__init__(resource="Task", resource_id=task_id)


class TaskQueueFullError(AppException):
    def __init__(self, max_tasks: int):
        super().__init__(
            message="Task queue is full",
            status_code=429,
            error_code="QUEUE_FULL",
            details={"max_concurrent_tasks": max_tasks},
        )


class TaskRetryExhaustedError(TaskError):
    def __init__(self, task_id: str, retry_count: int):
        super().__init__(
            message="All retries exhausted, task moved to dead letter queue",
            task_id=task_id,
            details={"retry_count": retry_count},
        )


# ── LLM Exceptions ──

class LLMError(AppException):
    def __init__(self, message: str = "LLM error", details: Optional[dict] = None):
        super().__init__(message=message, status_code=502, error_code="LLM_ERROR", details=details)


class LLMConnectionError(LLMError):
    def __init__(self, provider: str = "ollama"):
        super().__init__(
            message=f"Cannot connect to LLM provider: {provider}",
            details={"provider": provider},
        )


class LLMTimeoutError(LLMError):
    def __init__(self, timeout_seconds: int):
        super().__init__(
            message="LLM inference timed out",
            details={"timeout_seconds": timeout_seconds},
        )


class AllModelsFailedError(LLMError):
    def __init__(self, models_tried: list[str]):
        super().__init__(
            message="All LLM models (primary + fallback) failed",
            details={"models_tried": models_tried},
        )


# ── Tool Exceptions ──

class ToolError(AppException):
    def __init__(self, message: str = "Tool execution error", tool_key: Optional[str] = None, details: Optional[dict] = None):
        d = details or {}
        if tool_key:
            d["tool_key"] = tool_key
        super().__init__(message=message, status_code=500, error_code="TOOL_ERROR", details=d)


class ToolNotFoundError(NotFoundError):
    def __init__(self, tool_key: str):
        super().__init__(resource="Tool", resource_id=tool_key)


# ── Tenant / Multi-tenancy ──

class TenantError(AppException):
    def __init__(self, message: str = "Tenant error", details: Optional[dict] = None):
        super().__init__(message=message, status_code=403, error_code="TENANT_ERROR", details=details)


class QuotaExceededError(AppException):
    def __init__(self, resource: str, limit: int):
        super().__init__(
            message=f"Quota exceeded for {resource}",
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            details={"resource": resource, "limit": limit},
        )


# ── Approval ──

class ApprovalRequiredError(AppException):
    def __init__(self, approval_id: str, action: str):
        super().__init__(
            message=f"Action '{action}' requires human approval",
            status_code=202,
            error_code="APPROVAL_REQUIRED",
            details={"approval_id": approval_id, "action": action},
        )


# ── Content Moderation ──

class ContentBlockedError(AppException):
    def __init__(self, flags: list[str]):
        super().__init__(
            message="Content blocked by safety filter",
            status_code=400,
            error_code="CONTENT_BLOCKED",
            details={"flags": flags},
        )
