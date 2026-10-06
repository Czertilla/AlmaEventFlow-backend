from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from event.service.collective import CollectiveService
from event.uow.collective import CollectiveUOW


async def _person(engine: AsyncEngine) -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO person (id, surname, name) VALUES (:id, 'S', 'N')"),
            {"id": person_id},
        )
    return person_id


async def _collective(engine: AsyncEngine, name: str, principal: UUID | None) -> UUID:
    collective_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type, principal_id) "
                "VALUES (:id, :name, 'collective', :principal)"
            ),
            {"id": collective_id, "name": name, "principal": principal},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective_id},
        )
    return collective_id


async def _member(
    engine: AsyncEngine, person_id: UUID, collective_id: UUID, *, active: bool = True
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO member "
                "(id, person_id, collective_id, is_active, created_at) "
                "VALUES (:id, :person, :collective, :active, now())"
            ),
            {
                "id": uuid4(),
                "person": person_id,
                "collective": collective_id,
                "active": active,
            },
        )


async def test_memberships_list_active_collectives_of_the_person_only(
    event_engine: AsyncEngine,
    event_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    person, other = await _person(event_engine), await _person(event_engine)
    joined = await _collective(event_engine, "Choir", None)
    left = await _collective(event_engine, "Orchestra", None)
    foreign = await _collective(event_engine, "Theatre", None)
    await _member(event_engine, person, joined)
    await _member(event_engine, person, left, active=False)
    await _member(event_engine, other, foreign)

    service = CollectiveService(CollectiveUOW(event_sessionmaker))
    memberships = await service.get_my_memberships(person)

    assert [(m.id, m.name) for m in memberships] == [(joined, "Choir")]
    assert await service.get_my_memberships(uuid4()) == []


async def test_a_leader_who_is_not_a_member_has_no_memberships(
    event_engine: AsyncEngine,
    event_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    leader = await _person(event_engine)
    led = await _collective(event_engine, "Choir", leader)
    service = CollectiveService(CollectiveUOW(event_sessionmaker))

    assert [c.id for c in await service.get_my_collectives(leader)] == [led]
    assert await service.get_my_memberships(leader) == []
