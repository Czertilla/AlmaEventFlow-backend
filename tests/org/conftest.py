import os
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from support.http import api_client


@pytest.fixture
async def org_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/org"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE organization, address, person CASCADE"))
        await engine.dispose()


@pytest.fixture
def org_sessionmaker(
    org_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(org_engine, expire_on_commit=False)


@pytest.fixture
async def api(
    org_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    from org.app.app import app

    async def publish(payload: object) -> None:
        return None

    for module in ("organization", "university", "faculty", "collective"):
        for kind in ("created", "updated", "deleted"):
            monkeypatch.setattr(f"org.service.{module}.on_organization_{kind}", publish)
    async with api_client(app, org_sessionmaker) as client:
        yield client
