from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from core.schema.message.geo import LocationData
from event.service.location import LocationService
from event.uow.location import LocationUOW


def _service(engine: AsyncEngine) -> LocationService:
    return LocationService(
        LocationUOW(async_sessionmaker(engine, expire_on_commit=False))
    )


async def _row(
    engine: AsyncEngine, location_id: object
) -> tuple[str | None, float | None, float | None]:
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT name, lat, lon FROM location WHERE id = :id"),
                {"id": location_id},
            )
        ).one()
    return row[0], row[1], row[2]


async def test_a_location_keeps_where_it_is(event_engine: AsyncEngine) -> None:
    location_id = uuid4()

    await _service(event_engine).create(
        [LocationData(id=location_id, name="Актовый зал", lat=55.75, lon=37.62)]
    )

    name, lat, lon = await _row(event_engine, location_id)
    assert (name, lat, lon) == (
        "Актовый зал",
        pytest.approx(55.75),
        pytest.approx(37.62),
    )


async def test_a_location_with_nothing_on_a_map_has_no_point(
    event_engine: AsyncEngine,
) -> None:
    location_id = uuid4()

    await _service(event_engine).create(
        [LocationData(id=location_id, name="ул. Пушкина, 10")]
    )

    assert await _row(event_engine, location_id) == ("ул. Пушкина, 10", None, None)


async def test_an_update_moves_the_point_and_can_take_it_away(
    event_engine: AsyncEngine,
) -> None:
    location_id = uuid4()
    service = _service(event_engine)
    await service.create(
        [LocationData(id=location_id, name="Зал", lat=55.75, lon=37.62)]
    )

    await service.update(
        [LocationData(id=location_id, name="Зал", lat=55.8, lon=37.7)]
    )
    moved = await _row(event_engine, location_id)
    await service.update([LocationData(id=location_id, name="Зал")])
    cleared = await _row(event_engine, location_id)

    assert moved == ("Зал", pytest.approx(55.8), pytest.approx(37.7))
    assert cleared == ("Зал", None, None)
