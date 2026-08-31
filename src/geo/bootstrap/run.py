"""One-off/periodically-rerun data job, not request-path code:

    python -m geo.bootstrap.run --city moscow

Idempotent -- re-running upserts (keyed on each address's deterministic
uuid5, see ``sources.RawAddress.id``) instead of duplicating. Chunks the
target bbox into a grid so one Overpass request stays small and a failure
partway through only costs the current cell, not the whole run.
"""

import argparse
import asyncio
from logging import basicConfig, getLogger

from sqlalchemy import select

from geo.bootstrap.sources import BBox, OverpassSource, chunk_bbox
from geo.models.city import CityORM
from geo.models.country import CountryORM
from geo.models.region import RegionORM
from geo.uow.address import AddressUOW

logger = getLogger("geo.bootstrap")

# Rough box around Moscow within the MKAD plus a margin -- not a precise
# administrative boundary, just wide enough to catch the city.
CITY_BBOXES: dict[str, BBox] = {
    "moscow": (55.49, 37.32, 55.96, 37.97),
}

MOSCOW_SEED = {
    "country": {"name": "Россия", "code": "RU"},
    "region": {"name": "Москва"},
    "city": {"name": "Москва"},
}


async def _seed_moscow_hierarchy(uow: AddressUOW) -> int:
    """Country -> Region -> City is 3 stable rows for Moscow specifically --
    not worth fetching from anywhere, hand-seeded once. Returns the city_id
    addresses attach to."""
    session = uow.session

    country = (
        await session.execute(
            select(CountryORM).where(
                CountryORM.name == MOSCOW_SEED["country"]["name"]
            )
        )
    ).scalar_one_or_none()
    if country is None:
        country = CountryORM(**MOSCOW_SEED["country"])
        session.add(country)
        await session.flush()

    region = (
        await session.execute(
            select(RegionORM).where(
                RegionORM.country_id == country.id,
                RegionORM.name == MOSCOW_SEED["region"]["name"],
            )
        )
    ).scalar_one_or_none()
    if region is None:
        region = RegionORM(country_id=country.id, **MOSCOW_SEED["region"])
        session.add(region)
        await session.flush()

    city = (
        await session.execute(
            select(CityORM).where(
                CityORM.region_id == region.id,
                CityORM.name == MOSCOW_SEED["city"]["name"],
            )
        )
    ).scalar_one_or_none()
    if city is None:
        city = CityORM(region_id=region.id, **MOSCOW_SEED["city"])
        session.add(city)
        await session.flush()

    await session.commit()
    return city.id


async def _run(args: argparse.Namespace) -> None:
    bbox = (
        (args.min_lat, args.min_lon, args.max_lat, args.max_lon)
        if args.min_lat is not None
        else CITY_BBOXES[args.city]
    )
    source = OverpassSource(request_delay=args.delay)

    async with AddressUOW() as uow:
        city_id = await _seed_moscow_hierarchy(uow)
    logger.info(
        "city_id=%s ready, bbox=%s, grid=%dx%d",
        city_id,
        bbox,
        args.grid,
        args.grid,
    )

    cells = list(chunk_bbox(bbox, grid=args.grid))
    total_upserted = 0
    for i, cell in enumerate(cells, start=1):
        logger.info("cell %d/%d %s", i, len(cells), cell)
        batch = []
        async for raw in source.fetch(cell):
            batch.append(
                {
                    "id": raw.id,
                    "city_id": city_id,
                    "name": raw.name,
                    "spot": {"lat": raw.lat, "lon": raw.lon},
                    "parsed": {"house": raw.housenumber, "street": raw.street},
                }
            )
            if len(batch) >= args.batch_size:
                total_upserted += await _flush(batch)
                batch = []
        if batch:
            total_upserted += await _flush(batch)

    logger.info("done -- %d addresses upserted", total_upserted)


async def _flush(batch: list[dict]) -> int:
    async with AddressUOW() as uow:
        await uow.addresses.upsert_many(batch)
        await uow.commit()
    return len(batch)


def main() -> None:
    basicConfig(level="INFO", format="%(asctime)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", choices=sorted(CITY_BBOXES), default="moscow")
    parser.add_argument("--min-lat", type=float, default=None)
    parser.add_argument("--min-lon", type=float, default=None)
    parser.add_argument("--max-lat", type=float, default=None)
    parser.add_argument("--max-lon", type=float, default=None)
    parser.add_argument(
        "--grid",
        type=int,
        default=8,
        help="split the bbox into grid x grid Overpass requests",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="seconds to wait before each Overpass request",
    )
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
