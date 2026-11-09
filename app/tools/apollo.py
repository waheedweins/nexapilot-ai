"""app/tools/apollo.py — Apollo.io Firmographic Data Enrichment Tool"""

import httpx
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def enrich_company_via_apollo(domain: str) -> dict:
    """Fetches verified B2B firmographics, employee counts, and tech stacks using Apollo.io API."""
    if not settings.apollo_api_key:
        logger.warning("apollo_api_key_not_configured")
        return {"status": "skipped", "reason": "API key missing"}

    url = f"https://api.apollo.io/api/v1/organizations/enrich?domain={domain}"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "x-api-key": settings.apollo_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                org = data.get("organization", {})
                if not org:
                    return {"status": "not_found", "message": "No company match found in Apollo."}

                return {
                    "status": "success",
                    "company_name": org.get("name"),
                    "website": org.get("website_url"),
                    "industry": org.get("industry"),
                    "estimated_employees": org.get("estimated_num_employees"),
                    "country": org.get("country"),
                    "technologies": [t.get("name") for t in org.get("current_technologies", [])[:10]],
                    "linkedin_url": org.get("linkedin_url"),
                }
            else:
                logger.error("apollo_api_error", status_code=response.status_code, body=response.text)
                return {"status": "error", "status_code": response.status_code}
        except Exception as e:
            logger.exception("apollo_service_exception", error=str(e))
            return {"status": "error", "message": str(e)}
