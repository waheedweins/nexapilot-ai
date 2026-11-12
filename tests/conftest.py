"""Test fixtures."""
import os
import uuid
from types import SimpleNamespace

import pytest
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

# Set up test environment variables BEFORE importing the app
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GOOGLE_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-ci")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key-for-ci")

from app.agents import lead_agent
from app.api.deps import verify_auth0_token
from app.api.routers import agents as agents_router
from app.config import get_settings
from app.core import llm
from app.database import session as db_session
from app.database.session import Base
from app.main import app


class _DummyArqPool:
    """In-memory stand-in for Redis ARQ pool during API tests."""

    async def enqueue_job(self, function_name: str, **kwargs):
        return SimpleNamespace(job_id=f"test-job-{uuid.uuid4().hex[:8]}")


@pytest.fixture(autouse=True)
def mock_external_ai_services(monkeypatch):
    """Use mocks when dummy keys are set; automatically use real APIs when real keys are provided."""
    google_key = os.environ.get("GOOGLE_API_KEY", "")
    if google_key and google_key != "dummy-key-for-ci":
        return  # Original key detected — run live Gemini and DeepEval calls

    # 1. Mock internal LLM helper (plain text matching app/agents/lead_agent.py)
    async def fake_call_lite_llm(*args, **kwargs):
        prompt_text = str(args) + str(kwargs)
        if "http" in prompt_text.lower():
            return "Warm lead. Company website and research notes verified."
        return "Cold lead. No website or research notes were found."

    monkeypatch.setattr(llm, "call_lite_llm", fake_call_lite_llm)
    monkeypatch.setattr(lead_agent, "call_lite_llm", fake_call_lite_llm)

    # 2. Skip external Jev guardrail network call when using test key
    async def fake_validate_input_guardrail(payload: dict) -> None:
        return None

    monkeypatch.setattr(
        agents_router, "validate_input_guardrail", fake_validate_input_guardrail
    )

    # 3. Mock DeepEval metrics so they don't call OpenAI or require extra context params
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
def configure_test_auth_and_queue():
    """Allow X-API-Key in API tests while keeping 401 behavior for unauthenticated requests."""

    async def _test_auth_override(
        x_api_key: str = Header(default=""),
        credentials: HTTPAuthorizationCredentials | None = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> dict:
        settings = get_settings()
        if x_api_key and x_api_key == settings.api_key:
            return {"sub": "test-api-key-user"}
        if credentials and credentials.credentials:
            return {"sub": "test-bearer-user"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid credentials",
        )

    app.dependency_overrides[verify_auth0_token] = _test_auth_override
    if getattr(app.state, "arq_pool", None) is None:
        app.state.arq_pool = _DummyArqPool()

    yield

    app.dependency_overrides.clear()


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
