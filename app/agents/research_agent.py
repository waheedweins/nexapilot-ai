"""Research Agent — gathers external information about a company/topic."""

from app.agents.base import GraphState, log_step
from app.tools.web_search import web_search

name = "research_agent"


async def run(state: GraphState) -> GraphState:
    payload = state.get("payload", {})
    query = payload.get("website") or payload.get("company_name") or payload.get("topic", "")

    results = await web_search(str(query)) if query else []

    return {
        "research_notes": results,
        "log": log_step(state, f"{name}: gathered {len(results)} result(s) for {query!r}"),
    }
