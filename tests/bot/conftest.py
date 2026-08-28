import os
from collections.abc import Sequence
from uuid import uuid4

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
                    tgid=tgid,
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
