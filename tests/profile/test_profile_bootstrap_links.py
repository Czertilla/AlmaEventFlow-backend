from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

Maker = async_sessionmaker[AsyncSession]


async def _person(engine: AsyncEngine) -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO person (id, surname, name, created_at) "
                "VALUES (:id, 'S', 'N', now())"
            ),
            {"id": person_id},
        )
    return person_id


async def _links(engine: AsyncEngine) -> set[tuple[UUID, UUID]]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT person_id, user_id FROM person_account"))
        return {(row.person_id, row.user_id) for row in rows}


async def test_the_links_of_the_user_database_are_adopted_without_overwriting(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    from profile.bootstrap.links import adopt

    fresh, already, taken = [await _person(profile_engine) for _ in range(3)]
    new_user, known_user, rival, other = uuid4(), uuid4(), uuid4(), uuid4()
    async with profile_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO person_account (person_id, user_id, created_at) VALUES "
                "(:already, :known, now()), (:taken, :holder, now())"
            ),
            {
                "already": already,
                "known": known_user,
                "taken": taken,
                "holder": uuid4(),
            },
        )
    pairs = [
        (new_user, fresh),
        (known_user, already),
        (rival, taken),
        (other, uuid4()),
    ]

    dry = await adopt(profile_sessionmaker, pairs, dry_run=True)
    assert (new_user, fresh) not in {(u, p) for p, u in await _links(profile_engine)}
    report = await adopt(profile_sessionmaker, pairs)
    again = await adopt(profile_sessionmaker, pairs)

    assert (dry.linked, report.linked, again.linked) == (1, 1, 0)
    assert (report.seen, report.present) == (4, 1)
    assert report.clashes == [(rival, taken)]
    assert [user for user, _ in report.unknown_person] == [other]
    assert (fresh, new_user) in await _links(profile_engine)
    assert again.present == 2
    async with profile_engine.connect() as conn:
        history = (
            await conn.execute(
                text(
                    "SELECT user_id, old_person_id, new_person_id, action, source, "
                    "actor_id FROM person_account_history"
                )
            )
        ).all()
    assert [tuple(row) for row in history] == [
        (new_user, None, fresh, "linked", "bootstrap", None)
    ]
