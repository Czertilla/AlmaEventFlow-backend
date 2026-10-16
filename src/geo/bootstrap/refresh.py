"""Periodically-rerun data job, not request-path code:

    python -m geo.bootstrap.refresh
    python -m geo.bootstrap.refresh --older-than-days 14 --limit 500 --prune

Rows that search stored from Photon (``source="photon"``) are never rewritten
by a later search that does not see them, so they age. This asks the geocoder
for each one again: a row that is found keeps its id and takes the current
name, point and a new ``synced_at``; one that is not found is only reported,
and with ``--prune`` deleted once it has gone ``--prune-after-days`` without
being seen (a miss is not proof, a row seen again within that time is kept).
A row that has a twin from another source (the same street and house within
``DUPLICATE_RADIUS_M``, filed under a differently named city) is a duplicate
and goes with ``--prune`` too. A row a location points at is never deleted.

Only rows confirmed before the geocoder's own data was built are asked: when
the Photon instance reports its import date (``/status``) the newer rows
cannot have changed since.
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from logging import basicConfig, getLogger
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config.settings import settings
from geo.dto.point import PointDTO
from geo.geocoder.base import DatedGeocoder, GeocodedAddress, Geocoder, GeocoderError
from geo.geocoder.photon import PhotonGeocoder
from geo.identity import DUPLICATE_RADIUS_M, address_key, meters_between
from geo.repository.address import Neighbour, Stale
from geo.uow.address import AddressUOW

logger = getLogger("geo.bootstrap")

REFRESH_RADIUS_M = 1000.0
"""How far a re-found address may have moved and still be the same one."""

PAGE_SIZE = 100
SEARCH_LIMIT = 5
MAX_CONSECUTIVE_ERRORS = 3


@dataclass
class Report:
    checked: int = 0
    confirmed: int = 0
    missing: int = 0
    duplicates: int = 0
    pruned: int = 0
    errors: int = 0
    aborted: bool = False
    gone: list[UUID] = field(default_factory=lambda: [])


def _twin(row: Stale, around: list[Neighbour], source: str) -> bool:
    return any(
        other.id != row.id
        and other.source != source
        and other.key == row.key
        and meters_between(row.lat, row.lon, other.lat, other.lon) <= DUPLICATE_RADIUS_M
        for other in around
    )


def _found_again(row: Stale, found: list[GeocodedAddress]) -> GeocodedAddress | None:
    best: GeocodedAddress | None = None
    nearest = REFRESH_RADIUS_M
    for item in found:
        if address_key(item.street, item.housenumber) != row.key:
            continue
        meters = meters_between(row.lat, row.lon, item.lat, item.lon)
        if meters <= nearest:
            best, nearest = item, meters
    return best


async def _cutoff(geocoder: Geocoder, older_than: timedelta, now: datetime) -> datetime:
    cutoff = now - older_than
    if isinstance(geocoder, DatedGeocoder):
        try:
            imported = await geocoder.imported_at()
        except (GeocoderError, TimeoutError) as exc:
            logger.warning("the import date of %s is unknown: %s", geocoder.name, exc)
            return cutoff
        if imported is not None:
            logger.info("%s data was built %s", geocoder.name, imported.isoformat())
            return min(cutoff, imported)
    return cutoff


async def refresh(
    geocoder: Geocoder,
    *,
    sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    source: str = "photon",
    older_than: timedelta = timedelta(days=30),
    limit: int = 500,
    prune: bool = False,
    prune_after: timedelta = timedelta(days=90),
    delay: float = 0.0,
    now: datetime | None = None,
) -> Report:
    now = now or datetime.now(UTC)
    cutoff = await _cutoff(geocoder, older_than, now)
    report = Report()
    cursor: tuple[datetime, UUID] | None = None
    streak = 0

    while report.checked + report.duplicates < limit and not report.aborted:
        async with AddressUOW(sessionmaker) as uow:
            page = await uow.addresses.stale_found(
                source,
                cutoff,
                min(PAGE_SIZE, limit - report.checked - report.duplicates),
                cursor,
            )
            around = await uow.addresses.neighbours(
                [(row.lat, row.lon) for row in page], DUPLICATE_RADIUS_M
            )
        if not page:
            break
        cursor = (page[-1].synced_at, page[-1].id)

        confirmed: list[dict[str, Any]] = []
        for row in page:
            if _twin(row, around, source):
                report.duplicates += 1
                if prune and not row.attached:
                    report.gone.append(row.id)
                continue
            try:
                found = await geocoder.search(
                    f"{row.name}, {row.city}",
                    near=PointDTO(lat=row.lat, lon=row.lon),
                    limit=SEARCH_LIMIT,
                )
            except (GeocoderError, TimeoutError) as exc:
                report.errors += 1
                streak += 1
                logger.warning("%s: %s", row.name, exc)
                if streak >= MAX_CONSECUTIVE_ERRORS:
                    report.aborted = True
                    break
                continue
            streak = 0
            report.checked += 1
            match = _found_again(row, found)
            if match is None:
                report.missing += 1
                if prune and not row.attached and now - row.synced_at >= prune_after:
                    report.gone.append(row.id)
            else:
                report.confirmed += 1
                confirmed.append(
                    {
                        "id": row.id,
                        "city_id": row.city_id,
                        "name": match.name,
                        "spot": {"lat": match.lat, "lon": match.lon},
                        "parsed": {"house": match.housenumber, "street": match.street},
                        "source": source,
                        "source_id": match.source_id,
                        "synced_at": now,
                    }
                )
            if delay:
                await asyncio.sleep(delay)

        if confirmed:
            async with AddressUOW(sessionmaker) as uow:
                await uow.addresses.save_found(confirmed)
                await uow.commit()

    if report.gone:
        # deferred: avoids a service<->bootstrap import cycle
        from geo.service.address import AddressService

        for address_id in report.gone:
            await AddressService(AddressUOW(sessionmaker)).delete(address_id)
            report.pruned += 1
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=settings.GEO_PHOTON_URL)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--older-than-days",
        type=float,
        default=30.0,
        help="only rows not confirmed for this long are asked again",
    )
    parser.add_argument(
        "--limit", type=int, default=500, help="rows to ask in one run"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="seconds between requests; the public Photon is fair-use, 0 for your own",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="delete duplicates and rows missing for --prune-after-days",
    )
    parser.add_argument("--prune-after-days", type=float, default=90.0)
    return parser


def main() -> None:
    basicConfig(level="INFO", format="%(asctime)s %(message)s")
    args = _build_parser().parse_args()
    report = asyncio.run(
        refresh(
            PhotonGeocoder(args.url, timeout=args.timeout),
            older_than=timedelta(days=args.older_than_days),
            limit=args.limit,
            prune=args.prune,
            prune_after=timedelta(days=args.prune_after_days),
            delay=args.delay,
        )
    )
    logger.info(
        "checked %d: %d confirmed, %d missing, %d duplicate(s), %d error(s), "
        "%d pruned%s",
        report.checked,
        report.confirmed,
        report.missing,
        report.duplicates,
        report.errors,
        report.pruned,
        ", stopped early: the geocoder keeps failing" if report.aborted else "",
    )


if __name__ == "__main__":
    main()
