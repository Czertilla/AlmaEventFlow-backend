from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from event.service import notification


async def _seed(engine: AsyncEngine, *, lat: float | None, lon: float | None) -> UUID:
    collective_id, event_id, location_id = uuid4(), uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type) "
                "VALUES (:id, 'Choir', 'collective')"
            ),
            {"id": collective_id},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective_id},
        )
        await conn.execute(
            text(
                "INSERT INTO location (id, name, lat, lon) "
                "VALUES (:id, 'Актовый зал', :lat, :lon)"
            ),
            {"id": location_id, "lat": lat, "lon": lon},
        )
        await conn.execute(
            text(
                "INSERT INTO event (id, name, status_id, location_id, created_at) "
                "VALUES (:id, 'Concert', "
                "(SELECT id FROM event_status WHERE name = 'active'), :loc, now())"
            ),
            {"id": event_id, "loc": location_id},
        )
        await conn.execute(
            text(
                "INSERT INTO participation (id, collective_id, event_id, created_at) "
                "VALUES (:id, :collective, :event, now())"
            ),
            {"id": uuid4(), "collective": collective_id, "event": event_id},
        )
    return event_id


async def _announced(
    event_engine: AsyncEngine,
    event_sessionmaker: async_sessionmaker[AsyncSession],
    lat: float | None,
    lon: float | None,
):
    event_id = await _seed(event_engine, lat=lat, lon=lon)
    async with event_sessionmaker() as session:
        rows = await notification._resolve_collective_targets(  # pyright: ignore[reportPrivateUsage]
            session, event_ids=[event_id]
        )
    (request,) = notification._build_announcements(rows, {})  # pyright: ignore[reportPrivateUsage]
    return request


async def test_the_announcement_carries_where_the_location_is(
    event_engine: AsyncEngine,
    event_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    request = await _announced(event_engine, event_sessionmaker, 55.75, 37.62)

    assert request.location == "Актовый зал"
    assert (request.location_lat, request.location_lon) == (
        pytest.approx(55.75),
        pytest.approx(37.62),
    )


async def test_a_location_with_no_point_announces_the_text_only(
    event_engine: AsyncEngine,
    event_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    request = await _announced(event_engine, event_sessionmaker, None, None)

    assert request.location == "Актовый зал"
    assert (request.location_lat, request.location_lon) == (None, None)
