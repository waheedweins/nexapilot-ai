"""Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) instead of Postgres so the
test suite has no external dependency for unit/API-level tests. The CI
workflow additionally runs a real Postgres service container for anything
that needs Postgres-specific behavior (JSON columns, UUID type, etc.).
"""

import os
import sys
import types

# --- LANGCHAIN 0.3.x DEEPEVAL PATCH ---
# DeepEval relies on 'langchain.schema' which was removed in LangChain 0.3.0.
# We inject a fake module here BEFORE importing our app to prevent ModuleNotFoundErrors.
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.documents import Document
from langchain_core.outputs import Generation, LLMResult

mock_schema = types.ModuleType("langchain.schema")
mock_schema.HumanMessage = HumanMessage
mock_schema.AIMessage = AIMessage
mock_schema.SystemMessage = SystemMessage
mock_schema.BaseMessage = BaseMessage
mock_schema.Document = Document
mock_schema.Generation = Generation
mock_schema.LLMResult = LLMResult

sys.modules["langchain.schema"] = mock_schema
# --------------------------------------

# Set up test environment variables
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-ci")

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
