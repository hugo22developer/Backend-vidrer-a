from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def utcnow() -> datetime:
    return datetime.now(UTC)


def create_access_token(subject: str, role: str) -> str:
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iss": settings.jwt_issuer,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_refresh_token(subject: str, family_id: str, jti: str | None = None) -> tuple[str, str, datetime]:
    now = utcnow()
    token_jti = jti or str(uuid4())
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "type": "refresh",
        "family": family_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_jti,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256"), token_jti, expires_at


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"], issuer=settings.jwt_issuer)
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload

