"""One-off/periodically-rerun data job, not request-path code:

    python -m geo.bootstrap.run --city moscow
    python -m geo.bootstrap.run --city moscow --fresh --prune-stale

Idempotent -- re-running upserts (keyed on each address's deterministic
uuid5 over city+street+housenumber, see ``_address_id``) instead of
duplicating, even if the upstream OSM element id for the same real-world
address changes between runs. Chunks the target bbox into a grid, fetches
cells concurrently over a pool of Overpass mirrors and records finished
cells in a checkpoint file, so an interrupted or partly failed run resumes
with only the missing cells.

``--prune-stale`` turns a run into a re-sync: after a full (``--fresh``)
import, any ``source="osm"`` address in the city not touched by this run
(and not attached to a location) is deleted, catching upstream renames and
deletions. See ``geo.service.live_fetch`` for the complementary on-demand
path that fetches addresses outside any bulk-imported city on search.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import basicConfig, getLogger
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings
from geo.bootstrap.coverage import cells_covering_bbox
from geo.bootstrap.sources import (
    DEFAULT_MIRRORS,
    MIRRORS,
    BBox,
    OverpassError,
    OverpassSource,
    chunk_bbox,
    pick_administrative_names,
    resolve_mirror_urls,
)
from geo.service.geography import resolve_or_create_city
from geo.uow.address import AddressUOW

logger = getLogger("geo.bootstrap")

# Rough box around Moscow within the MKAD plus a margin -- not a precise
# administrative boundary, just wide enough to catch the city.
CITY_BBOXES: dict[str, BBox] = {
    "moscow": (55.49, 37.32, 55.96, 37.97),
}

MOSCOW_SEED = {
    "country_name": "Россия",
    "country_code": "RU",
    "region_name": "Москва",
    "city_name": "Москва",
}

CITY_SEEDS: dict[str, dict] = {
    "moscow": MOSCOW_SEED,
}


@dataclass
class Checkpoint:
    path: Path
    signature: str
    done: set[int] = field(default_factory=set)

    @classmethod
    def load(cls, path: Path, signature: str) -> "Checkpoint":
        checkpoint = cls(path, signature)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return checkpoint
        if data.get("signature") == signature:
            checkpoint.done = set(data.get("done", []))
        return checkpoint

    def save(self) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"signature": self.signature, "done": sorted(self.done)}),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)


@dataclass
class Progress:
    total: int
    done: int = 0
    addresses: int = 0
    failed: list[int] = field(default_factory=list)
    recent: deque[float] = field(default_factory=lambda: deque(maxlen=8))

    def minutes_left(self) -> int:
        if len(self.recent) < 2:
            return 0
        per_cell = (self.recent[-1] - self.recent[0]) / (len(self.recent) - 1)
        left = self.total - self.done - len(self.failed)
        return round(per_cell * max(left, 0) / 60)


def _bbox_contains(bbox: BBox, lat: float, lon: float) -> bool:
    min_lat, min_lon, max_lat, max_lon = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


async def resolve_city_for_point(
    uow: AddressUOW, source: OverpassSource, lat: float, lon: float
) -> int:
    """Matches a known bulk-imported city's bbox first (skips a network
    round-trip for the common case); otherwise reverse-geocodes the point's
    real country/region/city via Overpass's own administrative boundaries
    (``OverpassSource.reverse_geocode``) and seeds/reuses those rows -- never
    a placeholder, and never collides two different towns onto one city_id
    the way a single shared fallback city would."""
    for name, bbox in CITY_BBOXES.items():
        if _bbox_contains(bbox, lat, lon):
            return await resolve_or_create_city(uow, **CITY_SEEDS[name])
    country, region, city = pick_administrative_names(
        await source.reverse_geocode(lat, lon)
    )
    return await resolve_or_create_city(uow, country, region, city)


async def _flush(batch: list[dict], sessionmaker: async_sessionmaker | None) -> int:
    rows = list({row["id"]: row for row in batch}.values())
    async with AddressUOW(sessionmaker) as uow:
        await uow.addresses.upsert_many(rows)
        await uow.commit()
    return len(rows)


def _address_id(city_id: int, street: str, housenumber: str) -> UUID:
    """Keyed on the normalized (city, street, housenumber), not the upstream
    element: OSM's own id for the same real-world address can change between
    reimports (a redrawn way, a node retagged to a way, ...), and this keeps
    the row -- and its uuid -- stable regardless, so a reimport updates the
    existing row instead of inserting a duplicate."""
    return uuid5(NAMESPACE_URL, f"{city_id}:{street}:{housenumber}")


async def _import_cell(
    source: OverpassSource,
    cell: BBox,
    city_id: int,
    batch_size: int,
    db_lock: asyncio.Lock,
    sessionmaker: async_sessionmaker | None,
    *,
    id_fn: Callable[[str, str], UUID],
    synced_at: datetime,
) -> int:
    rows: dict[tuple[str, str], dict] = {}
    async for raw in source.fetch(cell):
        key = (raw.street.strip().casefold(), raw.housenumber.strip().casefold())
        rows.setdefault(
            key,
            {
                "id": id_fn(*key),
                "city_id": city_id,
                "name": raw.name,
                "spot": {"lat": raw.lat, "lon": raw.lon},
                "parsed": {"house": raw.housenumber, "street": raw.street},
                "source": raw.source,
                "source_id": raw.source_id,
                "synced_at": synced_at,
            },
        )
    batch = list(rows.values())
    stored = 0
    async with db_lock:
        for start in range(0, len(batch), batch_size):
            stored += await _flush(batch[start : start + batch_size], sessionmaker)
    return stored


async def _run(
    args: argparse.Namespace, sessionmaker: async_sessionmaker | None = None
) -> Progress:
    if args.prune_stale and not args.fresh:
        raise ValueError(
            "--prune-stale requires --fresh: a checkpointed rerun skips "
            "already-done cells and never touches their synced_at"
        )
    if args.prune_stale and args.min_lat is not None:
        raise ValueError(
            "--prune-stale isn't supported with a manual bbox override -- "
            "it would delete addresses merely outside this run's area"
        )

    run_started_at = datetime.now(timezone.utc)
    bbox = (
        (args.min_lat, args.min_lon, args.max_lat, args.max_lon)
        if args.min_lat is not None
        else CITY_BBOXES[args.city]
    )
    source = OverpassSource(
        urls=resolve_mirror_urls(args.servers),
        timeout=args.timeout,
        attempts=args.attempts,
        cooldown=args.cooldown,
    )

    async with AddressUOW(sessionmaker) as uow:
        city_id = await resolve_or_create_city(uow, **CITY_SEEDS[args.city])

    cells = list(chunk_bbox(bbox, grid=args.grid))
    checkpoint = Checkpoint.load(
        Path(args.state), f"{args.city}|{bbox}|{args.grid}"
    )
    if args.fresh:
        checkpoint.done.clear()

    pending: asyncio.Queue[int] = asyncio.Queue()
    for index in range(1, len(cells) + 1):
        if index not in checkpoint.done:
            pending.put_nowait(index)
    progress = Progress(total=pending.qsize())
    logger.info(
        "city_id=%s bbox=%s grid=%dx%d: %d cell(s) to fetch, %d already done, %d mirror(s), %d worker(s)",
        city_id,
        bbox,
        args.grid,
        args.grid,
        progress.total,
        len(cells) - progress.total,
        len(source.urls),
        args.concurrency,
    )

    db_lock = asyncio.Lock()

    async def worker() -> None:
        while True:
            try:
                index = pending.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                stored = await _import_cell(
                    source,
                    cells[index - 1],
                    city_id,
                    args.batch_size,
                    db_lock,
                    sessionmaker,
                    id_fn=lambda s, h: _address_id(city_id, s, h),
                    synced_at=run_started_at,
                )
            except OverpassError as exc:
                progress.failed.append(index)
                logger.error("cell %d gave up: %s", index, exc)
                continue
            checkpoint.done.add(index)
            checkpoint.save()
            progress.done += 1
            progress.addresses += stored
            progress.recent.append(time.monotonic())
            logger.info(
                "[%d/%d] cell %d: %d addresses (total %d), ~%d min left",
                progress.done + len(progress.failed),
                progress.total,
                index,
                stored,
                progress.addresses,
                progress.minutes_left(),
            )

    await asyncio.gather(*(worker() for _ in range(args.concurrency)))

    coverage_rows = {
        cell: {
            "cell_row": cell[0],
            "cell_col": cell[1],
            "source": "osm",
            "fetched_at": run_started_at,
        }
        for index in checkpoint.done
        for cell in cells_covering_bbox(cells[index - 1])
    }
    if coverage_rows:
        async with AddressUOW(sessionmaker) as uow:
            await uow.coverage.upsert_many(list(coverage_rows.values()))
            await uow.commit()

    if args.prune_stale and not progress.failed:
        # deferred: avoids a service<->bootstrap import cycle
        from geo.service.address import AddressService

        async with AddressUOW(sessionmaker) as uow:
            stale_ids = await uow.addresses.stale_deletable_ids(
                city_id, "osm", run_started_at
            )
        for stale_id in stale_ids:
            await AddressService(AddressUOW(sessionmaker)).delete(stale_id)
        if stale_ids:
            logger.info(
                "pruned %d address(es) no longer present upstream", len(stale_ids)
            )

    return progress


def _build_parser() -> argparse.ArgumentParser:
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
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--servers",
        default=settings.GEO_OVERPASS_MIRRORS or ",".join(DEFAULT_MIRRORS),
        help=(
            f"comma-separated mirror names ({', '.join(MIRRORS)}) or full "
            "URLs, tried in rotation; defaults to GEO_OVERPASS_MIRRORS"
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="cells fetched in parallel (each mirror still serves one request at a time)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="per-request timeout in seconds; short on purpose, a slow mirror is skipped",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=6,
        help="mirror attempts per cell before the cell is given up",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=30.0,
        help="seconds a failed mirror sits out (grows with consecutive failures)",
    )
    parser.add_argument(
        "--state",
        default="geo_bootstrap_state.json",
        help="checkpoint file with finished cells, used to resume",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="ignore the checkpoint and fetch every cell again",
    )
    parser.add_argument(
        "--prune-stale",
        action="store_true",
        help=(
            "delete osm-sourced addresses in this city not seen in this run "
            "(re-sync mode; requires --fresh, incompatible with a bbox override)"
        ),
    )
    return parser


def main() -> None:
    basicConfig(level="INFO", format="%(asctime)s %(message)s")
    args = _build_parser().parse_args()
    try:
        progress = asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.warning("interrupted -- finished cells are saved, rerun the same command to resume")
        sys.exit(130)

    logger.info(
        "done: %d cell(s), %d addresses upserted, %d cell(s) failed",
        progress.done,
        progress.addresses,
        len(progress.failed),
    )
    if progress.failed:
        logger.error(
            "failed cells %s -- rerun the same command to retry only them",
            sorted(progress.failed),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
