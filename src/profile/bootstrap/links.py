"""One-time job, run before the profile service starts serving:

    python -m profile.bootstrap.links
    python -m profile.bootstrap.links --user-db user --dry-run

The profile service owns the link of an account with its person
(person_account). Until it did, the user service kept it in "user".person_id.
This copies those pairs into the profile database. A pair is never written over
another: one that clashes with a link profile already has, or names a person
profile does not know, is only reported.
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from logging import basicConfig, getLogger
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.sqlalchemy import new_session
from core.database.sqlalchemy.engine.pgsql import get_url

logger = getLogger("profile.bootstrap")

Pair = tuple[UUID, UUID]


@dataclass
class Report:
    seen: int = 0
    linked: int = 0
    present: int = 0
    unknown_person: list[Pair] = field(default_factory=lambda: [])
    clashes: list[Pair] = field(default_factory=lambda: [])


async def read_pairs(user_db: str) -> list[Pair]:
    engine = create_async_engine(get_url(db_name=user_db))
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text('SELECT id, person_id FROM "user" WHERE person_id IS NOT NULL')
            )
            return [(row.id, row.person_id) for row in rows]
    finally:
        await engine.dispose()


async def _scalar(session: AsyncSession, query: str, **params: UUID) -> UUID | None:
    return (await session.execute(text(query), params)).scalar_one_or_none()


async def adopt(
    maker: async_sessionmaker[AsyncSession], pairs: list[Pair], *, dry_run: bool = False
) -> Report:
    report = Report()
    for user_id, person_id in pairs:
        report.seen += 1
        async with maker() as session:
            holder = await _scalar(
                session,
                "SELECT user_id FROM person_account WHERE person_id = :p",
                p=person_id,
            )
            current = await _scalar(
                session,
                "SELECT person_id FROM person_account WHERE user_id = :u",
                u=user_id,
            )
            known = await _scalar(
                session, "SELECT id FROM person WHERE id = :p", p=person_id
            )
            if holder == user_id:
                report.present += 1
            elif holder is not None or current is not None:
                report.clashes.append((user_id, person_id))
            elif known is None:
                report.unknown_person.append((user_id, person_id))
            else:
                if not dry_run:
                    await session.execute(
                        text(
                            "INSERT INTO person_account "
                            "(person_id, user_id, created_at) VALUES (:p, :u, now())"
                        ),
                        {"p": person_id, "u": user_id},
                    )
                    await session.commit()
                report.linked += 1
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-db", default="user", help="database of the user service"
    )
    parser.add_argument("--dry-run", action="store_true", help="only report")
    return parser


def main() -> None:
    basicConfig(level="INFO", format="%(asctime)s %(message)s")
    args = _build_parser().parse_args()

    async def run() -> Report:
        return await adopt(
            new_session, await read_pairs(args.user_db), dry_run=args.dry_run
        )

    report = asyncio.run(run())
    logger.info(
        "%d account(s): %d linked, %d already linked, %d unknown person(s), "
        "%d clash(es)%s",
        report.seen,
        report.linked,
        report.present,
        len(report.unknown_person),
        len(report.clashes),
        ", nothing written" if args.dry_run else "",
    )
    for user_id, person_id in report.unknown_person + report.clashes:
        logger.warning("not linked: account %s, person %s", user_id, person_id)


if __name__ == "__main__":
    main()
