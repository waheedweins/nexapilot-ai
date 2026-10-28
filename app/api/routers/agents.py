import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, verify_auth0_token
from app.core.guardrails import validate_input_guardrail
from app.core.output_guardrails import walk_and_sanitize
from app.graph.orchestrator import run_orchestrator
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


class InvokeResponse(BaseModel):
    session_id: str
    task_type: str
    research_notes: list[dict]
    lead_score: str | None
    lead_reasoning: str | None
    ops_result: dict | None
    log: list[str]


@router.post("/invoke", response_model=InvokeResponse)
async def invoke_agent(
    body: InvokeRequest, 
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(verify_auth0_token)
) -> InvokeResponse:
    """Run the LangGraph orchestrator for a given task, enforce security guards, and persist the session."""
    
    # 1. Validate payload against prompt injection and malicious input guardrails (Jev)
    await validate_input_guardrail(body.payload)

    user_id = token_payload.get("sub")
    session = await session_store.create_session(
        db, task_type=body.task_type, initial_state=body.payload
    )

    initial_state = {
        "task_type": body.task_type,
        "session_id": str(session.id),
        "payload": body.payload,
        "log": [],
    }

    logger.info("agent_invoke_start", session_id=str(session.id), user_id=user_id, task_type=body.task_type)
    result_state = await run_orchestrator(initial_state)
    logger.info("agent_invoke_complete", session_id=str(session.id))

    await session_store.update_session_state(db, session, state=result_state, status="completed")
    await session_store.append_message(
        db, session.id, role="agent", content=str(result_state), agent_name="orchestrator"
    )

    # 2. Extract result fields
    raw_response = {
        "session_id": str(session.id),
        "task_type": body.task_type,
        "research_notes": result_state.get("research_notes", []),
        "lead_score": result_state.get("lead_score"),
        "lead_reasoning": result_state.get("lead_reasoning"),
        "ops_result": result_state.get("ops_result"),
        "log": result_state.get("log", []),
    }

    # 3. Apply Output Guardrails to sanitize PII and sensitive data before returning
    safe_response = walk_and_sanitize(raw_response)

    return InvokeResponse(**safe_response)


@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    session = await session_store.get_session(db, session_id)
    if session is None:
        return {"error": "not_found"}
    
    # Also sanitize session state if retrieved directly
    safe_state = walk_and_sanitize(session.state)
    
    return {
        "id": str(session.id),
        "task_type": session.task_type,
        "status": session.status,
        "state": safe_state,
    }
