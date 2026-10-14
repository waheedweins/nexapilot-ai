"""Lead Agent — scores and qualifies a lead using research notes.

Uses LangChain with Gemini for live scoring when an API key is present, falling back 
to the deterministic heuristic for tests and CI/CD.
"""

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.base import GraphState, log_step
from app.config import get_settings

name = "lead_agent"


async def _score_with_llm(payload: dict, research_notes: list[dict]) -> tuple[str, str]:
    settings = get_settings()

    # Use LangChain's ChatGoogleGenerativeAI if API key is configured
    if settings.gemini_api_key:
        try:
            # Initialize LangChain's Gemini chat model wrapper
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=settings.gemini_api_key,
                temperature=0.1
            )
            
            prompt = f"""
            Analyze the following business lead and research notes. 
            Classify the lead score strictly as 'hot', 'warm', or 'cold'.
            Provide a concise reasoning for your decision.

            Payload: {payload}
            Research Notes: {research_notes}
            """

            # Asynchronously invoke the LangChain model
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            response_text = response.content.strip().lower()
            
            score = "warm"
            if "hot" in response_text[:20]:
                score = "hot"
            elif "cold" in response_text[:20]:
                score = "cold"

            return score, response.content
            
        except Exception:
            # Fall back to heuristic if API call or execution fails
            pass

    # Deterministic fallback heuristic (used in tests / when no key is set)
    has_website = bool(payload.get("website"))
    has_notes = bool(research_notes) and research_notes[0].get("url") is not None

    if has_website and has_notes:
        return "warm", "Company has an active web presence and research notes were found."
    if has_website:
        return "warm", "Company has a website; research was inconclusive."
    return "cold", "No website or usable research notes were found."


async def run(state: GraphState) -> GraphState:
    payload = state.get("payload", {})
    research_notes = state.get("research_notes", [])

    score, reasoning = await _score_with_llm(payload, research_notes)

    return {
        "lead_score": score,
        "lead_reasoning": reasoning,
        "log": log_step(state, f"{name}: scored lead as '{score}'"),
    }
