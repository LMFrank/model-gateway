from fastapi import HTTPException, Request, status

from app.config import get_settings


class AuthError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)



def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("missing authorization header")

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthError("invalid authorization header")

    return parts[1].strip()


async def require_client_auth(request: Request) -> None:
    settings = get_settings()
    if not settings.gateway_client_token:
        raise HTTPException(status_code=500, detail="GATEWAY_CLIENT_TOKEN is not configured")

    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token != settings.gateway_client_token:
        raise AuthError("invalid client token")


async def require_admin_auth(request: Request) -> None:
    settings = get_settings()
    if not settings.gateway_admin_token:
        raise HTTPException(status_code=500, detail="GATEWAY_ADMIN_TOKEN is not configured")

    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token != settings.gateway_admin_token:
        raise AuthError("invalid admin token")
