from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1/collectives"
ADMIN = principal(superuser=True)


async def _person(engine: AsyncEngine) -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO person (id, surname, name) VALUES (:id, 'Lead', 'Ivan')"),
            {"id": person_id},
        )
    return person_id


async def _collective(
    engine: AsyncEngine, name: str, *, verified: bool, leader: UUID | None = None
) -> UUID:
    collective_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type, principal_id) "
                "VALUES (:id, :name, 'collective', :leader)"
            ),
            {"id": collective_id, "name": name, "leader": leader},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, :verified)"),
            {"id": collective_id, "verified": verified},
        )
    return collective_id


async def test_the_administration_lists_collectives_by_confirmation(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    await _collective(event_engine, "A-waiting", verified=False)
    await _collective(event_engine, "B-confirmed", verified=True)
    await _collective(event_engine, "C-waiting", verified=False)

    everyone = await api.get(BASE, headers=ADMIN)
    waiting = await api.get(BASE, params={"is_verified": False}, headers=ADMIN)
    found = await api.get(BASE, params={"search": "confirmed"}, headers=ADMIN)
    confirmed_first = await api.get(
        BASE, params={"order_by": "-is_verified,name"}, headers=ADMIN
    )

    assert [c["name"] for c in everyone.json()["items"]] == [
        "A-waiting",
        "B-confirmed",
        "C-waiting",
    ]
    assert [c["name"] for c in waiting.json()["items"]] == ["A-waiting", "C-waiting"]
    assert [c["name"] for c in found.json()["items"]] == ["B-confirmed"]
    assert confirmed_first.json()["items"][0]["name"] == "B-confirmed"
    assert waiting.json()["pagination"]["total"] == 2


async def test_a_list_of_collectives_is_taken_by_ids(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    first = await _collective(event_engine, "First", verified=True)
    await _collective(event_engine, "Second", verified=False)
    third = await _collective(event_engine, "Third", verified=False)

    response = await api.get(BASE, params={"id__in": f"{first},{third}"}, headers=ADMIN)

    assert [c["id"] for c in response.json()["items"]] == [str(first), str(third)]


async def test_the_administration_confirms_and_withdraws(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective = await _collective(event_engine, "Choir", verified=False)

    confirmed = await api.patch(
        f"{BASE}/{collective}", json={"is_verified": True}, headers=ADMIN
    )
    read = await api.get(f"{BASE}/{collective}", headers=ADMIN)
    untouched = await api.patch(f"{BASE}/{collective}", json={}, headers=ADMIN)
    withdrawn = await api.patch(
        f"{BASE}/{collective}", json={"is_verified": False}, headers=ADMIN
    )

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["is_verified"] is True
    assert (confirmed.json()["name"], read.json()["is_verified"]) == ("Choir", True)
    assert untouched.json()["is_verified"] is True
    assert withdrawn.json()["is_verified"] is False


async def test_only_a_superuser_reaches_the_confirmation(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    leader = await _person(event_engine)
    collective = await _collective(event_engine, "Choir", verified=False, leader=leader)
    headers = principal(person_id=leader)

    listed = await api.get(BASE, headers=headers)
    read = await api.get(f"{BASE}/{collective}", headers=headers)
    patched = await api.patch(
        f"{BASE}/{collective}", json={"is_verified": True}, headers=headers
    )

    assert [listed.status_code, read.status_code, patched.status_code] == [403] * 3


async def test_an_unknown_collective_is_not_found(api: httpx.AsyncClient) -> None:
    response = await api.patch(
        f"{BASE}/{uuid4()}", json={"is_verified": True}, headers=ADMIN
    )

    assert response.status_code == 404


async def test_a_leader_creates_events_once_the_administration_confirmed_the_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    leader = await _person(event_engine)
    collective = await _collective(event_engine, "Choir", verified=False, leader=leader)
    headers = principal(person_id=leader)
    body = {"name": "Rehearsal", "collective_id": str(collective)}

    before = await api.post("/event/v1/me/events", json=body, headers=headers)
    await api.patch(f"{BASE}/{collective}", json={"is_verified": True}, headers=ADMIN)
    after = await api.post("/event/v1/me/events", json=body, headers=headers)
    mine = await api.get("/event/v1/me/collectives", headers=headers)

    assert before.status_code == 403
    assert before.json()["detail"] == "COLLECTIVE_NOT_VERIFIED"
    assert after.status_code == 200, after.text
    assert mine.json()[0]["is_verified"] is True
