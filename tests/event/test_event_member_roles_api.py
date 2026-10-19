from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1"
ADMIN = principal(superuser=True)


@dataclass
class Seed:
    collective: UUID
    other_collective: UUID
    person: UUID


async def _insert(engine: AsyncEngine, sql: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _collective(engine: AsyncEngine, name: str) -> UUID:
    collective_id = uuid4()
    await _insert(
        engine,
        "INSERT INTO organization (id, name, type) VALUES (:id, :name, 'collective')",
        id=collective_id,
        name=name,
    )
    await _insert(
        engine,
        "INSERT INTO collective (id, is_verified) VALUES (:id, true)",
        id=collective_id,
    )
    return collective_id


async def _seed(engine: AsyncEngine) -> Seed:
    person = uuid4()
    await _insert(
        engine,
        "INSERT INTO person (id, surname, name) VALUES (:id, 'Ivanov', 'Ivan')",
        id=person,
    )
    return Seed(
        await _collective(engine, "Choir"),
        await _collective(engine, "Dance"),
        person,
    )


async def _role(api: httpx.AsyncClient, collective: UUID, name: str) -> str:
    response = await api.post(
        f"{BASE}/roles",
        json={"collective_id": str(collective), "name": name},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _member(
    api: httpx.AsyncClient, seed: Seed, roles: list[str] | None = None
) -> str:
    response = await api.post(
        f"{BASE}/members",
        json={
            "collective_id": str(seed.collective),
            "person_id": str(seed.person),
            "roles": roles or [],
        },
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _names(response: httpx.Response) -> list[str]:
    assert response.status_code == 200, response.text
    return sorted(role["name"] for role in response.json()["roles"])


async def test_patching_roles_replaces_the_set_of_a_member(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    singer = await _role(api, seed.collective, "Singer")
    soloist = await _role(api, seed.collective, "Soloist")
    member = await _member(api, seed, [singer])

    added = await api.patch(
        f"{BASE}/members/{member}", json={"roles": [singer, soloist]}, headers=ADMIN
    )
    swapped = await api.patch(
        f"{BASE}/members/{member}", json={"roles": [soloist]}, headers=ADMIN
    )
    cleared = await api.patch(
        f"{BASE}/members/{member}", json={"roles": []}, headers=ADMIN
    )

    assert _names(added) == ["Singer", "Soloist"]
    assert _names(swapped) == ["Soloist"]
    assert _names(cleared) == []


async def test_a_patch_without_roles_leaves_them_alone(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    singer = await _role(api, seed.collective, "Singer")
    member = await _member(api, seed, [singer])

    patched = await api.patch(
        f"{BASE}/members/{member}", json={"is_active": False}, headers=ADMIN
    )

    assert _names(patched) == ["Singer"]
    assert patched.json()["is_active"] is False


async def test_roles_and_activity_change_in_one_patch(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    singer = await _role(api, seed.collective, "Singer")
    soloist = await _role(api, seed.collective, "Soloist")
    member = await _member(api, seed, [singer])

    patched = await api.patch(
        f"{BASE}/members/{member}",
        json={"roles": [soloist], "is_active": False},
        headers=ADMIN,
    )
    read = await api.get(f"{BASE}/members/{member}", headers=ADMIN)

    assert _names(patched) == ["Soloist"]
    assert patched.json()["is_active"] is False
    assert _names(read) == ["Soloist"]
    assert patched.json()["edited_at"] is not None


async def test_a_role_of_another_collective_is_not_given_to_the_member(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    singer = await _role(api, seed.collective, "Singer")
    foreign = await _role(api, seed.other_collective, "Dancer")
    member = await _member(api, seed, [singer])

    patched = await api.patch(
        f"{BASE}/members/{member}", json={"roles": [singer, foreign]}, headers=ADMIN
    )

    assert _names(patched) == ["Singer"]


async def test_putting_a_member_replaces_the_roles_too(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    singer = await _role(api, seed.collective, "Singer")
    soloist = await _role(api, seed.collective, "Soloist")
    member = await _member(api, seed, [singer])

    swapped = await api.put(
        f"{BASE}/members/{member}",
        json={"roles": [soloist], "is_active": True},
        headers=ADMIN,
    )
    emptied = await api.put(
        f"{BASE}/members/{member}", json={"is_active": True}, headers=ADMIN
    )

    assert _names(swapped) == ["Soloist"]
    assert _names(emptied) == []
