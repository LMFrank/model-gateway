from fastapi import Request


async def require_client_auth(request: Request) -> None:
    pass


async def require_admin_auth(request: Request) -> None:
    pass
