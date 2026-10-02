import os
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_BOT_TABLES = (
    'tg."user"',
    '"user"',
)

LinkCodeIssuer = Callable[..., Awaitable[str]]


def _bot_url() -> str:
    return (
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/bot"
    )


@pytest.fixture
async def bot_engine(test_database: None) -> AsyncIterator[AsyncEngine]:
    """Function-scoped engine on the migrated bot database. Created and
    disposed inside the test's event loop; every bot table is truncated on
    teardown for per-test isolation."""
    engine = create_async_engine(_bot_url())
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("TRUNCATE " + ", ".join(_BOT_TABLES) + " RESTART IDENTITY CASCADE")
            )
        await engine.dispose()


@pytest.fixture(autouse=True)
async def link_code() -> AsyncIterator[LinkCodeIssuer]:
    from core.dependencies.redis import redis
    from core.utils.telegram_link import TELEGRAM_LINK_REDIS_PREFIX

    issued: list[str] = []

    async def issue(person_id: UUID | None = None, *, value: str | None = None) -> str:
        code = uuid4().hex
        stored = value if value is not None else str(person_id)
        await redis.set(f"{TELEGRAM_LINK_REDIS_PREFIX}{code}", stored, ex=600)
        issued.append(code)
        return code

    yield issue
    if issued:
        await redis.delete(*[f"{TELEGRAM_LINK_REDIS_PREFIX}{code}" for code in issued])
    await redis.connection_pool.disconnect()


@pytest.fixture(autouse=True)
def offline_aef_client(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_client(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("bot.tg.service.account_link.register_notify_client", no_client)
    monkeypatch.setattr("bot.tg.service.account_link.register_oauth_link", no_client)


@pytest.fixture
def bot_sessionmaker(
    bot_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bot_engine, expire_on_commit=False)


@pytest.fixture
def bot_seed(
    bot_sessionmaker: async_sessionmaker[AsyncSession],
) -> "_BotSeeder":
    return _BotSeeder(bot_sessionmaker)


class _BotSeeder:
    def __init__(self, sessionmaker_: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker_

    async def tg_user(self, tgid: int, *, username: str | None = None) -> int:
        from bot.tg.model.user import TGUserORM

        async with self._sessionmaker() as session:
            session.add(
                TGUserORM(
                    id=tgid,
                    is_bot=False,
                    first_name=f"Test{tgid}",
                    username=username or f"test{tgid}",
                )
            )
            await session.commit()
        return tgid

    async def count(self, model: type[Any]) -> int:
        async with self._sessionmaker() as session:
            return (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

    async def all(self, model: type[Any]) -> Sequence[Any]:
        async with self._sessionmaker() as session:
            return (await session.execute(select(model))).scalars().all()

    @staticmethod
    def new_person_id() -> UUID:
        return uuid4()
