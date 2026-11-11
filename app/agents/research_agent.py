"""Research Agent — gathers internal RAG knowledge, Apollo firmographics, and web search data."""

from app.agents.base import GraphState, log_step
from app.core.rag import hybrid_corporate_search
from app.tools.apollo import enrich_company_via_apollo
from app.tools.web_search import web_search

name = "research_agent"


async def run(state: GraphState) -> GraphState:
    payload = state.get("payload", {})
    company_name = payload.get("company_name", "")
    website = payload.get("website", "")
    query = (
        payload.get("query")
        or website
        or company_name
        or payload.get("topic", "")
    )

    # 1. Internal RAG Search (Qdrant vector database)
    internal_knowledge = (
        await hybrid_corporate_search(query=str(query)) if query else []
    )

    # 2. External B2B Enrichment (Apollo.io) if website is provided
    apollo_data = {}
    if website:
        domain = (
            website.replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
        )
        apollo_data = await enrich_company_via_apollo(domain=domain)

    # 3. Fallback Web Search (Tavily) if external Apollo data is missing or it's a general query
    web_results = []
    if not apollo_data or apollo_data.get("status") != "success":
        web_results = await web_search(str(query)) if query else []

    research_notes = {
        "internal_rag_context": internal_knowledge,
        "external_apollo_firmographics": apollo_data,
        "external_web_snippets": web_results,
    }

    existing_notes = state.get("research_notes", [])
    updated_notes = (
        existing_notes + [research_notes]
        if isinstance(existing_notes, list)
        else [research_notes]
    )

    return {
        "research_notes": updated_notes,
        "log": log_step(
            state,
            f"{name}: completed hybrid research (RAG, Apollo, Web) for {query!r}",
        ),
    }
