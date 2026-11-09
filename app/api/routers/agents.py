"""app/api/routers/agents.py — Asynchronous Agent Orchestration Router via ARQ & Redis"""

import uuid
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_auth0_token
from app.core.guardrails import validate_input_guardrail
from app.core.output_guardrails import walk_and_sanitize
from app.core.cache import get_cached_response
from app.core.lead_intent import classify_lead_intent
from app.logging_config import get_logger
from app.memory import session_store

router = APIRouter(prefix="/v1/agents", tags=["agents"], dependencies=[Depends(verify_auth0_token)])
logger = get_logger(__name__)


class InvokeRequest(BaseModel):
    task_type: str = Field(
        default="lead_qualification",
        description="research_only | lead_qualification | operations",
    )
    session_id: str | None = None
    payload: dict = Field(default_factory=dict)


class EnqueueResponse(BaseModel):
    status: str
    job_id: str
    session_id: str
    message: str


@router.post("/invoke", response_model=EnqueueResponse)
async def invoke_agent(
    request: Request,
    body: InvokeRequest, 
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_auth0_token)
) -> EnqueueResponse:
    """Enqueues multi-agent workflow into Redis ARQ worker queue for distributed non-blocking execution."""
    
    # 1. Validate payload against prompt injection and malicious input guardrails (Jev)
    await validate_input_guardrail(body.payload)

    # 2. Classify Lead Intent
    execution_intent = await classify_lead_intent(body.task_type, body.payload)

    # 3. Check Cache if it's a cached operational task
    if execution_intent == "cached_operations":
        cached_data = await get_cached_response(db, body.task_type, body.payload)
        if cached_data:
            logger.info("returning_cached_lead_response", task_type=body.task_type)
            # If cached, we can return directly or let the worker handle it. 
            # For async job queues, returning enqueued status with session is standard.

    # 4. Create initial session record in PostgreSQL
    session = await session_store.create_session(
        db, task_type=body.task_type, initial_state=body.payload
    )
    session_id = str(session.id)

    # 5. Get ARQ Redis Pool from app state
    arq_pool = getattr(request.app.state, "arq_pool", None)
    if not arq_pool:
        raise HTTPException(status_code=500, detail="Redis ARQ worker pool is not initialized.")

    # 6. Push job to Redis background worker queue
    job = await arq_pool.enqueue_job(
        "execute_agent_workflow_task",
        session_id=session_id,
        task_type=body.task_type,
        payload=body.payload
    )

    logger.info("agent_workflow_enqueued_to_redis", session_id=session_id, job_id=job.job_id)

    return EnqueueResponse(
        status="enqueued",
        job_id=job.job_id,
        session_id=session_id,
        message="Workflow successfully enqueued to Redis background workers."
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    session = await session_store.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Sanitize session state before returning
    safe_state = walk_and_sanitize(session.state)
    
    return {
        "id": str(session.id),
        "task_type": session.task_type,
        "status": session.status,
        "state": safe_state,
    }
