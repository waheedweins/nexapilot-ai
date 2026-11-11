"""scripts/ingest_docs.py — Ingests internal markdown/text playbooks into Qdrant vector store."""

import asyncio

from langchain_core.documents import Document

from app.core.rag import get_vector_store
from app.logging_config import get_logger

logger = get_logger(__name__)

INITIAL_PLAYBOOKS = [
    Document(
        page_content=(
            "NexaPilot AI B2B Lead Qualification Criteria: Target companies "
            "must have >50 employees, active digital infrastructure, and a verified "
            "domain. High-priority leads are solar, tech, and enterprise manufacturing sectors."
        ),
        metadata={"source": "sales_playbook_v1.md"},
    ),
    Document(
        page_content=(
            "Pricing & Tiers: NexaPilot AI offers Starter ($29/mo), Professional "
            "($99/mo), and Enterprise (Custom SLA). Automated outreach uses Gemini "
            "Flash for fast reasoning and Apollo for firmographics."
        ),
        metadata={"source": "pricing_catalog.md"},
    ),
]


async def main():
    logger.info("starting_vector_ingestion")
    vector_store = get_vector_store()

    # Add documents to Qdrant vector store
    vector_store.add_documents(INITIAL_PLAYBOOKS)
    logger.info("vector_ingestion_completed", total_docs=len(INITIAL_PLAYBOOKS))


if __name__ == "__main__":
    asyncio.run(main())
