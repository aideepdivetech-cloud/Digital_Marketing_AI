"""
Database models package — imports all ORM models so Alembic can discover them.

Total: 34 tables covering all 68 gaps.
"""

# Mixins
from app.db.models.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

# Tenant
from app.db.models.tenant import Tenant

# User & Auth
from app.db.models.user import User, Role, UserRole, UserSetting

# Agents
from app.db.models.agent import Agent, AgentVersion, PromptTemplate, AgentTool

# Tasks
from app.db.models.task import Task, TaskDependency, TaskStep, TaskQueue, DeadLetterQueue

# Conversations
from app.db.models.conversation import Session, Conversation, Message

# Campaigns
from app.db.models.campaign import Campaign, CampaignContext

# Tools
from app.db.models.tool import Tool, ToolExecution

# Artifacts
from app.db.models.artifact import Artifact, AssetLibrary

# Events
from app.db.models.event import Event, EventSubscription, EventProcessingLog

# Notifications, Approvals, Credentials
from app.db.models.notification import Notification, Approval, CredentialsVault

# Monitoring & Operations
from app.db.models.monitoring import (
    AgentMemory,
    UsageTracking,
    LLMUsageLog,
    SystemHealth,
    AgentHeartbeat,
    Webhook,
    WebhookEvent,
    ScheduledTask,
    Feedback,
    AuditLog,
    FeatureFlag,
    SystemConfig,
    AgentLock,
    ModerationLog,
    CustomerProfile,
)

__all__ = [
    # Tenant
    "Tenant",
    # User
    "User", "Role", "UserRole", "UserSetting",
    # Agent
    "Agent", "AgentVersion", "PromptTemplate", "AgentTool",
    # Task
    "Task", "TaskDependency", "TaskStep", "TaskQueue", "DeadLetterQueue",
    # Conversation
    "Session", "Conversation", "Message",
    # Campaign
    "Campaign", "CampaignContext",
    # Tool
    "Tool", "ToolExecution",
    # Artifact
    "Artifact", "AssetLibrary",
    # Event
    "Event", "EventSubscription", "EventProcessingLog",
    # Notification
    "Notification", "Approval", "CredentialsVault",
    # Monitoring
    "AgentMemory", "UsageTracking", "LLMUsageLog",
    "SystemHealth", "AgentHeartbeat",
    "Webhook", "WebhookEvent",
    "ScheduledTask", "Feedback",
    "AuditLog", "FeatureFlag", "SystemConfig",
    "AgentLock", "ModerationLog", "CustomerProfile",
]
