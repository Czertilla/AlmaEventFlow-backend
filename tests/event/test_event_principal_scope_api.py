from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1"
ADMIN = principal(superuser=True)


@dataclass
class Side:
    """One collective with its principal and a member, role and attendance."""

    collective: UUID
    person: UUID
    member: str
    role: str
    participation: str
    attendance: str

    @property
    def headers(self) -> dict[str, str]:
        return principal(person_id=self.person)


async def _sql(engine: AsyncEngine, sql: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _post(api: httpx.AsyncClient, path: str, body: dict[str, object]) -> str:
    response = await api.post(f"{BASE}{path}", json=body, headers=ADMIN)
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _side(
    api: httpx.AsyncClient, engine: AsyncEngine, name: str, event: str
) -> Side:
    person, collective = uuid4(), uuid4()
    await _sql(
        engine,
        "INSERT INTO person (id, surname, name) VALUES (:id, :name, 'P')",
        id=person,
        name=name,
    )
    await _sql(
        engine,
        "INSERT INTO organization (id, name, type, principal_id)"
        " VALUES (:id, :name, 'collective', :principal)",
        id=collective,
        name=name,
        principal=person,
    )
    await _sql(
        engine, "INSERT INTO collective (id, is_verified) VALUES (:id, true)", id=collective
    )
    member = await _post(
        api, "/members", {"collective_id": str(collective), "person_id": str(person)}
    )
    role = await _post(api, "/roles", {"collective_id": str(collective), "name": "R"})
    participation = await _post(
        api, "/participations", {"collective_id": str(collective), "event_id": event}
    )
    attendance = await _post(
        api, "/attendances", {"member_id": member, "participation_id": participation}
    )
    return Side(collective, person, member, role, participation, attendance)


async def _sides(
    api: httpx.AsyncClient, engine: AsyncEngine
) -> tuple[Side, Side]:
    event = await _post(api, "/events", {"name": "Concert"})
    return (
        await _side(api, engine, "Choir", event),
        await _side(api, engine, "Dance", event),
    )


async def _exists(api: httpx.AsyncClient, kind: str, entity_id: str) -> bool:
    response = await api.get(f"{BASE}/{kind}/{entity_id}", headers=ADMIN)
    return response.status_code == 200


async def test_a_principal_cannot_touch_members_of_another_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)
    path = f"{BASE}/me/collectives/{choir.collective}/members/{dance.member}"

    patched = await api.patch(path, json={"is_active": False}, headers=choir.headers)
    deleted = await api.delete(path, headers=choir.headers)

    assert patched.status_code == 404
    assert deleted.status_code == 404
    assert await _exists(api, "members", dance.member)


async def test_a_principal_cannot_touch_roles_of_another_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)
    path = f"{BASE}/me/collectives/{choir.collective}/roles/{dance.role}"

    patched = await api.patch(path, json={"name": "Hijacked"}, headers=choir.headers)
    deleted = await api.delete(path, headers=choir.headers)

    assert patched.status_code == 404
    assert deleted.status_code == 404
    assert (await api.get(f"{BASE}/roles/{dance.role}", headers=ADMIN)).json()[
        "name"
    ] == "R"


async def test_a_principal_cannot_touch_attendance_of_another_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)
    path = f"{BASE}/me/collectives/{choir.collective}/attendance/{dance.attendance}"

    read = await api.get(path, headers=choir.headers)
    patched = await api.patch(path, json={"is_attended": True}, headers=choir.headers)
    deleted = await api.delete(path, headers=choir.headers)

    assert [read.status_code, patched.status_code, deleted.status_code] == [404] * 3
    assert await _exists(api, "attendances", dance.attendance)


async def test_a_principal_cannot_verify_another_collectives_participation(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)
    path = (
        f"{BASE}/me/collectives/{choir.collective}"
        f"/participation/{dance.participation}/attendance/verify"
    )

    response = await api.post(path, headers=choir.headers)

    assert response.status_code == 404
    read = await api.get(f"{BASE}/attendances/{dance.attendance}", headers=ADMIN)
    assert read.json()["is_verified"] is False


async def test_a_principal_still_manages_their_own_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, _ = await _sides(api, event_engine)
    base = f"{BASE}/me/collectives/{choir.collective}"

    member = await api.patch(
        f"{base}/members/{choir.member}", json={"is_active": False}, headers=choir.headers
    )
    role = await api.patch(
        f"{base}/roles/{choir.role}", json={"name": "Lead"}, headers=choir.headers
    )
    attendance = await api.patch(
        f"{base}/attendance/{choir.attendance}",
        json={"is_attended": True},
        headers=choir.headers,
    )
    verified = await api.post(
        f"{base}/participation/{choir.participation}/attendance/verify",
        headers=choir.headers,
    )

    assert [r.status_code for r in (member, role, attendance, verified)] == [200] * 4
    assert role.json()["name"] == "Lead"
    assert verified.json()[0]["is_verified"] is True


async def test_attendees_of_a_new_participation_must_belong_to_the_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)
    event = await _post(api, "/events", {"name": "Second"})
    path = f"{BASE}/me/collectives/{choir.collective}/participations"

    foreign = await api.post(
        path,
        json={"event_id": event, "member_ids": [dance.member]},
        headers=choir.headers,
    )
    own = await api.post(
        path,
        json={"event_id": event, "member_ids": [choir.member]},
        headers=choir.headers,
    )

    assert foreign.status_code == 404
    assert own.status_code == 200, own.text
    listed = await api.get(
        f"{BASE}/attendances", params={"member_id": dance.member}, headers=ADMIN
    )
    assert [a["participation_id"] for a in listed.json()["items"]] == [
        dance.participation
    ]


async def test_attendees_of_a_new_event_must_belong_to_the_collective(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    choir, dance = await _sides(api, event_engine)

    foreign = await api.post(
        f"{BASE}/me/events",
        json={
            "name": "Rehearsal",
            "collective_id": str(choir.collective),
            "member_ids": [dance.member],
        },
        headers=choir.headers,
    )
    own = await api.post(
        f"{BASE}/me/events",
        json={
            "name": "Rehearsal",
            "collective_id": str(choir.collective),
            "member_ids": [choir.member],
        },
        headers=choir.headers,
    )

    assert foreign.status_code == 404
    assert own.status_code == 200, own.text
