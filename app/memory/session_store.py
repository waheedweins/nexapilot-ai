"""Persists agent-session state and message history to Postgres.

This is the "conversation/session state" memory layer referenced in the
project roadmap (Phase 3). Long-term knowledge / RAG can be layered on top
of this later without changing the orchestrator's interface.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AgentSession, SessionMessage


async def create_session(db: AsyncSession, task_type: str, initial_state: dict) -> AgentSession:
    session = AgentSession(task_type=task_type, status="running", state=initial_state)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    return result.scalar_one_or_none()


async def update_session_state(
    db: AsyncSession, session: AgentSession, state: dict, status: str | None = None
) -> AgentSession:
    session.state = state
    if status:
        session.status = status
    await db.commit()
    await db.refresh(session)
    return session


async def append_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    agent_name: str | None = None,
) -> SessionMessage:
    message = SessionMessage(
        session_id=session_id, role=role, agent_name=agent_name, content=content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
