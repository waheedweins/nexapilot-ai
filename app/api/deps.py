"""Shared FastAPI dependencies: API-key auth and DB session re-export."""

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.database.session import get_db  # noqa: F401  (re-exported for routers)


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
