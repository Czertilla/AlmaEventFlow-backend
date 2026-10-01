import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.schema.message.geo import LocationData, LocationDelete
from event.service.location import LocationService
from event.uow.location import LocationUOW


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
            await conn.execute(text("TRUNCATE event, location CASCADE"))
        await engine.dispose()


async def test_deleting_a_location_detaches_events_instead_of_failing(event_engine):
    location_id, event_id = uuid4(), uuid4()
    service = LocationService(
        LocationUOW(async_sessionmaker(event_engine, expire_on_commit=False))
    )
    await service.create([LocationData(id=location_id, name=None)])
    async with event_engine.begin() as conn:
        await conn.execute(text("INSERT INTO event_status (id, name) VALUES (1, 's') ON CONFLICT DO NOTHING"))
        await conn.execute(
            text(
                "INSERT INTO event (id, name, location_id, status_id, created_at) "
                "VALUES (:id, 'e', :loc, 1, now())"
            ),
            {"id": event_id, "loc": location_id},
        )

    await service.delete([LocationDelete(id=location_id)])

    async with event_engine.connect() as conn:
        assert (
            await conn.execute(text("SELECT location_id FROM event WHERE id = :id"), {"id": event_id})
        ).scalar_one() is None
        assert (await conn.execute(text("SELECT count(*) FROM location"))).scalar_one() == 0
