"""Lead Agent — scores and qualifies a lead using research notes.

Uses Gemini for live scoring when an API key is present, falling back 
to the deterministic heuristic for tests and CI/CD.
"""

from google import genai
from app.agents.base import GraphState, log_step
from app.config import get_settings

name = "lead_agent"


async def _score_with_llm(payload: dict, research_notes: list[dict]) -> tuple[str, str]:
    settings = get_settings()

    # Use Gemini if API key is configured
    if settings.gemini_api_key:
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"""
            Analyze the following business lead and research notes. 
            Classify the lead score strictly as 'hot', 'warm', or 'cold'.
            Provide a concise reasoning for your decision.

            Payload: {payload}
            Research Notes: {research_notes}
            """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

            response_text = response.text.strip().lower()
            
            score = "warm"
            if "hot" in response_text[:20]:
                score = "hot"
            elif "cold" in response_text[:20]:
                score = "cold"

            return score, response.text
        except Exception as e:
            # Fall back to heuristic if API call fails
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
