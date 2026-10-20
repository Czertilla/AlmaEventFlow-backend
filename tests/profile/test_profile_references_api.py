from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal
from support.org import FakeOrg

V2 = "/profile/v2"
V1 = "/profile/v1"
ADMIN = principal(superuser=True)
USER = principal()


async def _count(engine: AsyncEngine, table: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def _types(engine: AsyncEngine) -> dict[UUID, str]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT id, type FROM organization"))
        return {row.id: row.type for row in rows}


async def test_a_diet_is_found_by_its_name_or_made_once(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    made = await api.post(f"{V2}/diets", json={"name": "Vegan"}, headers=USER)
    again = await api.post(f"{V2}/diets", json={"name": "  vegan "}, headers=USER)
    other = await api.post(f"{V2}/diets", json={"name": "Halal"}, headers=USER)

    assert made.status_code == 200, made.text
    assert again.json()["id"] == made.json()["id"]
    assert other.json()["id"] != made.json()["id"]
    assert await _count(profile_engine, "diet") == 2


async def test_a_degree_is_found_by_its_name_or_made_once(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    made = await api.post(
        f"{V2}/student-degrees", json={"name": "Master"}, headers=USER
    )
    again = await api.post(
        f"{V2}/student-degrees", json={"name": "MASTER"}, headers=USER
    )

    assert again.json()["id"] == made.json()["id"]
    assert await _count(profile_engine, "student_degree") == 1


async def _group(
    api: httpx.AsyncClient, name: str, degree: int, faculty: UUID, grade: int = 2
) -> httpx.Response:
    return await api.post(
        f"{V2}/student-groups",
        json={
            "name": name,
            "degree_id": degree,
            "faculty_id": str(faculty),
            "grade": grade,
        },
        headers=USER,
    )


async def test_a_group_is_told_apart_by_its_faculty(
    api: httpx.AsyncClient, org: FakeOrg, profile_engine: AsyncEngine
) -> None:
    university = org.add("university", "Polytech")
    law = org.add("faculty", "Law", university.id)
    art = org.add("faculty", "Art", university.id)
    degree = (
        await api.post(f"{V2}/student-degrees", json={"name": "Bachelor"}, headers=USER)
    ).json()

    made = await _group(api, "IS-21", degree["id"], law.id)
    again = await _group(api, "is-21", degree["id"], law.id, grade=4)
    elsewhere = await _group(api, "IS-21", degree["id"], art.id)

    assert made.status_code == 200, made.text
    assert (made.json()["grade"], made.json()["faculty_id"]) == (2, str(law.id))
    assert again.json()["id"] == made.json()["id"]
    assert again.json()["grade"] == 2
    assert elsewhere.json()["id"] != made.json()["id"]
    assert await _count(profile_engine, "student_group") == 2
    assert set((await _types(profile_engine)).values()) == {"faculty"}


async def test_a_group_needs_a_degree_that_exists(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    university = org.add("university", "Polytech")
    law = org.add("faculty", "Law", university.id)

    response = await _group(api, "IS-21", 9999, law.id)

    assert response.status_code == 404
    assert response.json()["detail"] == "STUDENT_DEGREE_NOT_FOUND"


async def test_a_group_of_an_unknown_faculty_is_refused(api: httpx.AsyncClient) -> None:
    degree = (
        await api.post(f"{V2}/student-degrees", json={"name": "Bachelor"}, headers=USER)
    ).json()

    response = await _group(api, "IS-21", degree["id"], uuid4())

    assert response.status_code == 404
    assert response.json()["detail"] == "ORGANIZATION_NOT_FOUND"


async def test_universities_faculties_and_workplaces_come_from_the_organization(
    api: httpx.AsyncClient, org: FakeOrg, profile_engine: AsyncEngine
) -> None:
    university = await api.post(
        f"{V2}/universities", json={"name": "Polytech"}, headers=USER
    )
    again = await api.post(
        f"{V2}/universities", json={"name": "POLYTECH"}, headers=USER
    )
    faculty = await api.post(
        f"{V2}/faculties",
        json={"name": "Law", "university_id": university.json()["id"]},
        headers=USER,
    )
    workplace = await api.post(
        f"{V2}/organizations", json={"name": "Acme"}, headers=USER
    )

    assert university.status_code == 200, university.text
    assert again.json()["id"] == university.json()["id"]
    assert (faculty.json()["type"], workplace.json()["type"]) == (
        "faculty",
        "organization",
    )
    assert len(org.refs) == 3
    assert await _types(profile_engine) == {
        UUID(university.json()["id"]): "university",
        UUID(faculty.json()["id"]): "faculty",
        UUID(workplace.json()["id"]): "organization",
    }


async def test_a_faculty_needs_a_university_that_exists(api: httpx.AsyncClient) -> None:
    response = await api.post(
        f"{V2}/faculties",
        json={"name": "Law", "university_id": str(uuid4())},
        headers=USER,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "UNIVERSITY_NOT_FOUND"


async def test_a_silent_organization_service_is_a_503(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    org.down = True

    response = await api.post(
        f"{V2}/organizations", json={"name": "Acme"}, headers=USER
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "ORGANIZATION_SERVICE_UNAVAILABLE"


async def test_the_references_are_for_signed_in_verified_users_and_need_a_name(
    api: httpx.AsyncClient,
) -> None:
    anonymous = await api.post(f"{V2}/diets", json={"name": "Vegan"})
    unverified = await api.post(
        f"{V2}/diets", json={"name": "Vegan"}, headers=principal(verified=False)
    )
    blank = await api.post(f"{V2}/diets", json={"name": "   "}, headers=USER)
    long = await api.post(
        f"{V2}/student-degrees", json={"name": "x" * 33}, headers=USER
    )

    assert anonymous.status_code in (401, 403)
    assert unverified.status_code == 403
    assert (blank.status_code, long.status_code) == (422, 422)


async def test_a_workplace_unknown_to_profile_is_taken_from_the_organization_service(
    api: httpx.AsyncClient, org: FakeOrg, profile_engine: AsyncEngine
) -> None:
    acme = org.add("organization", "Acme")
    body: dict[str, Any] = {
        "surname": "Ivanova",
        "name": "Maria",
        "workplace_id": str(acme.id),
    }

    response = await api.post(f"{V2}/profiles/my", json=body, headers=principal())

    assert response.status_code == 200, response.text
    assert response.json()["workplace_id"] == str(acme.id)
    assert (await _types(profile_engine))[acme.id] == "organization"


async def test_a_new_workplace_made_in_the_same_form_flow_is_usable_at_once(
    api: httpx.AsyncClient,
) -> None:
    workplace = (
        await api.post(f"{V2}/organizations", json={"name": "Acme"}, headers=USER)
    ).json()

    response = await api.post(
        f"{V2}/profiles/my",
        json={"surname": "Ivanova", "name": "Maria", "workplace_id": workplace["id"]},
        headers=principal(),
    )

    assert response.status_code == 200, response.text
