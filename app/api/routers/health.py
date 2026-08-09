from fastapi import APIRouter
from sqlalchemy import text

from app.database.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe. No auth, no dependencies — must always respond fast."""
    return {"status": "healthy"}


@router.get("/health/ready")
async def readiness_check() -> dict:
    """Readiness probe — verifies the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {"status": "ready" if db_ok else "degraded", "database": db_ok}
