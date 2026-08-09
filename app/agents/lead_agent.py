"""Lead Agent — scores and qualifies a lead using research notes.

The actual LLM call is isolated in `_score_with_llm` so it can be swapped
between providers (Gemini/OpenAI) or mocked entirely in tests.
"""

from app.agents.base import GraphState, log_step

name = "lead_agent"


async def _score_with_llm(payload: dict, research_notes: list[dict]) -> tuple[str, str]:
    """Placeholder scoring heuristic.

    Replace with a real LLM call (Gemini/OpenAI) once API keys are wired up.
    Keeping this deterministic keeps the graph testable without network
    access or API costs in CI.
    """
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
