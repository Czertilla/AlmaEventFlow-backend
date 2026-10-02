import os
from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_BOT_TABLES = (
    'tg."user"',
    '"user"',
)


def _bot_url() -> str:
    return (
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/bot"
    )


@pytest.fixture
async def bot_engine(test_database):
    """Function-scoped engine on the migrated bot database. Created and
    disposed inside the test's event loop; every bot table is truncated on
    teardown for per-test isolation."""
    engine = create_async_engine(_bot_url())
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE "
                    + ", ".join(_BOT_TABLES)
                    + " RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()


@pytest.fixture(autouse=True)
async def link_code(request):
    from core.dependencies.redis import redis
    from core.utils.telegram_link import TELEGRAM_LINK_REDIS_PREFIX

    issued: list[str] = []

    async def issue(person_id: UUID | None = None, *, value: str | None = None):
        code = uuid4().hex
        stored = value if value is not None else str(person_id)
        await redis.set(f"{TELEGRAM_LINK_REDIS_PREFIX}{code}", stored, ex=600)
        issued.append(code)
        return code

    yield issue
    if issued:
        await redis.delete(*[f"{TELEGRAM_LINK_REDIS_PREFIX}{c}" for c in issued])
    await redis.connection_pool.disconnect()


@pytest.fixture(autouse=True)
def offline_aef_client(monkeypatch):
    async def no_client(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "bot.tg.service.account_link.register_notify_client", no_client
    )
    monkeypatch.setattr(
        "bot.tg.service.account_link.register_oauth_link", no_client
    )


@pytest.fixture
def bot_sessionmaker(bot_engine):
    return async_sessionmaker(bot_engine, expire_on_commit=False)


@pytest.fixture
def bot_seed(bot_sessionmaker):
    return _BotSeeder(bot_sessionmaker)


class _BotSeeder:
    def __init__(self, sessionmaker_) -> None:
        self._sessionmaker = sessionmaker_

    async def tg_user(self, tgid: int, *, username: str | None = None):
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

    async def count(self, model) -> int:
        async with self._sessionmaker() as session:
            return (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

    async def all(self, model) -> Sequence:
        async with self._sessionmaker() as session:
            return (await session.execute(select(model))).scalars().all()

    @staticmethod
    def new_person_id():
        return uuid4()
