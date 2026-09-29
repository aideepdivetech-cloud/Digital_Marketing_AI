"""
Boss Agent — The central router that receives user queries and delegates to Master Agents.

Flow: User → Boss Agent → Intent Classification → Route to Master Agent
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.agents.base.base_agent import AgentContext, AgentResult, BaseAgent
from app.constants import MASTER_AGENT_KEYS
from app.llm.providers.base import LLMConfig, LLMMessage, LLMToolDefinition
from app.observability.logger import get_logger

logger = get_logger("agent.boss")

# Master agent keys for routing
ROUTING_MAP = {
    "brand_pr": "m01_brand_pr",
    "content_marketing": "m02_content",
    "ecommerce": "m03_ecommerce",
    "email_lifecycle": "m04_email",
    "lead_generation": "m05_lead_gen",
    "paid_advertising": "m06_paid_ads",
    "seo": "m07_seo",
    "social_media": "m08_social",
    "video_multimedia": "m09_video",
    "analytics": "m10_analytics",
    "cdp": "m11_cdp",
    "marketing_ops": "m12_ops",
}


class BossAgent(BaseAgent):
    """
    The Boss Agent is the central orchestrator. It:
    1. Receives user queries
    2. Classifies intent
    3. Routes to the appropriate Master Agent
    4. Returns the Master Agent's response
    """

    def __init__(self):
        super().__init__(
            agent_key="boss_agent",
            agent_type="boss",
            name="Boss Agent",
            description="Central orchestrator that routes tasks to Master Agents",
            llm_config=LLMConfig(
                temperature=0.3,  # Low temp for reliable classification
                max_tokens=1024,
            ),
        )

    def get_system_prompt(self, context: AgentContext) -> str:
        """Boss Agent system prompt for intent classification and routing."""
        master_list = "\n".join(
            f"  - {key}: {name}" for key, name in MASTER_AGENT_KEYS.items()
        )

        return f"""You are the Boss Agent — the central router for a Digital Marketing AI Platform.

Your job is to:
1. Understand the user's digital marketing question or task
2. Classify which Master Agent should handle it
3. Extract the key parameters for the task

## Available Master Agents:
{master_list}

## Your Response Format:
You MUST respond with a JSON object (no markdown, no explanation):
{{
    "intent": "<brief description of what the user wants>",
    "master_agent_key": "<one of the master agent keys above>",
    "confidence": <0.0 to 1.0>,
    "task_title": "<short title for this task>",
    "task_description": "<detailed description of the task>",
    "parameters": {{
        // extracted parameters relevant to the task
    }},
    "requires_clarification": false,
    "clarification_question": null,
    "risk_level": "low"  // low, medium, high, critical
}}

## Routing Rules:
- Lead generation, CRM, prospecting, lead scoring → m05_lead_gen
- SEO, keywords, backlinks, technical SEO, SERP → m07_seo
- Social media, posts, engagement, community → m08_social
- Paid ads, PPC, Google Ads, Meta Ads, budgets → m06_paid_ads
- Email marketing, newsletters, drip campaigns → m04_email
- Content creation, blogs, articles, editorial → m02_content
- Video, YouTube, multimedia, podcasts → m09_video
- CRO, conversion, checkout, A/B testing → m03_ecommerce
- Brand, PR, reputation, crisis, community → m01_brand_pr
- Analytics, dashboards, reporting, KPIs → m10_analytics
- Customer data, segments, CDP, profiles → m11_cdp
- Automation, workflows, integrations → m12_ops

## Important:
- If the request is unclear, set "requires_clarification" to true
- If the request spans multiple domains, choose the PRIMARY one
- ALWAYS respond with valid JSON only"""

    def get_tools(self) -> list[LLMToolDefinition]:
        """Boss Agent uses structured JSON output, not tool calls."""
        return []

    async def execute(self, context: AgentContext, input_data: dict[str, Any]) -> AgentResult:
        """
        Classify user intent and route to the appropriate Master Agent.
        """
        user_query = input_data.get("query", input_data.get("message", ""))

        if not user_query:
            return AgentResult(
                success=False,
                error="No query provided. Please ask a digital marketing question.",
            )

        logger.info(
            "boss_processing_query",
            query_preview=user_query[:100],
            tenant_id=str(context.tenant_id),
        )

        # Build messages for classification
        messages = self.build_messages(context, user_query)

        # Call LLM with JSON mode
        config = LLMConfig(
            temperature=0.3,
            max_tokens=1024,
            response_format="json",
        )

        response = await self.call_llm(messages, context, config_override=config)

        # Parse the classification response
        try:
            classification = json.loads(response.content)
        except json.JSONDecodeError:
            logger.error("boss_json_parse_failed", raw=response.content[:200])
            return AgentResult(
                success=False,
                error="Failed to classify your request. Please rephrase and try again.",
            )

        # Validate the routing
        master_key = classification.get("master_agent_key", "")
        if master_key not in MASTER_AGENT_KEYS:
            # Try to find a match from the routing map
            intent_lower = classification.get("intent", "").lower()
            for keyword, key in ROUTING_MAP.items():
                if keyword.replace("_", " ") in intent_lower:
                    master_key = key
                    break

        if master_key not in MASTER_AGENT_KEYS:
            logger.warning("boss_unknown_master", key=master_key)
            return AgentResult(
                success=False,
                error=f"Could not route to a Master Agent. Detected: {master_key}",
            )

        # Check if clarification is needed
        if classification.get("requires_clarification"):
            return AgentResult(
                success=True,
                output={
                    "type": "clarification_needed",
                    "question": classification.get("clarification_question", "Could you provide more details?"),
                    "partial_classification": classification,
                },
            )

        logger.info(
            "boss_routed",
            master_agent=master_key,
            confidence=classification.get("confidence", 0),
            risk_level=classification.get("risk_level", "low"),
        )

        # Return delegation result
        return AgentResult(
            success=True,
            output=classification,
            delegate_to=master_key,
            delegate_input={
                "original_query": user_query,
                "classification": classification,
                "parameters": classification.get("parameters", {}),
            },
            tokens_used=response.total_tokens,
        )
