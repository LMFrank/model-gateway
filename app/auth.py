from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings


def _get_settings(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "").strip()
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip() or None


def _require_token(request: Request, expected_token: str, realm: str) -> None:
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{realm} token is not configured",
        )

    token = _extract_bearer_token(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not hmac.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid token",
        )


async def require_client_auth(request: Request) -> None:
    settings = _get_settings(request)
    _require_token(request, settings.gateway_client_token, "client")


async def require_admin_auth(request: Request) -> None:
    settings = _get_settings(request)
    _require_token(request, settings.gateway_admin_token, "admin")
