import importlib.util
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/org/v1"
ADMIN = principal(superuser=True)
USER = principal()
BACKFILL = next(
    Path(__file__).resolve().parents[2].glob("migrations/versions/org/*backfill*.py")
)


async def _make(api: httpx.AsyncClient, kind: str, name: str, **extra: object) -> str:
    response = await api.post(
        f"{BASE}/{kind}", json={"name": name, **extra}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _count(engine: AsyncEngine, table: str, entity_id: str) -> int:
    async with engine.connect() as conn:
        return (
            await conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE id = :id"), {"id": entity_id}
            )
        ).scalar_one()


async def test_a_faculty_is_attached_only_to_a_university(
    api: httpx.AsyncClient,
) -> None:
    university = await _make(api, "universities", "MSU")
    plain = await _make(api, "organizations", "Acme")
    faculty = await _make(api, "faculties", "Math", university_id=university)

    to_plain = await api.post(
        f"{BASE}/faculties",
        json={"name": "Law", "university_id": plain},
        headers=ADMIN,
    )
    to_unknown = await api.post(
        f"{BASE}/faculties",
        json={"name": "Art", "university_id": str(uuid4())},
        headers=ADMIN,
    )
    patched = await api.patch(
        f"{BASE}/faculties/{faculty}", json={"university_id": plain}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/faculties/{faculty}",
        json={"name": "Math", "university_id": plain},
        headers=ADMIN,
    )
    kept = await api.get(f"{BASE}/faculties/{faculty}", headers=USER)

    for refused in (to_plain, to_unknown, patched, replaced):
        assert refused.status_code == 404, refused.text
        assert refused.json()["detail"] == "UNIVERSITY_NOT_FOUND"
    assert kept.json()["university_id"] == university


async def test_a_collective_is_attached_only_to_a_university(
    api: httpx.AsyncClient,
) -> None:
    university = await _make(api, "universities", "MSU")
    plain = await _make(api, "organizations", "Acme")
    collective = await _make(api, "collectives", "Choir", university_id=university)

    to_plain = await api.post(
        f"{BASE}/collectives",
        json={"name": "Club", "university_id": plain},
        headers=ADMIN,
    )
    patched = await api.patch(
        f"{BASE}/collectives/{collective}",
        json={"university_id": plain},
        headers=ADMIN,
    )
    cleared = await api.patch(
        f"{BASE}/collectives/{collective}",
        json={"university_id": None},
        headers=ADMIN,
    )

    assert to_plain.status_code == patched.status_code == 404
    assert to_plain.json()["detail"] == "UNIVERSITY_NOT_FOUND"
    assert cleared.status_code == 200, cleared.text


async def test_deleting_through_the_typed_endpoint_removes_the_organization_too(
    api: httpx.AsyncClient, org_engine: AsyncEngine
) -> None:
    university = await _make(api, "universities", "MSU")
    faculty = await _make(api, "faculties", "Math")
    collective = await _make(api, "collectives", "Choir")

    for kind, entity_id in (
        ("universities", university),
        ("faculties", faculty),
        ("collectives", collective),
    ):
        deleted = await api.delete(f"{BASE}/{kind}/{entity_id}", headers=ADMIN)
        assert deleted.status_code == 200, deleted.text

    for entity_id in (university, faculty, collective):
        read = await api.get(f"{BASE}/organizations/{entity_id}", headers=USER)
        assert read.status_code == 404, read.text
        assert await _count(org_engine, "organization", entity_id) == 0


async def test_a_university_with_faculties_cannot_be_deleted(
    api: httpx.AsyncClient, org_engine: AsyncEngine
) -> None:
    university = await _make(api, "universities", "MSU")
    faculty = await _make(api, "faculties", "Math", university_id=university)

    typed = await api.delete(f"{BASE}/universities/{university}", headers=ADMIN)
    generic = await api.delete(f"{BASE}/organizations/{university}", headers=ADMIN)

    assert typed.status_code == generic.status_code == 409
    assert typed.json()["detail"] == "UNIVERSITY_HAS_FACULTIES"
    assert generic.json()["detail"] == "UNIVERSITY_HAS_FACULTIES"
    assert await _count(org_engine, "university", university) == 1
    assert await _count(org_engine, "faculty", faculty) == 1

    await api.delete(f"{BASE}/faculties/{faculty}", headers=ADMIN)
    freed = await api.delete(f"{BASE}/organizations/{university}", headers=ADMIN)

    assert freed.status_code == 200, freed.text
    assert await _count(org_engine, "organization", university) == 0


async def test_the_backfill_gives_every_typed_organization_its_own_row(
    api: httpx.AsyncClient, org_engine: AsyncEngine
) -> None:
    university = await _make(api, "universities", "MSU")
    faculty = await _make(api, "faculties", "Math")
    collective = await _make(api, "collectives", "Choir")
    plain = await _make(api, "organizations", "Acme")
    async with org_engine.begin() as conn:
        for table, entity_id in (
            ("university", university),
            ("faculty", faculty),
            ("collective", collective),
        ):
            await conn.execute(
                text(f"DELETE FROM {table} WHERE id = :id"), {"id": entity_id}
            )
    spec = importlib.util.spec_from_file_location("org_backfill", BACKFILL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    async with org_engine.begin() as conn:
        for statement in module.BACKFILL:
            await conn.execute(text(statement))
        for statement in module.BACKFILL:
            await conn.execute(text(statement))

    assert await _count(org_engine, "university", university) == 1
    assert await _count(org_engine, "faculty", faculty) == 1
    assert await _count(org_engine, "collective", collective) == 1
    for table in ("university", "faculty", "collective"):
        assert await _count(org_engine, table, plain) == 0
    listed = await api.get(f"{BASE}/universities", headers=USER)
    assert [u["id"] for u in listed.json()["items"]] == [university]
