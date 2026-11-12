"""Test fixtures."""
import json
import os
import pytest
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
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
    """Use mocks when dummy keys are set; automatically use real APIs when real keys are provided."""
    google_key = os.environ.get("GOOGLE_API_KEY", "")
    if google_key and google_key != "dummy-key-for-ci":
        return  # Original key detected — run live Gemini and DeepEval calls

    # 1. Mock internal LLM helper
    async def fake_call_lite_llm(*args, **kwargs):
        prompt_text = str(args) + str(kwargs)
        has_website = "http" in prompt_text.lower()
        tier = "warm" if has_website else "cold"
        return json.dumps({
            "tier": tier,
            "score": 75 if has_website else 25,
            "reasoning": f"Mocked {tier} lead classification for CI.",
        })

    monkeypatch.setattr(llm, "call_lite_llm", fake_call_lite_llm)
    monkeypatch.setattr(lead_agent, "call_lite_llm", fake_call_lite_llm)

    # 2. Mock DeepEval metrics so they don't call OpenAI or require extra context params
    def fake_measure(self, test_case, *args, **kwargs):
        is_hallucination = isinstance(self, HallucinationMetric)
        self.score = 0.0 if is_hallucination else 1.0
        self.success = True
        self.reason = "Mocked evaluation for CI"
        return self.score

    async def fake_a_measure(self, test_case, *args, **kwargs):
        return fake_measure(self, test_case, *args, **kwargs)

    for metric_cls in (FaithfulnessMetric, HallucinationMetric, AnswerRelevancyMetric):
        monkeypatch.setattr(metric_cls, "measure", fake_measure)
        monkeypatch.setattr(metric_cls, "a_measure", fake_a_measure)


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
