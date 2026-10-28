"""Cache manager for NexaPilot AI to eliminate redundant LLM API calls."""

import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models import PromptCache
from app.logging_config import get_logger

logger = get_logger(__name__)


def generate_prompt_hash(task_type: str, payload: dict) -> str:
    """Normalizes task type and payload and generates a unique SHA-256 hash key."""
    normalized_data = {
        "task_type": task_type.strip().lower(),
        "payload": {k: str(v).strip().lower() for k, v in sorted(payload.items())}
    }
    raw_str = json.dumps(normalized_data, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


async def get_cached_response(db: AsyncSession, task_type: str, payload: dict) -> dict | None:
    """Checks if a cached response exists for the given prompt signature."""
    prompt_hash = generate_prompt_hash(task_type, payload)
    
    result = await db.execute(
        select(PromptCache).where(PromptCache.prompt_hash == prompt_hash)
    )
    cached_entry = result.scalars().first()
    
    if cached_entry:
        logger.info("cache_hit", prompt_hash=prompt_hash, task_type=task_type)
        return json.loads(cached_entry.response_data)
        
    logger.debug("cache_miss", prompt_hash=prompt_hash, task_type=task_type)
    return None


async def set_cached_response(db: AsyncSession, task_type: str, payload: dict, response_data: dict) -> None:
    """Saves an agent response to the database cache."""
    prompt_hash = generate_prompt_hash(task_type, payload)
    
    try:
        cache_entry = PromptCache(
            prompt_hash=prompt_hash,
            task_type=task_type,
            response_data=json.dumps(response_data)
        )
        db.add(cache_entry)
        await db.commit()
        logger.info("cache_stored", prompt_hash=prompt_hash, task_type=task_type)
    except Exception as e:
        await db.rollback()
        logger.error("cache_store_failed", error=str(e), prompt_hash=prompt_hash)
