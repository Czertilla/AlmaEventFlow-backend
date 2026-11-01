from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support import event_seed as seed
from support.http import principal

from core.schema.message.event import SharedCollectiveSubjectsRequest
from event.api.kafka.sub.visibility import on_shared_collective_subjects
from event.uow.member import MemberUOW

BASE = "/event/v1"
ADMIN = principal(superuser=True)


@dataclass
class World:
    choir: UUID
    dance: UUID
    choir_leader: UUID
    dance_leader: UUID
    singer: UUID
    retired: UUID
    dancer: UUID
    singer_member: UUID
    retired_member: UUID
    dancer_member: UUID
    singer_attendance: UUID
    dancer_attendance: UUID


async def _world(engine: AsyncEngine) -> World:
    choir_leader = await seed.person(engine, "Choirleader")
    dance_leader = await seed.person(engine, "Danceleader")
    singer = await seed.person(engine, "Singer")
    retired = await seed.person(engine, "Retired")
    dancer = await seed.person(engine, "Dancer")
    choir = await seed.collective(engine, "Choir", choir_leader)
    dance = await seed.collective(engine, "Dance", dance_leader)
    singer_member = await seed.member(engine, singer, choir)
    retired_member = await seed.member(engine, retired, choir, active=False)
    dancer_member = await seed.member(engine, dancer, dance)
    event = await seed.event(engine, "Concert", seed.day(1), [choir, dance])
    return World(
        choir=choir,
        dance=dance,
        choir_leader=choir_leader,
        dance_leader=dance_leader,
        singer=singer,
        retired=retired,
        dancer=dancer,
        singer_member=singer_member,
        retired_member=retired_member,
        dancer_member=dancer_member,
        singer_attendance=await seed.attendance(
            engine, event.of(choir), singer_member, comment="late"
        ),
        dancer_attendance=await seed.attendance(
            engine, event.of(dance), dancer_member, comment="early"
        ),
    )


def _as(person_id: UUID | None) -> dict[str, str]:
    return principal(person_id=person_id, user_id=uuid4())


async def _members(
    api: httpx.AsyncClient, headers: dict[str, str], **params: str | int | bool
) -> set[str]:
    response = await api.get(
        f"{BASE}/members",
        params={"include_inactive": True, "limit": 100, **params},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return {item["person_id"] for item in response.json()["items"]}


async def test_members_and_attendances_need_a_verified_user(
    api: httpx.AsyncClient,
) -> None:
    unverified = principal(person_id=uuid4(), verified=False)

    assert (await api.get(f"{BASE}/members")).status_code == 401
    assert (await api.get(f"{BASE}/attendances")).status_code == 401
    assert (await api.get(f"{BASE}/members", headers=unverified)).status_code == 403
    assert (
        await api.get(f"{BASE}/attendances", headers=unverified)
    ).status_code == 403


async def test_a_leader_lists_only_the_members_of_their_collectives(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    seen = await _members(api, _as(world.choir_leader))

    assert seen == {str(world.singer), str(world.retired)}


async def test_an_active_member_lists_only_their_own_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    seen = await _members(api, _as(world.singer))

    assert seen == {str(world.singer), str(world.retired)}


async def test_a_former_member_sees_no_members(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    assert await _members(api, _as(world.retired)) == set()


async def test_a_caller_without_a_person_sees_no_members(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    await _world(event_engine)

    assert await _members(api, _as(None)) == set()


async def test_a_superuser_lists_every_member(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    assert await _members(api, ADMIN) == {
        str(world.singer),
        str(world.retired),
        str(world.dancer),
    }


async def test_a_name_search_does_not_reach_other_collectives(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = _as(world.choir_leader)

    foreign = await _members(api, headers, search="Dancer")
    by_person = await _members(api, headers, person_id=str(world.dancer))
    own = await _members(api, headers, search="Singer")

    assert foreign == by_person == set()
    assert own == {str(world.singer)}


async def test_a_member_of_another_collective_reads_as_missing(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = _as(world.choir_leader)

    own = await api.get(f"{BASE}/members/{world.singer_member}", headers=headers)
    foreign = await api.get(f"{BASE}/members/{world.dancer_member}", headers=headers)
    missing = await api.get(f"{BASE}/members/{uuid4()}", headers=headers)
    admin = await api.get(f"{BASE}/members/{world.dancer_member}", headers=ADMIN)

    assert own.status_code == 200
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    assert admin.status_code == 200


async def _attendances(
    api: httpx.AsyncClient, headers: dict[str, str], **params: str | int | bool
) -> set[str]:
    response = await api.get(
        f"{BASE}/attendances", params={"limit": 100, **params}, headers=headers
    )
    assert response.status_code == 200, response.text
    return {item["id"] for item in response.json()["items"]}


async def test_attendances_are_listed_within_the_callers_collectives(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    leader = await _attendances(api, _as(world.choir_leader))
    member = await _attendances(api, _as(world.singer))
    outsider = await _attendances(api, _as(None))
    admin = await _attendances(api, ADMIN)

    assert leader == member == {str(world.singer_attendance)}
    assert outsider == set()
    assert admin == {str(world.singer_attendance), str(world.dancer_attendance)}


async def test_an_attendance_search_by_name_does_not_reach_other_collectives(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = _as(world.choir_leader)

    assert await _attendances(api, headers, search="Dancer") == set()
    assert await _attendances(api, headers, search="Singer") == {
        str(world.singer_attendance)
    }


async def test_an_attendance_of_another_collective_reads_as_missing(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = _as(world.choir_leader)

    own = await api.get(
        f"{BASE}/attendances/{world.singer_attendance}", headers=headers
    )
    foreign = await api.get(
        f"{BASE}/attendances/{world.dancer_attendance}", headers=headers
    )
    missing = await api.get(f"{BASE}/attendances/{uuid4()}", headers=headers)
    admin = await api.get(
        f"{BASE}/attendances/{world.dancer_attendance}", headers=ADMIN
    )

    assert own.status_code == 200
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    assert admin.status_code == 200


async def test_a_leader_reads_their_own_collective_through_the_me_routes(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = _as(world.choir_leader)
    own = f"{BASE}/me/collectives/{world.choir}"

    members = await api.get(
        f"{own}/members", params={"include_inactive": True}, headers=headers
    )
    attendance = await api.get(
        f"{own}/attendance/{world.singer_attendance}", headers=headers
    )
    foreign = await api.get(
        f"{own}/attendance/{world.dancer_attendance}", headers=headers
    )

    assert members.status_code == 200, members.text
    assert {item["person_id"] for item in members.json()["items"]} == {
        str(world.singer),
        str(world.retired),
    }
    assert attendance.status_code == 200, attendance.text
    assert foreign.status_code == 404


async def test_only_a_superuser_adds_members(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    newcomer = await seed.person(event_engine, "Newcomer")
    body = {"person_id": str(newcomer)}
    choir = f"{BASE}/me/collectives/{world.choir}/members"

    by_leader = await api.post(choir, json=body, headers=_as(world.choir_leader))
    by_member = await api.post(choir, json=body, headers=_as(world.singer))
    by_admin = await api.post(choir, json=body, headers=ADMIN)
    elsewhere = await api.post(
        f"{BASE}/me/collectives/{world.dance}/members",
        json={"person_id": str(world.singer)},
        headers=ADMIN,
    )
    missing = await api.post(
        f"{BASE}/me/collectives/{uuid4()}/members", json=body, headers=ADMIN
    )

    assert by_leader.status_code == by_member.status_code == 403
    assert by_admin.status_code == elsewhere.status_code == 200, by_admin.text
    assert by_admin.json()["person_id"] == str(newcomer)
    assert missing.status_code == 404
    assert await _members(api, ADMIN, person_id=str(newcomer)) == {str(newcomer)}


async def _shared(
    sessionmaker: async_sessionmaker[AsyncSession],
    viewer: UUID,
    subjects: list[UUID] | None = None,
) -> set[UUID]:
    response = await on_shared_collective_subjects(
        SharedCollectiveSubjectsRequest(viewer_person_id=viewer, subject_ids=subjects),
        MemberUOW(sessionmaker),
    )
    assert response.error is None
    assert response.data is not None
    return set(response.data.person_ids)


async def test_a_leader_and_a_member_share_the_active_people_of_the_collective(
    event_engine: AsyncEngine, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    world = await _world(event_engine)

    by_leader = await _shared(event_sessionmaker, world.choir_leader)
    by_member = await _shared(event_sessionmaker, world.singer)

    assert by_leader == by_member == {world.singer, world.choir_leader}


async def test_a_former_member_and_a_stranger_share_nothing(
    event_engine: AsyncEngine, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    world = await _world(event_engine)

    assert await _shared(event_sessionmaker, world.retired) == set()
    assert await _shared(event_sessionmaker, uuid4()) == set()


async def test_the_shared_people_are_narrowed_to_the_subjects_asked(
    event_engine: AsyncEngine, event_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    world = await _world(event_engine)

    shared = await _shared(
        event_sessionmaker,
        world.singer,
        [world.retired, world.dancer, uuid4(), world.choir_leader],
    )

    assert shared == {world.choir_leader}
