"""NexaPilot AI — FastAPI application factory."""

import os
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import agents, health, webhooks
from app.config import get_settings
from app.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def setup_langsmith_tracing() -> None:
    """Activates LangSmith tracing using application settings."""
    settings = get_settings()
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing).lower()
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        logger.info("langsmith_tracing_initialized", project=settings.langsmith_project)
    else:
        logger.warning("langsmith_api_key_missing_tracing_disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_langsmith_tracing()

    # Initialize ARQ Redis Pool for background workers
    try:
        app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        logger.info("redis_arq_pool_initialized", redis_url=settings.redis_url)
    except Exception as e:
        logger.error("redis_arq_pool_initialization_failed", error=str(e))
        app.state.arq_pool = None

    logger.info("startup", app=settings.app_name, environment=settings.environment)
    yield

    # Close ARQ Redis Pool on shutdown
    if getattr(app.state, "arq_pool", None):
        await app.state.arq_pool.close()
        logger.info("redis_arq_pool_closed")

    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Operations Platform for Automating Business Workflows",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(webhooks.router)

    @app.get("/")
    def root() -> dict:
        return {
            "message": f"{settings.app_name} is running",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


app = create_app()
