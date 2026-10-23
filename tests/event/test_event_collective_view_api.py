from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine
from support import event_seed as seed
from support.http import principal

BASE = "/event/v2/collectives"


@dataclass
class World:
    leader: UUID
    member_person: UUID
    choir: UUID
    band: UUID
    members: list[UUID]


async def _world(engine: AsyncEngine, events: int = 6) -> World:
    leader = await seed.person(engine, "Lead")
    member_person = await seed.person(engine, "Mem")
    choir = await seed.collective(engine, "Choir", leader)
    band = await seed.collective(engine, "Band", await seed.person(engine, "BandLead"))
    members = [
        await seed.member(engine, member_person, choir),
        await seed.member(engine, await seed.person(engine, "Abramov"), choir),
        await seed.member(
            engine, await seed.person(engine, "Gone"), choir, active=False
        ),
    ]
    await seed.role(engine, choir, "Tenor", members[:1])
    await seed.role(engine, choir, "Bass")
    hall = await seed.location(engine, "Hall", 1.0, 2.0)
    for offset in range(-events // 2, events // 2):
        event = await seed.event(
            engine,
            f"E{offset:+d}",
            seed.day(offset),
            [choir, band] if offset == 0 else [choir],
            location_id=hall if offset == 0 else None,
        )
        for member in members[:2]:
            await seed.attendance(
                engine, event.of(choir), member, offset < 0, marked=offset < 0
            )
    await seed.event(engine, "Model", None, [choir], status="template")
    await seed.event(engine, "Foreign", seed.day(0), [band])
    return World(leader, member_person, choir, band, members)


async def test_the_roster_has_names_roles_and_the_former_members(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(
        f"{BASE}/{world.choir}/roster", headers=principal(person_id=world.leader)
    )

    body = response.json()
    assert response.status_code == 200, response.text
    assert [m["person"]["surname"] for m in body["members"]] == [
        "Abramov",
        "Gone",
        "Mem",
    ]
    assert [m["is_active"] for m in body["members"]] == [True, False, True]
    mem = body["members"][2]
    assert [r["name"] for r in mem["roles"]] == ["Tenor"]
    assert [r["name"] for r in body["roles"]] == ["Bass", "Tenor"]
    assert body["roles"][0]["collective_id"] == str(world.choir)


async def test_the_panel_is_for_the_leader_and_a_superuser(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine, events=2)
    member = principal(person_id=world.member_person)

    codes = [
        (await api.get(f"{BASE}/{world.choir}/{path}", headers=headers)).status_code
        for path in ("roster", "events", "attendance-matrix")
        for headers in (
            member,
            principal(person_id=world.leader),
            principal(superuser=True),
        )
    ]

    assert codes == [403, 200, 200] * 3


async def test_the_events_of_a_collective_are_listed_in_every_status(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine, events=2)

    response = await api.get(
        f"{BASE}/{world.choir}/events", headers=principal(person_id=world.leader)
    )

    body = response.json()
    assert [e["name"] for e in body["items"]] == ["Model", "E+0", "E-1"]
    assert body["truncated"] is False
    shared = next(e for e in body["items"] if e["name"] == "E+0")
    assert shared["location"]["name"] == "Hall"
    assert shared["participation_id"]
    assert body["items"][0]["status"] == "template"


async def test_the_matrix_holds_the_roster_the_window_and_its_places(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    headers = principal(person_id=world.leader)

    first = await api.get(
        f"{BASE}/{world.choir}/attendance-matrix",
        params={"anchor": seed.iso(0), "limit": 2},
        headers=headers,
    )
    body = first.json()
    older = await api.get(
        f"{BASE}/{world.choir}/attendance-matrix",
        params={"direction": "past", "cursor": body["past_cursor"], "limit": 2},
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert [e["name"] for e in body["events"]] == ["E-2", "E-1", "E+0", "E+1"]
    assert (body["has_more_past"], body["has_more_future"]) == (True, True)
    assert len(body["members"]) == 3
    assert len(body["roles"]) == 2
    participations = {e["participation_id"] for e in body["events"]}
    assert {a["participation_id"] for a in body["attendances"]} == participations
    assert len(body["attendances"]) == 8
    by_event = {e["participation_id"]: e["name"] for e in body["events"]}
    assert {
        by_event[a["participation_id"]]: a["is_attended"]
        for a in body["attendances"]
    } == {"E-2": True, "E-1": True, "E+0": None, "E+1": None}
    assert [e["name"] for e in older.json()["events"]] == ["E-3"]
    assert len(older.json()["attendances"]) == 2
    assert older.json()["has_more_past"] is False


async def test_a_range_is_returned_whole(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)

    response = await api.get(
        f"{BASE}/{world.choir}/attendance-matrix",
        params={"date_from": seed.iso(-2), "date_to": seed.iso(0)},
        headers=principal(person_id=world.leader),
    )
    broken = await api.get(
        f"{BASE}/{world.choir}/attendance-matrix",
        params={"date_from": seed.iso(-2)},
        headers=principal(person_id=world.leader),
    )

    body = response.json()
    assert [e["name"] for e in body["events"]] == ["E-2", "E-1", "E+0"]
    assert (body["has_more_past"], body["has_more_future"]) == (False, False)
    assert (body["past_cursor"], body["future_cursor"]) == (None, None)
    assert broken.status_code == 422
