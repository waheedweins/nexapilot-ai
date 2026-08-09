"""Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) instead of Postgres so the
test suite has no external dependency for unit/API-level tests. The CI
workflow additionally runs a real Postgres service container for anything
that needs Postgres-specific behavior (JSON columns, UUID type, etc.).
"""

import os

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import session as db_session
from app.database.session import Base
from app.main import app


@pytest.fixture(autouse=True)
async def setup_database():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    db_session.engine = test_engine
    db_session.AsyncSessionLocal.kw["bind"] = test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await test_engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
