from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, has_permission
from app.core.security import decode_token
from app.db.redis import redis_client
from app.db.session import get_session
from app.models.entities import AdminUser


async def rate_limit(request: Request, key_prefix: str, limit: int, window_seconds: int) -> None:
    if redis_client is None:
        return
    client = request.client.host if request.client else "unknown"
    key = f"rl:{key_prefix}:{client}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window_seconds)
    if current > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos. Intenta más tarde.")


async def login_rate_limit(request: Request) -> None:
    await rate_limit(request, "auth-login", 8, 60)


async def contact_rate_limit(request: Request) -> None:
    await rate_limit(request, "public-contact", 5, 300)


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> AdminUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token, "access")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc
    user = await session.get(AdminUser, payload["sub"])
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")
    return user


def require_permission(permission: Permission) -> Callable:
    async def dependency(user: AdminUser = Depends(get_current_user)) -> AdminUser:
        if not has_permission(user.role.value, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso insuficiente")
        return user

    return dependency
