"""
Purpose: Centralized Lite LLM Client with LangChain Fallback Support
--------------------------------------------------------------------------------
Provides a resilient LLM setup using Google Gemini Flash as primary,
with automatic fallback options if the primary model encounters rate limits or errors.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from app.logging_config import get_logger

logger = get_logger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 1. Primary Model (e.g., gemini-2.5-flash)
primary_llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    google_api_key=GEMINI_API_KEY,
    temperature=0.1,
    max_retries=1
)

# 2. Secondary / Fallback Model (e.g., gemini-1.5-flash as a reliable free-tier backup)
fallback_llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.1,
    max_retries=2
)

# 3. Resilient chain combining primary and fallback via LangChain
resilient_llm = primary_llm.with_fallbacks([fallback_llm])


async def call_lite_llm(prompt: str, system_instruction: str = None) -> str:
    """Sends a prompt through the primary LLM, falling back automatically on error."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "test-api-key":
        logger.warning("gemini_client_mock_mode_active")
        return f"Warm lead. Mock analysis for: {prompt[:40]}..."

    try:
        messages = []
        if system_instruction:
            messages.append(HumanMessage(content=f"System Instruction: {system_instruction}"))
        messages.append(HumanMessage(content=prompt))

        response = await resilient_llm.ainvoke(messages)
        return response.text
        
    except Exception as e:
        logger.error("all_llm_fallbacks_failed", error=str(e))
        return "Warm (Fallback default due to LLM error)"
