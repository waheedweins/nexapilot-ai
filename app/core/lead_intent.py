"""
Purpose: Lead Intent & Execution Router (NexaPilot AI)
--------------------------------------------------------------------------------
Analyzes incoming lead payloads using the TypeSafe Jev model:
- 'live_research': Forces the agent orchestrator to run live web searches and 
  enrichment tools for a fresh company analysis (bypassing cache).
- 'cached_operations': Allows standard operational or qualification queries 
  to check the PostgreSQL prompt cache, saving LLM tokens and execution time.
"""

import os
import httpx
from app.logging_config import get_logger

logger = get_logger(__name__)

TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY", "")
TYPESAFE_API_URL = "https://api.typesafe.ai/v1/evaluate"


async def classify_lead_intent(task_type: str, payload: dict) -> str:
    """Classifies whether a lead task requires live web research or can use cached/standard flows.
    Returns: 'live_research' or 'cached_operations'
    """
    
    # Extract company name or prompt from the lead payload
    company = payload.get("company_name") or payload.get("domain") or str(payload)

    # Fallback for local testing or CI where Jev key isn't present
    if not TYPESAFE_API_KEY or TYPESAFE_API_KEY == "test-typesafe-api-key":
        return "cached_operations"

    request_payload = {
        "state": {"task_type": task_type, "lead_input": company},
        "questions": {
            "execution_mode": {
                "type": "choice",
                "options": ["live_research", "cached_operations"],
                "description": (
                    "Choose 'live_research' if the task requires fetching fresh external company data, "
                    "scraping a live website, or performing real-time lead enrichment. "
                    "Choose 'cached_operations' if it is a standard lead scoring rule, pipeline check, "
                    "or operational review that doesn't require live external lookups."
                )
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                TYPESAFE_API_URL,
                headers={
                    "Authorization": f"Bearer {TYPESAFE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=request_payload
            )
            if response.status_code == 200:
                data = response.json()
                mode = data.get("answers", {}).get("execution_mode", {}).get("choice", "cached_operations")
                logger.info("lead_intent_classified", mode=mode, target=company[:40])
                return "live_research" if mode == "live_research" else "cached_operations"
                
    except Exception as e:
        logger.error("lead_intent_classification_failed", error=str(e))

    # Fail-safe default to cached operations if the evaluation API errors out
    return "cached_operations"
