from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
async def sessionmaker_():
    """In-memory SQLite session factory with the notify schema created. A
    StaticPool keeps a single shared connection so the schema persists across
    sessions opened by the unit-of-work."""
    from core.database.sqlalchemy.core import Base
    import notify.models  # noqa: F401

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


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

    async def count(self, model) -> int:
        async with self._sessionmaker() as session:
            return (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()

    async def all(self, model) -> Sequence:
        async with self._sessionmaker() as session:
            return (await session.execute(select(model))).scalars().all()
