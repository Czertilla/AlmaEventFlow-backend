from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1/me"


async def _collective_without_principal(engine: AsyncEngine) -> None:
    collective = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type)"
                " VALUES (:id, 'Orphans', 'collective')"
            ),
            {"id": collective},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective},
        )


async def test_an_account_without_a_person_has_no_collectives_and_no_memberships(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    await _collective_without_principal(event_engine)
    headers = principal()

    collectives = await api.get(f"{BASE}/collectives", headers=headers)
    members = await api.get(f"{BASE}/members", headers=headers)

    assert collectives.status_code == 200, collectives.text
    assert collectives.json() == []
    assert members.status_code == 200, members.text
    assert members.json() == []
