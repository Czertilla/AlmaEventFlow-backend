import os
from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_NOTIFY_TABLES = (
    "notification_delivery",
    "notification_recipient",
    "outbox_event",
    "notification",
    "client",
    "preference",
    "account",
)


def _notify_url() -> str:
    return (
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/notify"
    )


@pytest.fixture
async def notify_engine(test_database):
    """Function-scoped engine on the migrated notify database. Created and
    disposed inside the test's event loop (asyncpg dislikes cross-loop reuse);
    every notify table is truncated on teardown for per-test isolation."""
    engine = create_async_engine(_notify_url())
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE "
                    + ", ".join(_NOTIFY_TABLES)
                    + " RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()


@pytest.fixture
def sessionmaker_(notify_engine):
    return async_sessionmaker(notify_engine, expire_on_commit=False)


@pytest.fixture
def seed(sessionmaker_):
    return _Seeder(sessionmaker_)


class _Seeder:
    def __init__(self, sessionmaker_) -> None:
        self._sessionmaker = sessionmaker_

    async def accounts(self, count: int) -> list[UUID]:
        from notify.models.account import AccountORM

        ids = [uuid4() for _ in range(count)]
        async with self._sessionmaker() as session:
            session.add_all(
                AccountORM(
                    id=user_id,
                    email=f"user{i}@example.com",
                    is_verified=True,
                )
                for i, user_id in enumerate(ids)
            )
            await session.commit()
        return ids

    async def accounts_with_persons(
        self, count: int
    ) -> list[tuple[UUID, UUID]]:
        from notify.models.account import AccountORM

        pairs = [(uuid4(), uuid4()) for _ in range(count)]
        async with self._sessionmaker() as session:
            session.add_all(
                AccountORM(
                    id=user_id,
                    email=f"person{i}@example.com",
                    is_verified=True,
                    person_id=person_id,
                )
                for i, (user_id, person_id) in enumerate(pairs)
            )
            await session.commit()
        return pairs

    async def count(self, model) -> int:
        async with self._sessionmaker() as session:
            return (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

    async def all(self, model) -> Sequence:
        async with self._sessionmaker() as session:
            return (await session.execute(select(model))).scalars().all()
