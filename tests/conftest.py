"""Test fixtures."""
import json
import os
import pytest
from deepeval.metrics import FaithfulnessMetric
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

# Set up test environment variables BEFORE importing the app
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key-for-ci")

from app.agents import lead_agent
from app.core import llm
from app.database import session as db_session
from app.database.session import Base
from app.main import app


@pytest.fixture(autouse=True)
def mock_external_ai_services(monkeypatch):
    """Intercept all Gemini and DeepEval LLM calls so CI needs no real API keys."""

    # 1. Mock your internal LLM helper (patched at both definition and import sites)
    async def fake_call_lite_llm(*args, **kwargs):
        prompt_text = str(args) + str(kwargs)
        # Return 'cold' when no website/notes are present, otherwise 'warm'
        is_cold = "None" in prompt_text or "no website" in prompt_text.lower()
        tier = "cold" if is_cold else "warm"
        return json.dumps({
            "tier": tier,
            "score": 25 if is_cold else 75,
            "reasoning": f"Mocked {tier} lead classification for CI.",
        })

    monkeypatch.setattr(llm, "call_lite_llm", fake_call_lite_llm)
    monkeypatch.setattr(lead_agent, "call_lite_llm", fake_call_lite_llm)

    # 2. Mock DeepEval's FaithfulnessMetric so it doesn't call OpenAI
    def fake_measure(self, test_case, *args, **kwargs):
        self.score = 1.0
        self.success = True
        self.reason = "Mocked faithfulness evaluation for CI"
        return self.score

    async def fake_a_measure(self, test_case, *args, **kwargs):
        return fake_measure(self, test_case, *args, **kwargs)

    monkeypatch.setattr(FaithfulnessMetric, "measure", fake_measure)
    monkeypatch.setattr(FaithfulnessMetric, "a_measure", fake_a_measure)


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
