"""One-time job, run once after profile started to keep the heads of units:

    python -m org.bootstrap.republish
    python -m org.bootstrap.republish --dry-run

The profile service opens the full name of the head of a university or a faculty
to every user, so it keeps their `principal_id`. A university or a faculty
announced before profile stored it carries no head there; this announces them
again.
"""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from logging import basicConfig, getLogger

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database.sqlalchemy import new_session
from core.schema.message.org import OrganizationData

logger = getLogger("org.bootstrap")

UNIT_TYPES = ("university", "faculty")

Publish = Callable[[list[OrganizationData]], Awaitable[object]]


async def announce(
    maker: async_sessionmaker[AsyncSession],
    publish: Publish,
    types: Sequence[str] = UNIT_TYPES,
    *,
    dry_run: bool = False,
) -> int:
    async with maker() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id, name, type, principal_id FROM organization "
                    "WHERE type = ANY(:types) ORDER BY id"
                ),
                {"types": list(types)},
            )
        ).all()
    organizations = [
        OrganizationData(
            id=row.id, name=row.name, type=row.type, principal_id=row.principal_id
        )
        for row in rows
    ]
    if organizations and not dry_run:
        await publish(organizations)
    return len(organizations)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="only count")
    return parser


def main() -> None:
    basicConfig(level="INFO", format="%(asctime)s %(message)s")
    args = _build_parser().parse_args()

    async def run() -> int:
        from core.broker.kafka import broker
        from org.api.kafka.pub.organization import on_organization_updated

        await broker.start()
        try:
            return await announce(
                new_session, on_organization_updated, dry_run=args.dry_run
            )
        finally:
            await broker.stop()

    count = asyncio.run(run())
    logger.info(
        "%d organization(s)%s", count, " counted" if args.dry_run else " announced"
    )


if __name__ == "__main__":
    main()
