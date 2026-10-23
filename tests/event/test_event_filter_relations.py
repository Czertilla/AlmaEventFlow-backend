from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from event.filter.attendance import AttendanceFilter
from event.filter.event import EventFilter
from event.filter.member import MemberFilter
from event.filter.participation import ParticipationFilter
from event.models.attendance import AttendanceORM
from event.models.event import EventORM
from event.models.member import MemberORM
from event.models.participation import ParticipationORM


@dataclass
class World:
    choir: UUID
    dance: UUID
    concert: UUID
    contest: UUID
    anna: UUID
    boris: UUID
    anna_choir: UUID
    boris_dance: UUID
    boris_inactive: UUID
    choir_concert: UUID
    dance_contest: UUID
    choir_role: UUID
    attendance_anna: UUID
    attendance_boris: UUID


async def _insert(engine: AsyncEngine, sql: str, **params: Any) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _world(engine: AsyncEngine) -> World:
    w = World(*(uuid4() for _ in range(14)))
    await _insert(
        engine,
        "INSERT INTO event_status (id, name) VALUES (1, 's') ON CONFLICT DO NOTHING",
    )
    for collective, name in ((w.choir, "Hor"), (w.dance, "Tantsy")):
        await _insert(
            engine,
            "INSERT INTO organization (id, name, type) "
            "VALUES (:id, :name, 'collective')",
            id=collective,
            name=name,
        )
        await _insert(
            engine,
            "INSERT INTO collective (id, is_verified) VALUES (:id, true)",
            id=collective,
        )
    for event, name in ((w.concert, "Koncert"), (w.contest, "Konkurs")):
        await _insert(
            engine,
            "INSERT INTO event (id, name, status_id, created_at) "
            "VALUES (:id, :name, 1, now())",
            id=event,
            name=name,
        )
    for person, surname in ((w.anna, "Ivanova"), (w.boris, "Petrov")):
        await _insert(
            engine,
            "INSERT INTO person (id, surname, name) VALUES (:id, :surname, 'X')",
            id=person,
            surname=surname,
        )
    members = (
        (w.anna_choir, w.anna, w.choir, True),
        (w.boris_dance, w.boris, w.dance, True),
        (w.boris_inactive, w.boris, w.choir, False),
    )
    for member, person, collective, active in members:
        await _insert(
            engine,
            "INSERT INTO member (id, person_id, collective_id, is_active, created_at) "
            "VALUES (:id, :person, :collective, :active, now())",
            id=member,
            person=person,
            collective=collective,
            active=active,
        )
    await _insert(
        engine,
        "INSERT INTO role (id, collective_id, name, created_at) "
        "VALUES (:id, :collective, 'Soloist', now())",
        id=w.choir_role,
        collective=w.choir,
    )
    await _insert(
        engine,
        "INSERT INTO member_role (role_id, member_id) VALUES (:role, :member)",
        role=w.choir_role,
        member=w.anna_choir,
    )
    for participation, collective, event in (
        (w.choir_concert, w.choir, w.concert),
        (w.dance_contest, w.dance, w.contest),
    ):
        await _insert(
            engine,
            "INSERT INTO participation (id, collective_id, event_id, created_at) "
            "VALUES (:id, :collective, :event, now())",
            id=participation,
            collective=collective,
            event=event,
        )
    for attendance, member, participation, comment in (
        (w.attendance_anna, w.anna_choir, w.choir_concert, "late"),
        (w.attendance_boris, w.boris_dance, w.dance_contest, None),
    ):
        await _insert(
            engine,
            "INSERT INTO attendance "
            "(id, member_id, participation_id, is_attended, is_verified, comment, "
            "created_at) "
            "VALUES (:id, :member, :participation, false, false, :comment, now())",
            id=attendance,
            member=member,
            participation=participation,
            comment=comment,
        )
    return w


async def _ids(
    sessionmaker: async_sessionmaker[AsyncSession], flt: Any, model: Any
) -> set[UUID]:
    async with sessionmaker() as session:
        rows = await session.scalars(flt.filter(select(model)))
        return {row.id for row in rows}


@pytest.fixture
async def world(event_engine: AsyncEngine) -> World:
    return await _world(event_engine)


async def test_participation_search_matches_collective_and_event_names(
    world: World, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    by_collective = await _ids(
        event_sessionmaker, ParticipationFilter(search="tants"), ParticipationORM
    )
    by_event = await _ids(
        event_sessionmaker, ParticipationFilter(search="koncer"), ParticipationORM
    )

    assert by_collective == {world.dance_contest}
    assert by_event == {world.choir_concert}


async def test_participation_is_found_by_id(
    world: World, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    one = await _ids(
        event_sessionmaker,
        ParticipationFilter(id=world.dance_contest),
        ParticipationORM,
    )
    many = await _ids(
        event_sessionmaker,
        ParticipationFilter(id__in=[world.dance_contest, world.choir_concert]),
        ParticipationORM,
    )

    assert one == {world.dance_contest}
    assert many == {world.dance_contest, world.choir_concert}


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ({"collective_id": "choir"}, "attendance_anna"),
        ({"event_id": "contest"}, "attendance_boris"),
        ({"person_id": "boris"}, "attendance_boris"),
        ({"member_id": "anna_choir"}, "attendance_anna"),
        ({"participation_id": "dance_contest"}, "attendance_boris"),
        ({"search": "ivanov"}, "attendance_anna"),
        ({"search": "konkurs"}, "attendance_boris"),
        ({"search": "hor"}, "attendance_anna"),
        ({"search": "late"}, "attendance_anna"),
    ],
)
async def test_attendance_is_narrowed_through_its_relations(
    filters: dict[str, str],
    expected: str,
    world: World,
    event_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    params: dict[str, Any] = {
        name: getattr(world, value) if name != "search" else value
        for name, value in filters.items()
    }

    found = await _ids(event_sessionmaker, AttendanceFilter(**params), AttendanceORM)

    assert found == {getattr(world, expected)}


async def test_attendance_filter_restores_its_fields_after_filtering(
    world: World,
) -> None:
    flt = AttendanceFilter(collective_id=world.choir, person_id=world.anna)

    flt.filter(select(AttendanceORM))

    assert flt.collective_id == world.choir
    assert flt.person_id == world.anna


async def test_members_are_filtered_by_role(
    world: World, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    one = await _ids(
        event_sessionmaker, MemberFilter(role_id=world.choir_role), MemberORM
    )
    many = await _ids(
        event_sessionmaker, MemberFilter(role_id__in=[world.choir_role]), MemberORM
    )

    assert one == many == {world.anna_choir}


async def test_inactive_members_are_hidden_unless_asked_for(
    world: World, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    default = await _ids(
        event_sessionmaker, MemberFilter(is_active=True), MemberORM
    )
    everyone = await _ids(
        event_sessionmaker,
        MemberFilter(is_active=True, include_inactive=True),
        MemberORM,
    )
    only_inactive = await _ids(
        event_sessionmaker, MemberFilter(is_active=False), MemberORM
    )

    assert default == {world.anna_choir, world.boris_dance}
    assert everyone == {world.anna_choir, world.boris_dance, world.boris_inactive}
    assert only_inactive == {world.boris_inactive}


async def test_events_are_found_by_id(
    world: World, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    found = await _ids(event_sessionmaker, EventFilter(id=world.contest), EventORM)

    assert found == {world.contest}
