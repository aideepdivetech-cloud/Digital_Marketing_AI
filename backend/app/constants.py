"""
System-wide constants for the Digital Marketing AI Platform.
"""

# ── Task Status Flow ──
# pending → queued → routing → delegated → in_progress → completed
#                  → awaiting_approval → approved → in_progress
#                                      → cancelled
#                  → failed → (retry) → queued
#                           → dead_letter

TASK_STATUSES = {
    "pending",
    "queued",
    "routing",
    "awaiting_approval",
    "approved",
    "delegated",
    "in_progress",
    "awaiting_sub",
    "tool_executing",
    "paused",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
    "dead_letter",
}

TASK_TERMINAL_STATUSES = {"completed", "failed", "cancelled", "dead_letter"}
TASK_ACTIVE_STATUSES = {"queued", "routing", "delegated", "in_progress", "awaiting_sub", "tool_executing"}

# ── Task Priorities ──
PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}

# ── Agent Types ──
AGENT_TYPES = {"boss", "master", "sub_brain", "sub_execution"}

# ── Master Agent Keys ──
MASTER_AGENT_KEYS = {
    "m01_brand_pr": "Brand, PR & Community",
    "m02_content": "Content Marketing",
    "m03_ecommerce": "Conversion & E-commerce",
    "m04_email": "Email & Lifecycle",
    "m05_lead_gen": "Lead Generation & CRM",
    "m06_paid_ads": "Paid Advertising & Media",
    "m07_seo": "SEO",
    "m08_social": "Social Media",
    "m09_video": "Video & Multimedia",
    "m10_analytics": "Marketing Analytics & BI",
    "m11_cdp": "Customer Data Platform",
    "m12_ops": "Marketing Operations & Automation",
}

# ── Brain Categories ──
BRAIN_CATEGORIES = {"research", "strategy", "technical", "analytics"}

# ── Execution Categories ──
EXECUTION_CATEGORIES = {"content", "media", "distribution", "operations"}

# ── Tool Categories ──
TOOL_CATEGORIES = {"content", "web", "data", "communication", "analysis", "third_party"}

# ── Notification Types ──
NOTIFICATION_TYPES = {
    "info", "warning", "error", "success",
    "task_complete", "task_failed", "approval_needed",
    "queue_update", "system", "campaign_update",
}

# ── Risk Levels ──
RISK_LEVELS = {"low", "medium", "high", "critical"}

# ── LLM Defaults ──
DEFAULT_LLM_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
}

# ── Retry Defaults ──
DEFAULT_MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff base in seconds
RETRY_BACKOFF_MAX = 300  # Max backoff = 5 minutes

# ── WebSocket Channels ──
WS_CHANNEL_TASK_UPDATES = "task_updates"
WS_CHANNEL_AGENT_PROGRESS = "agent_progress"
WS_CHANNEL_NOTIFICATIONS = "notifications"
WS_CHANNEL_QUEUE_UPDATES = "queue_updates"

# ── Heartbeat ──
HEARTBEAT_INTERVAL_SECONDS = 30
HEARTBEAT_STALE_THRESHOLD_SECONDS = 90

# ── Event Types ──
EVENT_TYPES = {
    # Content events
    "content.created", "content.published", "content.updated",
    # Customer events
    "customer.created", "customer.updated", "customer.segment_changed",
    # Campaign events
    "campaign.created", "campaign.launched", "campaign.paused", "campaign.completed",
    # Conversion events
    "conversion.lead_captured", "conversion.sale_completed", "conversion.cart_abandoned",
    # Performance events
    "performance.threshold_hit", "performance.anomaly_detected", "performance.report_ready",
    # System events
    "system.approval_requested", "system.approval_granted", "system.error_occurred",
    # Agent events
    "agent.task_started", "agent.task_completed", "agent.task_failed",
    # Integration events
    "webhook.received", "schedule.triggered",
}
