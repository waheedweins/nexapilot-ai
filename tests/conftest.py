"""Test fixtures."""
import os
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import session as db_session
from app.database.session import Base
from app.main import app

# Set up test environment variables
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-ci")

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
