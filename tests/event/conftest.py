import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def event_engine(test_database):
    engine = create_async_engine(
        f"postgresql+asyncpg://{os.environ['DB_USER']}:{os.environ['DB_PASS']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/event"
    )
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("TRUNCATE event, location, organization CASCADE")
            )
        await engine.dispose()


@pytest.fixture
def event_sessionmaker(event_engine):
    return async_sessionmaker(event_engine, expire_on_commit=False)
