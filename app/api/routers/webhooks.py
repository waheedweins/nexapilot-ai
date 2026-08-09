import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import get_settings
from app.logging_config import get_logger

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/n8n")
async def n8n_webhook(request: Request, x_webhook_secret: str = Header(default="")) -> dict:
    """Inbound webhook for n8n workflows (e.g. Gmail/Slack triggers).

    Verified with a shared secret rather than the API key, since n8n is a
    separate trust boundary from interactive API clients.
    """
    settings = get_settings()
    if not hmac.compare_digest(x_webhook_secret, settings.n8n_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    body = await request.json()
    logger.info("n8n_webhook_received", keys=list(body.keys()))

    # TODO(Phase 5): route `body` into the orchestrator or a dedicated
    # ingestion handler once concrete n8n workflows are defined.
    return {"status": "received"}
