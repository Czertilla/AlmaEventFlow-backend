from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1"
ADMIN = principal(superuser=True)


async def _sql(engine: AsyncEngine, sql: str, **params: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(sql), params)


async def _collective_with_template(
    api: httpx.AsyncClient, engine: AsyncEngine
) -> tuple[UUID, UUID, dict[str, str]]:
    person, collective = uuid4(), uuid4()
    await _sql(
        engine,
        "INSERT INTO person (id, surname, name) VALUES (:id, 'P', 'P')",
        id=person,
    )
    await _sql(
        engine,
        "INSERT INTO organization (id, name, type, principal_id)"
        " VALUES (:id, 'Choir', 'collective', :principal)",
        id=collective,
        principal=person,
    )
    await _sql(
        engine,
        "INSERT INTO collective (id, is_verified) VALUES (:id, true)",
        id=collective,
    )
    template = await api.post(
        f"{BASE}/events",
        json={
            "name": "Weekly",
            "status": "template",
            "type": "concert",
            "level": "regional",
        },
        headers=ADMIN,
    )
    assert template.status_code == 200, template.text
    template_id = UUID(template.json()["id"])
    joined = await api.post(
        f"{BASE}/participations",
        json={"collective_id": str(collective), "event_id": str(template_id)},
        headers=ADMIN,
    )
    assert joined.status_code == 200, joined.text
    return collective, template_id, principal(person_id=person)


async def test_templates_of_a_collective_are_listed(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective, template_id, headers = await _collective_with_template(
        api, event_engine
    )

    response = await api.get(
        f"{BASE}/me/collectives/{collective}/templates", headers=headers
    )

    assert response.status_code == 200, response.text
    assert [(e["id"], e["type"], e["level"]) for e in response.json()] == [
        (str(template_id), "concert", "regional")
    ]


async def test_an_event_can_start_from_a_template(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective, template_id, headers = await _collective_with_template(
        api, event_engine
    )

    response = await api.post(
        f"{BASE}/me/events",
        json={
            "name": "Rehearsal",
            "collective_id": str(collective),
            "template_id": str(template_id),
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["name"], body["type"], body["level"]) == (
        "Rehearsal",
        "concert",
        "regional",
    )
