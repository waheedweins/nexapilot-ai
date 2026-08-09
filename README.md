# NexaPilot AI

**AI Operations Platform for Automating Business Workflows**

A production-style multi-agent backend: FastAPI + LangGraph orchestrator + async
Postgres persistence + Dockerized deployment + GitHub Actions CI/CD that publishes
container images to GitHub Packages (ghcr.io).

```
User → FastAPI → LangGraph Orchestrator → { Research | Lead | Ops } Agent → Postgres → n8n → Gmail / Slack / APIs
```

## Stack

- **FastAPI** — async web framework, versioned REST API
- **LangGraph** — agent orchestration graph (Research, Lead, Ops agents; routed by the orchestrator)
- **SQLAlchemy 2.0 (async) + Alembic** — Postgres persistence and migrations
- **Pydantic Settings** — typed, validated configuration from environment variables
- **structlog** — structured JSON logging
- **pytest + httpx** — automated tests against the ASGI app
- **ruff** — linting
- **Docker (multi-stage)** — production image
- **GitHub Actions** — lint → test → build → push to `ghcr.io/<owner>/nexapilot-ai`

## Project layout

```
nexapilot-ai/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── config.py             # Settings (env-driven)
│   ├── logging_config.py
│   ├── api/
│   │   ├── deps.py           # shared dependencies (DB session, API-key auth)
│   │   └── routers/
│   │       ├── health.py
│   │       ├── agents.py     # /v1/agents/* — invoke the orchestrator
│   │       └── webhooks.py   # inbound n8n / provider webhooks
│   ├── graph/
│   │   └── orchestrator.py   # LangGraph StateGraph wiring the 3 agents
│   ├── agents/
│   │   ├── base.py
│   │   ├── research_agent.py
│   │   ├── lead_agent.py
│   │   └── ops_agent.py
│   ├── tools/
│   │   └── web_search.py     # pluggable search tool (Tavily-compatible interface)
│   ├── memory/
│   │   └── session_store.py  # conversation/session state persisted to Postgres
│   └── database/
│       ├── session.py        # async engine/session factory
│       └── models.py         # ORM models
├── alembic/                  # migrations
├── tests/
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

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Run migrations (inside the app container, or locally against the compose Postgres):

```bash
alembic upgrade head
```

Run tests:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

## API

All business endpoints are versioned under `/v1` and require an `X-API-Key` header
matching `API_KEY` in the environment (see `app/api/deps.py`).

- `GET /health` — liveness/readiness, no auth
- `POST /v1/agents/invoke` — run the orchestrator graph for a given task
  ```json
  {
    "task_type": "lead_qualification",
    "session_id": "optional-session-id",
    "payload": { "company_name": "Acme Corp", "website": "https://acme.com" }
  }
  ```
- `POST /v1/webhooks/n8n` — inbound webhook receiver for n8n workflows

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push/PR to `main`:

1. **lint** — `ruff check .`
2. **test** — `pytest` against a Postgres service container
3. **build-and-push** (main branch only) — builds the Docker image and pushes it to
   **GitHub Packages** (`ghcr.io/<owner>/nexapilot-ai`) tagged with the commit SHA and
   `latest`, using the repo's built-in `GITHUB_TOKEN` (no extra secrets needed).

To deploy elsewhere (ECS, a VM, etc.), pull the published image:

```bash
docker pull ghcr.io/<owner>/nexapilot-ai:latest
```

## Roadmap

- Phase 3: long-term knowledge base / RAG for the Research agent
- Phase 5: n8n workflow wiring for Gmail/Slack/CRM actions
- Phase 6: human-in-the-loop approval gate before any external "write" action
- Phase 7: AWS deployment + LangSmith tracing
