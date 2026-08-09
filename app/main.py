"""NexaPilot AI — FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import agents, health, webhooks
from app.config import get_settings
from app.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("startup", app=settings.app_name, environment=settings.environment)
    yield
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
