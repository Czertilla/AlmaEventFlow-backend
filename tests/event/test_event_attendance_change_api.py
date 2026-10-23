from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine
from support import event_seed as seed
from support.http import principal

BASE = "/event/v2/attendances"


@dataclass
class World:
    leader: UUID
    mine_person: UUID
    other_person: UUID
    own: UUID
    colleague: UUID
    participation: UUID


async def _world(engine: AsyncEngine) -> World:
    leader = await seed.person(engine, "Lead")
    mine_person = await seed.person(engine, "Mine")
    other_person = await seed.person(engine, "Other")
    choir = await seed.collective(engine, "Choir", leader)
    mine = await seed.member(engine, mine_person, choir)
    other = await seed.member(engine, other_person, choir)
    event = await seed.event(engine, "Rehearsal", seed.day(1), [choir])
    own = await seed.attendance(engine, event.of(choir), mine)
    colleague = await seed.attendance(engine, event.of(choir), other)
    return World(leader, mine_person, other_person, own, colleague, event.of(choir))


async def test_a_member_marks_and_comments_on_their_own_place(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = principal(person_id=world.mine_person)

    marked = await api.patch(
        f"{BASE}/{world.own}", json={"is_attended": True}, headers=headers
    )
    commented = await api.patch(
        f"{BASE}/{world.own}", json={"comment": "late"}, headers=headers
    )
    cleared = await api.patch(
        f"{BASE}/{world.own}", json={"comment": None}, headers=headers
    )
    untouched = await api.patch(f"{BASE}/{world.own}", json={}, headers=headers)

    body = marked.json()
    assert marked.status_code == 200, marked.text
    assert body["attendance"]["is_attended"] is True
    assert body["attendance"]["edited_at"] is not None
    assert body["participation"]["id"] == str(world.participation)
    assert (
        body["participation"]["attended_count"],
        body["participation"]["total_count"],
    ) == (1, 2)
    assert commented.json()["attendance"]["comment"] == "late"
    assert commented.json()["attendance"]["is_attended"] is True
    assert cleared.json()["attendance"]["comment"] is None
    assert untouched.json()["attendance"]["is_attended"] is True


async def test_an_untouched_place_reads_as_not_marked_until_someone_marks_it(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = principal(person_id=world.mine_person)

    untouched = await api.patch(f"{BASE}/{world.own}", json={}, headers=headers)
    absent = await api.patch(
        f"{BASE}/{world.own}", json={"is_attended": False}, headers=headers
    )

    assert untouched.json()["attendance"]["is_attended"] is None
    assert untouched.json()["attendance"]["edited_at"] is None
    assert absent.json()["attendance"]["is_attended"] is False
    assert absent.json()["attendance"]["edited_at"] is not None


async def test_a_value_cannot_be_cleared_with_null(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    admin = principal(superuser=True)

    attended = await api.patch(
        f"{BASE}/{world.own}", json={"is_attended": None}, headers=admin
    )
    verified = await api.patch(
        f"{BASE}/{world.own}", json={"is_verified": None}, headers=admin
    )

    assert attended.status_code == 422
    assert verified.status_code == 422


async def test_a_member_cannot_touch_a_colleagues_place_or_verify(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = principal(person_id=world.mine_person)

    colleague = await api.patch(
        f"{BASE}/{world.colleague}", json={"is_attended": True}, headers=headers
    )
    verify = await api.patch(
        f"{BASE}/{world.own}", json={"is_verified": True}, headers=headers
    )
    stranger = await api.patch(
        f"{BASE}/{world.own}",
        json={"is_attended": True},
        headers=principal(person_id=uuid4()),
    )
    nobody = await api.patch(
        f"{BASE}/{world.own}", json={"is_attended": True}, headers=principal()
    )

    assert (colleague.status_code, colleague.json()["detail"]) == (
        403,
        "NOT_MEMBER_PERSON",
    )
    assert (verify.status_code, verify.json()["detail"]) == (
        403,
        "NOT_COLLECTIVE_PRINCIPAL",
    )
    assert stranger.status_code == 403
    assert nobody.status_code == 403


async def test_the_leader_marks_verifies_and_changes_a_verified_place(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    leader = principal(person_id=world.leader)
    member = principal(person_id=world.other_person)

    marked = await api.patch(
        f"{BASE}/{world.colleague}",
        json={"is_attended": False, "is_verified": True},
        headers=leader,
    )
    refused = await api.patch(
        f"{BASE}/{world.colleague}", json={"is_attended": True}, headers=member
    )
    corrected = await api.patch(
        f"{BASE}/{world.colleague}",
        json={"is_attended": True, "is_verified": False},
        headers=leader,
    )

    assert marked.json()["attendance"]["is_verified"] is True
    assert (refused.status_code, refused.json()["detail"]) == (
        403,
        "ATTENDANCE_ALREADY_VERIFIED",
    )
    assert corrected.json()["attendance"]["is_attended"] is True
    assert corrected.json()["participation"]["attended_count"] == 1


async def test_a_superuser_changes_any_place_and_an_unknown_one_is_not_found(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    admin = principal(superuser=True)

    changed = await api.patch(
        f"{BASE}/{world.own}",
        json={"is_attended": True, "is_verified": True},
        headers=admin,
    )
    missing = await api.patch(
        f"{BASE}/{uuid4()}", json={"is_attended": True}, headers=admin
    )

    assert changed.json()["attendance"]["is_verified"] is True
    assert missing.status_code == 404


@dataclass
class Stage:
    leader: UUID
    member_person: UUID
    newcomer: UUID
    outsider: UUID
    participation: UUID


async def _stage(engine: AsyncEngine) -> Stage:
    leader = await seed.person(engine, "Lead")
    member_person = await seed.person(engine, "Mine")
    choir = await seed.collective(engine, "Choir", leader)
    band = await seed.collective(engine, "Band", await seed.person(engine, "BandLead"))
    await seed.member(engine, member_person, choir)
    newcomer = await seed.member(engine, await seed.person(engine, "New"), choir)
    outsider = await seed.member(engine, await seed.person(engine, "Out"), band)
    event = await seed.event(engine, "Rehearsal", seed.day(1), [choir])
    return Stage(leader, member_person, newcomer, outsider, event.of(choir))


async def test_the_leader_declares_a_member_and_the_new_place_is_not_marked(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    stage = await _stage(event_engine)
    headers = principal(person_id=stage.leader)
    body = {
        "participation_id": str(stage.participation),
        "member_id": str(stage.newcomer),
    }

    first = await api.post(BASE, json=body, headers=headers)
    again = await api.post(BASE, json=body, headers=headers)

    assert first.status_code == 200, first.text
    place = first.json()["attendance"]
    assert place["member_id"] == str(stage.newcomer)
    assert place["is_attended"] is None
    assert place["is_verified"] is False
    assert place["edited_at"] is None
    assert first.json()["participation"]["id"] == str(stage.participation)
    assert (
        first.json()["participation"]["attended_count"],
        first.json()["participation"]["total_count"],
    ) == (0, 1)
    assert again.json()["attendance"]["id"] == place["id"]
    assert again.json()["participation"]["total_count"] == 1


async def test_only_the_leader_or_a_superuser_declares_and_only_their_own_members(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    stage = await _stage(event_engine)
    body = {
        "participation_id": str(stage.participation),
        "member_id": str(stage.newcomer),
    }

    member = await api.post(
        BASE, json=body, headers=principal(person_id=stage.member_person)
    )
    admin = await api.post(BASE, json=body, headers=principal(superuser=True))
    foreign = await api.post(
        BASE,
        json={**body, "member_id": str(stage.outsider)},
        headers=principal(person_id=stage.leader),
    )
    nowhere = await api.post(
        BASE,
        json={**body, "participation_id": str(uuid4())},
        headers=principal(person_id=stage.leader),
    )

    assert (member.status_code, member.json()["detail"]) == (
        403,
        "NOT_COLLECTIVE_PRINCIPAL",
    )
    assert admin.status_code == 200, admin.text
    assert (foreign.status_code, foreign.json()["detail"]) == (404, "MEMBER_NOT_FOUND")
    assert (nowhere.status_code, nowhere.json()["detail"]) == (
        404,
        "PARTICIPATION_NOT_FOUND",
    )
