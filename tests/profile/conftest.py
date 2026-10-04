import os
from collections.abc import AsyncIterator
from typing import Any

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

_PUBLISHERS = (
    "on_person_created",
    "on_person_updated",
    "on_person_deleted",
)


@pytest.fixture
async def profile_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/profile"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE person, organization, diet, student_degree "
                    "RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()


@pytest.fixture
def profile_sessionmaker(
    profile_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(profile_engine, expire_on_commit=False)


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []

    def recorder(name: str) -> Any:
        async def publish(payload: Any) -> None:
            events.append((name, payload))

        return publish

    for name in _PUBLISHERS:
        monkeypatch.setattr(f"profile.service.person.{name}", recorder(name))
    return events


@pytest.fixture
async def api(
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    published: list[tuple[str, Any]],
) -> AsyncIterator[httpx.AsyncClient]:
    from profile.app.app import app

    async with api_client(app, profile_sessionmaker) as client:
        yield client
