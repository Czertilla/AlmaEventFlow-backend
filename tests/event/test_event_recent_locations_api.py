import datetime
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v2/collectives"


@dataclass
class Seed:
    leader: UUID
    other_leader: UUID
    collective: UUID
    other_collective: UUID


async def _insert(engine: AsyncEngine, sql: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _person(engine: AsyncEngine, surname: str) -> UUID:
    person_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO person (id, surname, name) VALUES (:id, :surname, 'X')",
        id=person_id,
        surname=surname,
    )
    return person_id


async def _collective(engine: AsyncEngine, name: str, leader: UUID) -> UUID:
    collective_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO organization (id, name, type, principal_id) "
        "VALUES (:id, :name, 'collective', :leader)",
        id=collective_id,
        name=name,
        leader=leader,
    )
    await _insert(
        engine,
        "INSERT INTO collective (id, is_verified) VALUES (:id, true)",
        id=collective_id,
    )
    return collective_id


async def _seed(engine: AsyncEngine) -> Seed:
    await _insert(
        engine,
        "INSERT INTO event_status (id, name) VALUES (1, 's') ON CONFLICT DO NOTHING",
    )
    leader = await _person(engine, "Leader")
    other_leader = await _person(engine, "Other")
    return Seed(
        leader,
        other_leader,
        await _collective(engine, "Choir", leader),
        await _collective(engine, "Dance", other_leader),
    )


async def _place(engine: AsyncEngine, name: str | None) -> UUID:
    location_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO location (id, name) VALUES (:id, :name)",
        id=location_id,
        name=name,
    )
    return location_id


async def _event(
    engine: AsyncEngine,
    collective: UUID,
    location: UUID | None,
    *,
    created: str,
    edited: str | None = None,
) -> UUID:
    event_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO event (id, name, status_id, location_id, created_at, edited_at) "
        "VALUES (:id, 'E', 1, :location, :created, :edited)",
        id=event_id,
        location=location,
        created=datetime.datetime.fromisoformat(created),
        edited=datetime.datetime.fromisoformat(edited) if edited else None,
    )
    await _insert(
        engine,
        "INSERT INTO participation (id, collective_id, event_id, created_at) "
        "VALUES (:id, :collective, :event, now())",
        id=uuid4(),
        collective=collective,
        event=event_id,
    )
    return event_id


def _url(collective: UUID, **params: int) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"{BASE}/{collective}/recent-locations" + (f"?{query}" if query else "")


async def test_places_come_latest_first_by_edit_or_creation_time(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    hall = await _place(event_engine, "Hall")
    park = await _place(event_engine, "Park")
    club = await _place(event_engine, "Club")
    await _event(event_engine, seed.collective, hall, created="2026-01-01T10:00Z")
    await _event(
        event_engine,
        seed.collective,
        park,
        created="2026-01-02T10:00Z",
        edited="2026-03-01T10:00Z",
    )
    await _event(event_engine, seed.collective, club, created="2026-02-01T10:00Z")

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert response.status_code == 200, response.text
    assert [i["location_id"] for i in response.json()] == [
        str(park),
        str(club),
        str(hall),
    ]


async def test_a_place_is_listed_once_at_its_latest_use(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    hall = await _place(event_engine, "Hall")
    park = await _place(event_engine, "Park")
    await _event(event_engine, seed.collective, hall, created="2026-01-01T10:00Z")
    await _event(event_engine, seed.collective, park, created="2026-02-01T10:00Z")
    await _event(event_engine, seed.collective, hall, created="2026-03-01T10:00Z")

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    items = response.json()
    assert [i["location_id"] for i in items] == [str(hall), str(park)]
    assert items[0]["used_at"].startswith("2026-03-01T10:00")


async def test_only_the_collectives_own_events_with_a_place_count(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    mine = await _place(event_engine, "Mine")
    theirs = await _place(event_engine, "Theirs")
    await _event(event_engine, seed.collective, mine, created="2026-01-01T10:00Z")
    await _event(event_engine, seed.collective, None, created="2026-02-01T10:00Z")
    await _event(
        event_engine, seed.other_collective, theirs, created="2026-03-01T10:00Z"
    )

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert [i["location_id"] for i in response.json()] == [str(mine)]


async def test_an_address_only_place_without_a_name_is_still_a_recent_place(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    proxy = await _place(event_engine, None)
    await _event(event_engine, seed.collective, proxy, created="2026-01-01T10:00Z")

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert [i["location_id"] for i in response.json()] == [str(proxy)]


async def test_limit_keeps_the_latest_places(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    places = [await _place(event_engine, f"P{n}") for n in range(3)]
    for n, place in enumerate(places):
        await _event(
            event_engine, seed.collective, place, created=f"2026-01-0{n + 1}T10:00Z"
        )

    response = await api.get(
        _url(seed.collective, limit=2), headers=principal(person_id=seed.leader)
    )

    assert [i["location_id"] for i in response.json()] == [
        str(places[2]),
        str(places[1]),
    ]


async def test_a_collective_without_events_has_no_recent_places(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_only_the_leader_or_a_superuser_may_read_them(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    hall = await _place(event_engine, "Hall")
    await _event(event_engine, seed.collective, hall, created="2026-01-01T10:00Z")
    url = _url(seed.collective)

    assert (await api.get(url)).status_code == 401
    stranger = await api.get(url, headers=principal(person_id=seed.other_leader))
    assert stranger.status_code == 403
    admin = await api.get(url, headers=principal(superuser=True))
    assert admin.status_code == 200
    assert [i["location_id"] for i in admin.json()] == [str(hall)]
    missing = await api.get(_url(uuid4()), headers=principal(superuser=True))
    assert missing.status_code == 404


async def test_limit_is_bounded(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    headers = principal(person_id=seed.leader)

    for limit in (0, 51):
        response = await api.get(_url(seed.collective, limit=limit), headers=headers)
        assert response.status_code == 422
