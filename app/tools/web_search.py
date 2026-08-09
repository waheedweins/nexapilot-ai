"""Pluggable web-search tool used by the Research agent.

Uses Tavily's search API when TAVILY_API_KEY is set. Falls back to a stub
response so the graph is runnable end-to-end in dev/CI without external
credentials.
"""

import httpx

from app.config import get_settings

TAVILY_ENDPOINT = "https://api.tavily.com/search"


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    settings = get_settings()

    if not settings.tavily_api_key:
        return [
            {
                "title": "Search unavailable (no TAVILY_API_KEY configured)",
                "url": None,
                "content": f"Stubbed result for query: {query!r}",
            }
        ]

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TAVILY_ENDPOINT,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "content": item.get("content"),
        }
        for item in data.get("results", [])
    ]
