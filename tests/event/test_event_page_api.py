import datetime
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine
from support import event_seed as seed
from support.http import principal

BASE = "/event/v2/events"


@dataclass
class World:
    leader: UUID
    member_person: UUID
    stranger: UUID
    choir: UUID
    band: UUID
    event: UUID
    choir_participation: UUID
    band_participation: UUID
    own_attendance: UUID
    idle_member: UUID


async def _world(engine: AsyncEngine) -> World:
    leader = await seed.person(engine, "Lead", "Anna")
    member_person = await seed.person(engine, "Zorin", "Boris", "Petrovich")
    colleague = await seed.person(engine, "Abramov", "Ivan")
    idle = await seed.person(engine, "Idle", "Ivan")
    stranger = await seed.person(engine, "Stranger")
    choir = await seed.collective(engine, "Choir", leader)
    band = await seed.collective(engine, "Band", await seed.person(engine, "BandLead"))
    mine = await seed.member(engine, member_person, choir)
    other = await seed.member(engine, colleague, choir)
    idle_member = await seed.member(engine, idle, choir)
    await seed.member(engine, await seed.person(engine, "Left"), choir, active=False)
    tenor = await seed.role(engine, choir, "Tenor", [mine, other])
    await seed.role(engine, choir, "Bass", [other])
    assert tenor
    hall = await seed.location(engine, "Main hall", 55.0, 37.0)
    event = await seed.event(
        engine, "Gala", seed.day(2), [choir, band], location_id=hall, type="concert"
    )
    start = datetime.datetime(2026, 11, 1, 18, 0, tzinfo=datetime.UTC)
    await seed.stage(
        engine, event.id, start + datetime.timedelta(hours=1), None, "Second"
    )
    await seed.stage(
        engine, event.id, start, start + datetime.timedelta(hours=1), "First"
    )
    own = await seed.attendance(engine, event.of(choir), mine, True, marked=True)
    await seed.attendance(engine, event.of(choir), other, False, comment="sick")
    await seed.attendance(
        engine,
        event.of(band),
        await seed.member(engine, await seed.person(engine, "Bandsman"), band),
        True,
        marked=True,
    )
    return World(
        leader,
        member_person,
        stranger,
        choir,
        band,
        event.id,
        event.of(choir),
        event.of(band),
        own,
        idle_member,
    )


async def test_the_leader_gets_the_whole_page_in_one_answer(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(
        f"{BASE}/{world.event}", headers=principal(person_id=world.leader)
    )

    page = response.json()
    assert response.status_code == 200, response.text
    assert page["event"]["name"] == "Gala"
    assert page["event"]["location"]["name"] == "Main hall"
    assert page["event"]["type"] == "concert"
    assert [s["name"] for s in page["stages"]] == ["First", "Second"]
    assert [p["collective_name"] for p in page["participations"]] == ["Choir", "Band"]
    assert page["editable_collective_id"] == str(world.choir)
    choir = next(p for p in page["participations"] if p["collective_name"] == "Choir")
    assert choir["is_principal"] is True
    assert (choir["attended_count"], choir["total_count"]) == (1, 2)
    people = [a["member"]["person"]["surname"] for a in choir["attendances"]]
    assert people == ["Abramov", "Zorin"]
    abramov, zorin = choir["attendances"]
    assert [r["name"] for r in abramov["member"]["roles"]] == ["Bass", "Tenor"]
    assert abramov["comment"] == "sick"
    assert abramov["is_attended"] is None
    assert zorin["is_attended"] is True
    assert zorin["member"]["person"]["patronymic"] == "Petrovich"
    assert [m["person"]["surname"] for m in choir["addable_members"]] == ["Idle"]
    assert choir["my_attendance_id"] is None


async def test_a_member_sees_the_roster_of_their_own_collective_only(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(
        f"{BASE}/{world.event}", headers=principal(person_id=world.member_person)
    )

    by_name = {p["collective_name"]: p for p in response.json()["participations"]}
    choir, band = by_name["Choir"], by_name["Band"]
    assert [p["collective_name"] for p in response.json()["participations"]] == [
        "Choir",
        "Band",
    ]
    assert (choir["is_member"], choir["is_principal"]) == (True, False)
    assert choir["my_attendance_id"] == str(world.own_attendance)
    assert len(choir["attendances"]) == 2
    assert choir["addable_members"] == []
    assert response.json()["editable_collective_id"] is None
    assert band["can_view_attendances"] is False
    assert (band["attendances"], band["attended_count"], band["total_count"]) == (
        [],
        None,
        None,
    )


async def test_a_stranger_sees_who_takes_part_but_no_places(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(
        f"{BASE}/{world.event}", headers=principal(person_id=world.stranger)
    )

    participations = response.json()["participations"]
    assert [p["collective_name"] for p in participations] == ["Band", "Choir"]
    assert all(
        p["attendances"] == [] and p["total_count"] is None for p in participations
    )


async def test_a_superuser_manages_every_participation(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(f"{BASE}/{world.event}", headers=principal(superuser=True))

    participations = response.json()["participations"]
    assert all(p["is_principal"] and p["can_view_attendances"] for p in participations)
    assert response.json()["editable_collective_id"] == str(world.band)


async def test_a_draft_and_a_template_are_for_the_leaders_of_the_collectives_in_it(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    draft = await seed.event(
        event_engine, "Draft", seed.day(1), [world.choir], status="draft"
    )
    model = await seed.event(
        event_engine, "Model", None, [world.choir], status="template"
    )
    leader = principal(person_id=world.leader)
    member = principal(person_id=world.member_person)

    seen = [await api.get(f"{BASE}/{e.id}", headers=leader) for e in (draft, model)]
    hidden = [await api.get(f"{BASE}/{e.id}", headers=member) for e in (draft, model)]
    missing = await api.get(f"{BASE}/{uuid4()}", headers=leader)

    assert [r.status_code for r in seen] == [200, 200]
    assert [r.status_code for r in hidden] == [404, 404]
    assert seen[1].json()["event"]["status"] == "template"
    assert seen[1].json()["event"]["date"] is None
    assert missing.status_code == 404
