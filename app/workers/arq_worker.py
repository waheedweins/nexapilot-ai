"""app/workers/arq_worker.py — ARQ Redis Background Worker Definition"""

import os
from arq import create_pool
from arq.connections import RedisSettings
from app.config import get_settings
from app.graph.orchestrator import run_agent_workflow
from app.memory.session_store import save_session_state
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def execute_agent_workflow_task(ctx: dict, session_id: str, task_type: str, payload: dict) -> dict:
    """ARQ worker task that executes the multi-agent workflow asynchronously in a separate process/worker."""
    logger.info("arq_task_started", session_id=session_id, task_type=task_type)
    
    try:
        # Execute the LangGraph orchestrator
        final_state = await run_agent_workflow(
            session_id=session_id,
            task_type=task_type,
            payload=payload
        )
        
        # Persist final state and agent execution logs to PostgreSQL
        await save_session_state(session_id=session_id, state=final_state)
        logger.info("arq_task_completed", session_id=session_id)
        return {"status": "success", "session_id": session_id}
        
    except Exception as e:
        logger.exception("arq_task_failed", session_id=session_id, error=str(e))
        raise e


class WorkerSettings:
    """ARQ Worker configuration settings."""
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [execute_agent_workflow_task]
    max_jobs = 10
    job_timeout = 300  # 5 minutes max per agent run
