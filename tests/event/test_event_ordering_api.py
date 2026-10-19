from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1"
ADMIN = principal(superuser=True)


async def _insert(engine: AsyncEngine, sql: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _collective(engine: AsyncEngine) -> UUID:
    collective_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO organization (id, name, type) VALUES (:id, 'Choir', 'collective')",
        id=collective_id,
    )
    await _insert(
        engine,
        "INSERT INTO collective (id, is_verified) VALUES (:id, true)",
        id=collective_id,
    )
    return collective_id


async def _member(
    api: httpx.AsyncClient,
    engine: AsyncEngine,
    collective: UUID,
    surname: str,
    patronymic: str | None = None,
) -> str:
    person = uuid4()
    await _insert(
        engine,
        "INSERT INTO person (id, surname, name, patronymic) "
        "VALUES (:id, :surname, 'X', :patronymic)",
        id=person,
        surname=surname,
        patronymic=patronymic,
    )
    response = await api.post(
        f"{BASE}/members",
        json={"collective_id": str(collective), "person_id": str(person)},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _ids(
    api: httpx.AsyncClient, path: str, **params: str | int
) -> list[str]:
    response = await api.get(f"{BASE}/{path}", params=params, headers=ADMIN)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


@pytest.mark.parametrize("order", ["edited_at", "-edited_at"])
async def test_members_never_edited_come_last_in_either_direction(
    api: httpx.AsyncClient, event_engine: AsyncEngine, order: str
) -> None:
    collective = await _collective(event_engine)
    untouched = await _member(api, event_engine, collective, "Alpha")
    edited = await _member(api, event_engine, collective, "Bravo")
    also_edited = await _member(api, event_engine, collective, "Charlie")
    await api.patch(f"{BASE}/members/{edited}", json={"is_active": True}, headers=ADMIN)
    await api.patch(
        f"{BASE}/members/{also_edited}", json={"is_active": True}, headers=ADMIN
    )

    ids = await _ids(api, "members", order_by=order)

    assert ids[-1] == untouched
    assert set(ids[:2]) == {edited, also_edited}
    assert ids[:2] == (
        [edited, also_edited] if order == "edited_at" else [also_edited, edited]
    )


async def test_members_without_a_patronymic_come_last_when_it_sorts_descending(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective = await _collective(event_engine)
    plain = await _member(api, event_engine, collective, "Alpha")
    first = await _member(api, event_engine, collective, "Bravo", "Antonovich")
    second = await _member(api, event_engine, collective, "Charlie", "Borisovich")

    descending = await _ids(api, "members", order_by="-person__patronymic")
    ascending = await _ids(api, "members", order_by="person__patronymic")

    assert descending == [second, first, plain]
    assert ascending == [first, second, plain]


async def test_pages_of_members_that_tie_on_the_sort_key_never_repeat_or_skip(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective = await _collective(event_engine)
    members = [
        await _member(api, event_engine, collective, f"Surname{n}") for n in range(7)
    ]

    pages: list[str] = []
    for page in range(4):
        pages += await _ids(api, "members", order_by="is_active", limit=2, page=page)

    assert pages == sorted(members)


async def test_events_never_edited_come_last_when_edited_at_sorts_descending(
    api: httpx.AsyncClient,
) -> None:
    created = [
        (
            await api.post(
                f"{BASE}/events", json={"name": f"Event {n}"}, headers=ADMIN
            )
        ).json()["id"]
        for n in range(3)
    ]
    await api.patch(
        f"{BASE}/events/{created[1]}", json={"name": "Renamed"}, headers=ADMIN
    )

    ids = await _ids(api, "events", order_by="-edited_at")

    assert ids[0] == created[1]
    assert set(ids[1:]) == {created[0], created[2]}
