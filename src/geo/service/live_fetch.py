"""On-demand counterpart to ``geo.bootstrap.run``'s bulk import: when a
search lands near a point outside any bulk-imported city, fetch that small
area from Overpass in the background and cache it, so the DB grows lazily
instead of requiring every city to be bootstrapped up front. Fire-and-forget
by design -- Overpass's latency/reliability profile (see ``OverpassSource``)
is incompatible with blocking a synchronous search response; the first
search near a cold point returns whatever's already local, a later one is
served locally once the fetch lands.
"""

import asyncio
from datetime import UTC, datetime
from logging import getLogger

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings
from geo.bootstrap.coverage import bbox_of_cell, cell_of
from geo.bootstrap.run import _address_id, _import_cell, resolve_city_for_point
from geo.bootstrap.sources import (
    OverpassError,
    OverpassSource,
    resolve_mirror_urls,
)
from geo.schema.point import Point
from geo.uow.address import AddressUOW

logger = getLogger("geo.bootstrap")

_LIVE_BATCH_SIZE = 1000

_inflight: set[tuple[int, int]] = set()
_source: OverpassSource | None = None


def _shared_source() -> OverpassSource:
    global _source
    if _source is None:
        urls = (
            resolve_mirror_urls(settings.GEO_OVERPASS_MIRRORS)
            if settings.GEO_OVERPASS_MIRRORS
            else None
        )
        # attempts comfortably exceeds the mirror count: not every public
        # mirror builds the area index reverse_geocode's is_in query needs --
        # one that doesn't fails every single time (not just transient), so
        # enough attempts to cycle past it and reach one that does matters.
        _source = OverpassSource(
            urls=urls, timeout=25.0, attempts=10, cooldown=10.0
        )
    return _source


async def live_fetch(
    cell: tuple[int, int],
    near: Point,
    *,
    sessionmaker: async_sessionmaker | None = None,
    source: OverpassSource | None = None,
) -> None:
    """Awaitable core, independent of the fire-and-forget wrapper below --
    kept separate so tests can call and await it directly instead of
    sleeping on a background task."""
    src = source or _shared_source()
    try:
        async with AddressUOW(sessionmaker) as uow:
            city_id = await resolve_city_for_point(uow, src, near.lat, near.lon)
        await _import_cell(
            src,
            bbox_of_cell(*cell),
            city_id,
            _LIVE_BATCH_SIZE,
            asyncio.Lock(),
            sessionmaker,
            id_fn=lambda s, h: _address_id(city_id, s, h),
            synced_at=datetime.now(UTC),
        )
    except OverpassError as exc:
        logger.warning("live fetch failed for cell %s: %s", cell, exc)
        return

    async with AddressUOW(sessionmaker) as uow:
        await uow.coverage.upsert_many(
            [
                {
                    "cell_row": cell[0],
                    "cell_col": cell[1],
                    "source": "osm",
                    "fetched_at": datetime.now(UTC),
                }
            ]
        )
        await uow.commit()


async def _guarded_live_fetch(
    cell: tuple[int, int],
    near: Point,
    sessionmaker: async_sessionmaker | None,
    *,
    source: OverpassSource | None = None,
) -> None:
    try:
        async with AddressUOW(sessionmaker) as uow:
            if await uow.coverage.covered(*cell):
                return
        await live_fetch(cell, near, sessionmaker=sessionmaker, source=source)
    finally:
        _inflight.discard(cell)


def schedule_live_fetch(
    near: Point, *, sessionmaker: async_sessionmaker | None = None
) -> None:
    """Fire-and-forget: never awaited by the caller, must not raise."""
    if not settings.GEO_LIVE_FETCH:
        return
    cell = cell_of(near.lat, near.lon)
    if cell in _inflight:
        return
    _inflight.add(cell)
    asyncio.create_task(_guarded_live_fetch(cell, near, sessionmaker))
