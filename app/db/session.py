from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse, urlencode, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _build_engine(url: str):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    sslmode = params.pop("sslmode", None)
    connect_args = {}
    if sslmode and sslmode[0] == "require":
        connect_args["ssl"] = True
    clean_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))
    return create_async_engine(clean_url, pool_pre_ping=True, connect_args=connect_args)


engine = _build_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

