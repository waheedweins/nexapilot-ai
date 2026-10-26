"""Shared FastAPI dependencies: Auth0 OIDC verification, API-key auth, and DB session re-export."""

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import get_settings
from app.database.session import get_db  # noqa: F401 (re-exported for routers)

# HTTPBearer extracts the Authorization: Bearer <token> header automatically
security = HTTPBearer(auto_error=True)


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Legacy API-key authentication (retained for fallback or service-to-service calls)."""
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


async def verify_auth0_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """NEW: Validates Auth0 RS256 JWT Access Tokens by querying the Auth0 JWKS endpoint."""
    settings = get_settings()
    token = credentials.credentials

    try:
        # Fetch the JSON Web Key Set (JWKS) from your Auth0 tenant
        async with httpx.AsyncClient() as client:
            jwks_res = await client.get(
                f"https://{settings.auth0_domain}/.well-known/jwks.json"
            )
            jwks = jwks_res.json()

        # Match the token's key ID (kid) with the public key from Auth0
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e"),
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate JWKS key.",
            )

        # Decode, verify signature, audience, and issuer
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload  # Returns user claims (sub, email, roles, etc.)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token credentials: {str(e)}",
        )
