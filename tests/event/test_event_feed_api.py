import datetime
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine
from support import event_seed as seed
from support.http import principal

FEED = "/event/v2/feed"
CONTEXT = "/event/v2/me/context"


@dataclass
class World:
    leader: UUID
    member_person: UUID
    stranger: UUID
    choir: UUID
    band: UUID
    member: UUID


async def _world(engine: AsyncEngine) -> World:
    leader = await seed.person(engine, "Lead")
    member_person = await seed.person(engine, "Member")
    stranger = await seed.person(engine, "Stranger")
    choir = await seed.collective(engine, "Choir", leader)
    band = await seed.collective(engine, "Band", await seed.person(engine, "Other"))
    member = await seed.member(engine, member_person, choir)
    return World(leader, member_person, stranger, choir, band, member)


def _names(response: httpx.Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()["items"]]


async def test_the_context_lists_the_collectives_a_person_leads_or_belongs_to(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    await seed.member(event_engine, world.leader, world.band, active=False)
    await seed.role(event_engine, world.choir, "Tenor", [world.member])

    led = await api.get(CONTEXT, headers=principal(person_id=world.leader))
    belonging = await api.get(CONTEXT, headers=principal(person_id=world.member_person))
    outsider = await api.get(CONTEXT, headers=principal(person_id=world.stranger))
    no_person = await api.get(CONTEXT, headers=principal())

    by_name = {c["name"]: c for c in led.json()["collectives"]}
    assert set(by_name) == {"Choir", "Band"}
    assert by_name["Choir"]["is_principal"] is True
    assert by_name["Choir"]["member_id"] is None
    assert by_name["Band"]["is_principal"] is False
    assert by_name["Band"]["member_is_active"] is False
    mine = belonging.json()["collectives"]
    assert [(c["name"], c["is_principal"], c["member_id"]) for c in mine] == [
        ("Choir", False, str(world.member))
    ]
    assert mine[0]["is_verified"] is True
    assert [r["name"] for r in mine[0]["roles"]] == ["Tenor"]
    assert by_name["Band"]["roles"] == []
    assert outsider.json()["collectives"] == []
    assert no_person.json() == {"person_id": None, "collectives": []}


async def test_the_feed_goes_around_a_day_and_continues_both_ways(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    for offset in range(-3, 4):
        await seed.event(event_engine, f"E{offset:+d}", seed.day(offset), [world.choir])
    headers = principal(person_id=world.stranger)

    around = await api.get(
        FEED, params={"anchor": seed.iso(0), "limit": 2}, headers=headers
    )
    cursors = around.json()
    earlier = await api.get(
        FEED,
        params={"direction": "past", "cursor": cursors["past_cursor"], "limit": 2},
        headers=headers,
    )
    later = await api.get(
        FEED,
        params={"direction": "future", "cursor": cursors["future_cursor"], "limit": 2},
        headers=headers,
    )
    last = await api.get(
        FEED,
        params={
            "direction": "future",
            "cursor": later.json()["future_cursor"],
            "limit": 2,
        },
        headers=headers,
    )

    assert _names(around) == ["E-2", "E-1", "E+0", "E+1"]
    assert (cursors["has_more_past"], cursors["has_more_future"]) == (True, True)
    assert _names(earlier) == ["E-3"]
    assert (earlier.json()["has_more_past"], earlier.json()["has_more_future"]) == (
        False,
        False,
    )
    assert _names(later) == ["E+2", "E+3"]
    assert later.json()["has_more_future"] is False
    assert _names(last) == []


async def test_events_of_one_day_are_never_repeated_or_skipped_between_pages(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    for number in range(5):
        await seed.event(event_engine, f"Same{number}", seed.day(1), [world.choir])
    headers = principal(person_id=world.stranger)

    seen: list[str] = []
    params: dict[str, str | int] = {
        "direction": "future",
        "anchor": seed.iso(0),
        "limit": 2,
    }
    while True:
        page = await api.get(FEED, params=params, headers=headers)
        seen += _names(page)
        if not page.json()["has_more_future"]:
            break
        params["cursor"] = page.json()["future_cursor"]

    assert sorted(seen) == [f"Same{n}" for n in range(5)]


async def test_the_feed_applies_the_filters_of_the_home_page(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    await seed.event(
        event_engine,
        "Concert",
        seed.day(1),
        [world.choir],
        type="concert",
        level="regional",
    )
    await seed.event(
        event_engine,
        "Online",
        seed.day(2),
        [world.band],
        type="rehearsal",
        format="online",
    )
    await seed.event(event_engine, "Past", seed.day(-2), [world.choir], type="concert")
    headers = principal(person_id=world.stranger)
    base = {"anchor": seed.iso(0), "limit": 10}

    by_type = await api.get(FEED, params={**base, "type": ["concert"]}, headers=headers)
    by_level = await api.get(
        FEED, params={**base, "level": ["regional"]}, headers=headers
    )
    by_format = await api.get(
        FEED, params={**base, "format": ["online"]}, headers=headers
    )
    by_collective = await api.get(
        FEED, params={**base, "collective_id": [str(world.band)]}, headers=headers
    )
    upcoming = await api.get(
        FEED, params={**base, "date_from": seed.iso(0)}, headers=headers
    )

    assert _names(by_type) == ["Past", "Concert"]
    assert _names(by_level) == ["Concert"]
    assert _names(by_format) == ["Online"]
    assert _names(by_collective) == ["Online"]
    assert _names(upcoming) == ["Concert", "Online"]
    assert upcoming.json()["has_more_past"] is False


async def test_only_the_leaders_of_a_taking_part_collective_see_a_draft(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    await seed.event(event_engine, "Public", seed.day(1), [world.choir])
    await seed.event(event_engine, "Draft", seed.day(2), [world.choir], status="draft")
    await seed.event(event_engine, "Old", seed.day(3), [world.choir], status="archived")
    await seed.event(
        event_engine, "Model", seed.day(4), [world.choir], status="template"
    )
    params = {"anchor": seed.iso(0), "limit": 10}

    leader = await api.get(
        FEED, params=params, headers=principal(person_id=world.leader)
    )
    member = await api.get(
        FEED, params=params, headers=principal(person_id=world.member_person)
    )
    anonymous = await api.get(FEED, params=params, headers=principal())
    admin = await api.get(FEED, params=params, headers=principal(superuser=True))
    asked = await api.get(
        FEED,
        params={**params, "status": ["draft", "archived"]},
        headers=principal(person_id=world.stranger),
    )

    assert _names(leader) == ["Public", "Draft", "Old"]
    assert _names(member) == ["Public"]
    assert _names(anonymous) == ["Public"]
    assert _names(admin) == ["Public", "Draft", "Old"]
    assert _names(asked) == []


async def test_a_card_carries_the_place_the_time_and_the_callers_own_collectives(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    hall = await seed.location(event_engine, "Main hall", 55.0, 37.0)
    shared = await seed.event(
        event_engine, "Gala", seed.day(1), [world.choir, world.band], location_id=hall
    )
    start = datetime.datetime(2026, 11, 1, 10, 0, tzinfo=datetime.UTC)
    await seed.stage(
        event_engine, shared.id, start, start + datetime.timedelta(hours=2)
    )
    await seed.stage(
        event_engine, shared.id, start + datetime.timedelta(hours=3), None, "Party"
    )
    mine = await seed.attendance(
        event_engine, shared.of(world.choir), world.member, True, marked=True
    )
    colleague = await seed.member(
        event_engine, await seed.person(event_engine), world.choir
    )
    await seed.attendance(
        event_engine, shared.of(world.choir), colleague, False, marked=True
    )
    await seed.attendance(
        event_engine,
        shared.of(world.band),
        await seed.member(event_engine, await seed.person(event_engine), world.band),
        False,
    )

    response = await api.get(
        FEED,
        params={"anchor": seed.iso(0)},
        headers=principal(person_id=world.member_person),
    )

    [card] = response.json()["items"]
    assert card["location"] == {
        "id": str(hall),
        "name": "Main hall",
        "lat": 55.0,
        "lon": 37.0,
    }
    assert card["starts_at"].startswith("2026-11-01T10:00")
    assert card["ends_at"].startswith("2026-11-01T13:00")
    [participation] = card["participations"]
    assert participation["collective_name"] == "Choir"
    assert (participation["attended_count"], participation["total_count"]) == (1, 2)
    assert participation["my_attendance"]["id"] == str(mine)
    assert participation["my_attendance"]["is_attended"] is True


async def test_a_place_nobody_marked_has_no_value_and_is_not_counted(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    event = await seed.event(event_engine, "Gala", seed.day(1), [world.choir])
    await seed.attendance(event_engine, event.of(world.choir), world.member, True)
    colleague = await seed.member(
        event_engine, await seed.person(event_engine), world.choir
    )
    await seed.attendance(
        event_engine, event.of(world.choir), colleague, True, marked=True
    )

    response = await api.get(
        FEED,
        params={"anchor": seed.iso(0)},
        headers=principal(person_id=world.member_person),
    )

    [participation] = response.json()["items"][0]["participations"]
    assert participation["my_attendance"]["is_attended"] is None
    assert (participation["attended_count"], participation["total_count"]) == (1, 2)


async def test_cards_come_back_by_id_in_the_order_asked(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    first = await seed.event(event_engine, "First", seed.day(1), [world.choir])
    second = await seed.event(event_engine, "Second", seed.day(2), [world.choir])
    hidden = await seed.event(
        event_engine, "Hidden", seed.day(3), [world.choir], status="draft"
    )
    headers = principal(person_id=world.stranger)

    response = await api.get(
        f"{FEED}/cards",
        params={"id": [str(second.id), str(hidden.id), str(uuid4()), str(first.id)]},
        headers=headers,
    )
    empty = await api.get(f"{FEED}/cards", headers=headers)

    assert [c["name"] for c in response.json()] == ["Second", "First"]
    assert empty.status_code == 422


async def test_pending_lists_active_events_with_an_unmarked_place_of_the_caller(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    waiting = await seed.event(event_engine, "Waiting", seed.day(-1), [world.choir])
    marked = await seed.event(event_engine, "Marked", seed.day(-2), [world.choir])
    sealed = await seed.event(event_engine, "Sealed", seed.day(-3), [world.choir])
    draft = await seed.event(
        event_engine, "Draft", seed.day(1), [world.choir], status="draft"
    )
    await seed.attendance(event_engine, waiting.of(world.choir), world.member)
    await seed.attendance(
        event_engine, marked.of(world.choir), world.member, True, marked=True
    )
    await seed.attendance(
        event_engine, sealed.of(world.choir), world.member, verified=True
    )
    await seed.attendance(event_engine, draft.of(world.choir), world.member)

    response = await api.get(
        f"{FEED}/pending", headers=principal(person_id=world.member_person)
    )
    nothing = await api.get(
        f"{FEED}/pending", headers=principal(person_id=world.stranger)
    )

    assert [c["name"] for c in response.json()] == ["Waiting"]
    assert response.json()[0]["participations"][0]["my_attendance"]["edited_at"] is None
    assert nothing.json() == []


async def test_a_bad_cursor_is_refused(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    response = await api.get(
        FEED, params={"direction": "future", "cursor": "nonsense"}, headers=principal()
    )

    assert response.status_code == 422


async def test_a_change_of_a_place_moves_the_version_of_its_card(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    world = await _world(event_engine)
    shared = await seed.event(event_engine, "Gala", seed.day(1), [world.choir])
    place = await seed.attendance(event_engine, shared.of(world.choir), world.member)
    headers = principal(person_id=world.member_person)
    params = {"anchor": seed.iso(0)}

    before = (await api.get(FEED, params=params, headers=headers)).json()["items"][0]
    await api.patch(
        f"/event/v2/attendances/{place}", json={"is_attended": True}, headers=headers
    )
    after = (await api.get(FEED, params=params, headers=headers)).json()["items"][0]

    assert before["edited_at"] is None
    assert before["updated_at"] >= before["created_at"]
    assert after["updated_at"] > before["updated_at"]
    assert after["edited_at"] is None
