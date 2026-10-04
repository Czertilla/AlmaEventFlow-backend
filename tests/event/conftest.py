import os
from collections.abc import AsyncIterator
from uuid import UUID

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
async def event_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/event"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE event, location, organization CASCADE"))
        await engine.dispose()


@pytest.fixture
def event_sessionmaker(
    event_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(event_engine, expire_on_commit=False)


@pytest.fixture
def notices(monkeypatch: pytest.MonkeyPatch) -> list[UUID]:
    sent: list[UUID] = []

    async def notify_targets(uow: object, *, event_ids: list[UUID]) -> None:
        sent.extend(event_ids)

    async def nothing(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("event.service.event.notify_event_targets", notify_targets)
    monkeypatch.setattr("event.service.event.notify_collective_chats", nothing)
    return sent


@pytest.fixture
async def api(
    event_sessionmaker: async_sessionmaker[AsyncSession],
    notices: list[UUID],
) -> AsyncIterator[httpx.AsyncClient]:
    from event.app.app import app

    async with api_client(app, event_sessionmaker) as client:
        yield client
