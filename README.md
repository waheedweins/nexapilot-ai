```markdown
# NexaPilot AI

**AI Operations Platform for Automating Business Workflows**

A production-style multi-agent backend featuring FastAPI, a LangGraph orchestrator, async PostgreSQL persistence, Jev security and intent gateways, prompt caching, PII redaction, LangSmith tracing, and Dockerized CI/CD publishing to GitHub Packages (`ghcr.io`).


```

User → Auth0 / FastAPI (Jev Input Guardrail) → Intent Router (Cache vs Live) → LangGraph Orchestrator → { Research | Lead | Ops } Agent → PII Sanitizer → Postgres → n8n → Gmail / Slack / APIs

```

## Stack & Advanced Architecture

- **FastAPI** — async web framework, versioned REST API (`/v1`)
- **LangGraph** — multi-agent orchestration graph (Research, Lead, Ops agents)
- **SQLAlchemy 2.0 (async) + Alembic** — Postgres persistence, session history, and prompt caching tables
- **Auth0 OIDC** — RS256 JWT access token verification
- **Jev (TypeSafe SDK)** — semantic prompt injection guardrails & intelligent execution mode routing (`live_research` vs `cached_operations`)
- **Centralized LLM Gateway** — Google Gemini Flash with automatic LangChain `.with_fallbacks()` resilience
- **Output Guardrails** — recursive PII redaction (masking emails, phones, keys, and DB URIs)
- **LangSmith** — native telemetry and multi-agent execution tracing
- **structlog** — structured JSON logging
- **pytest + httpx** — automated test suite against async ASGI app
- **Docker (multi-stage)** — production container image
- **GitHub Actions** — lint → test → build → push to `ghcr.io/<owner>/nexapilot-ai`

## Project layout


```

nexapilot-ai/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py            # Typed environment configuration (Pydantic Settings)
│   ├── logging_config.py    # Structured JSON / console logger
│   ├── api/
│   │   ├── deps.py          # Shared dependencies (DB session, Auth0 JWT verification)
│   │   └── routers/
│   │       ├── health.py    # Liveness & readiness probes
│   │       ├── agents.py    # /v1/agents/* — invoke orchestrator & retrieve sessions
│   │       └── webhooks.py  # Secured inbound n8n webhook receiver
│   ├── core/
│   │   ├── llm.py           # Centralized LLM client wrapper with automatic fallbacks
│   │   ├── cache.py         # PostgreSQL prompt caching layer (SHA-256 signatures)
│   │   ├── guardrails.py    # Jev semantic prompt-injection input firewall
│   │   ├── lead_intent.py   # Jev intent router (cache vs live research classification)
│   │   └── output_guardrails.py # Recursive PII redaction and sanitization
│   ├── graph/
│   │   └── orchestrator.py  # LangGraph StateGraph wiring the 3 agents
│   ├── agents/
│   │   ├── base.py          # Shared graph state TypedDict & protocol
│   │   ├── research_agent.py# External information gathering (Tavily web search)
│   │   ├── lead_agent.py    # B2B lead scoring & qualification (Gemini + fallbacks)
│   │   └── ops_agent.py     # Automated execution & Human-in-the-Loop safety gate
│   ├── tools/
│   │   └── web_search.py    # Pluggable search tool (Tavily-compatible interface)
│   ├── memory/
│   │   └── session_store.py # Session state & message history persisted to Postgres
│   └── database/
│       ├── session.py       # Async SQLAlchemy engine & session factory
│       └── models.py        # ORM models (AgentSession, SessionMessage, Lead, PromptCache)
├── alembic/                 # Database migrations
├── tests/                   # Automated unit & API test suite
├── .github/workflows/ci-cd.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── pyproject.toml

```

## Local development

```bash
cp .env.example .env
docker compose up --build

```

* API: http://localhost:8000
* Docs: http://localhost:8000/docs
* Health: http://localhost:8000/health

Run migrations (inside the app container, or locally against PostgreSQL):

```bash
alembic upgrade head

```

Run tests:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v

```

## API Endpoints

All business endpoints are versioned under `/v1` and protected by **Auth0 OIDC JWT Bearer tokens** (verified via JWKS).

* `GET /health` — liveness probe, no auth
* `GET /health/ready` — readiness probe verifying database reachability
* `POST /v1/agents/invoke` — run the orchestrator graph with guardrails, intent routing, and caching
```json
{
  "task_type": "lead_qualification",
  "session_id": "optional-session-id",
  "payload": { "company_name": "Acme Corp", "website": "[https://acme.com](https://acme.com)" }
}

```


* `GET /v1/agents/sessions/{session_id}` — retrieve past session state and history
* `POST /v1/webhooks/n8n` — inbound webhook receiver for self-hosted n8n workflows (secured via HMAC signature)

## CI/CD Pipeline

`.github/workflows/ci-cd.yml` runs on every push/PR to `main`:

1. **lint** — `ruff check .`
2. **test** — runs `pytest` against a live Postgres service container with Alembic migrations
3. **build-and-push** (main branch only) — builds multi-stage Docker image and pushes it to **GitHub Packages** (`ghcr.io/<owner>/nexapilot-ai`) tagged with commit SHA and `latest`.

To pull the production image:

```bash
docker pull ghcr.io/<owner>/nexapilot-ai:latest

```

## Roadmap & Status

* [x] Phase 1: FastAPI, Async SQLAlchemy, Alembic, Docker, CI/CD pipeline
* [x] Phase 2: LangGraph multi-agent orchestrator (Research, Lead, Ops agents)
* [x] Phase 3: PostgreSQL session persistence & prompt caching layer
* [x] Phase 4: Auth0 OIDC security, Jev input guardrails, and PII output redaction
* [x] Phase 5: Centralized LLM gateway with LangChain `.with_fallbacks()` resilience
* [x] Phase 6: Human-in-the-Loop (HITL) safety allowlist and n8n webhook dispatcher
* [ ] Phase 7: Qdrant vector store RAG integration for research policies & LangSmith telemetry dashboard

```

```
