from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import login_rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token, utcnow, verify_password
from app.db.session import get_session
from app.models.entities import AdminUser, RefreshToken
from app.schemas.entities import LoginRequest, RefreshRequest, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])


def token_response(user: AdminUser, refresh_token: str, access_token: str) -> TokenPair:
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        user={"id": user.id, "name": user.name, "email": user.email, "role": user.role.value},
    )


@router.post("/login", response_model=TokenPair, dependencies=[Depends(login_rate_limit)])
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    result = await session.execute(select(AdminUser).where(AdminUser.email == str(payload.email).lower()))
    user = result.scalar_one_or_none()
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    family_id = str(uuid4())
    refresh_token, jti, expires_at = create_refresh_token(user.id, family_id)
    session.add(RefreshToken(user_id=user.id, jti=jti, family_id=family_id, expires_at=expires_at))
    await session.commit()
    return token_response(user, refresh_token, create_access_token(user.id, user.role.value))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    try:
        decoded = decode_token(payload.refresh_token, "refresh")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc

    result = await session.execute(select(RefreshToken).where(RefreshToken.jti == decoded["jti"]))
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token desconocido")
    if stored.revoked_at is not None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == stored.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Reutilización de refresh token detectada")

    user = await session.get(AdminUser, stored.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo o inexistente")

    new_refresh, new_jti, expires_at = create_refresh_token(user.id, stored.family_id)
    stored.revoked_at = utcnow()
    stored.replaced_by_jti = new_jti
    session.add(RefreshToken(user_id=user.id, jti=new_jti, family_id=stored.family_id, expires_at=expires_at))
    await session.commit()
    return token_response(user, new_refresh, create_access_token(user.id, user.role.value))


@router.post("/logout")
async def logout(payload: RefreshRequest, session: AsyncSession = Depends(get_session)) -> dict[str, bool]:
    try:
        decoded = decode_token(payload.refresh_token, "refresh")
    except Exception:
        return {"ok": True}
    await session.execute(
        update(RefreshToken).where(RefreshToken.family_id == decoded["family"]).values(revoked_at=utcnow())
    )
    await session.commit()
    return {"ok": True}

