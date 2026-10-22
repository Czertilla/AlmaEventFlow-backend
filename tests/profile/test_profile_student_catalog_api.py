from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal
from support.org import FakeOrg

V1 = "/profile/v1"
STUDENTS = f"{V1}/students"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)
USER = principal()


async def _count(engine: AsyncEngine, table: str) -> int:
    async with engine.connect() as conn:
        return (
            await conn.execute(text(f"SELECT count(*) FROM {table}"))
        ).scalar_one()


async def _degree(api: httpx.AsyncClient, name: str = "Bachelor") -> int:
    response = await api.post(
        f"{STUDENTS}/degrees", json={"name": name}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _group(
    api: httpx.AsyncClient, degree: int, faculty: UUID, name: str = "IS-21"
) -> httpx.Response:
    return await api.post(
        f"{STUDENTS}/groups",
        json={
            "name": name,
            "degree_id": degree,
            "faculty_id": str(faculty),
            "grade": 2,
        },
        headers=ADMIN,
    )


async def _faculty(org: FakeOrg, name: str = "Law") -> UUID:
    university = org.add("university", f"Polytech {name}")
    return org.add("faculty", name, university.id).id


async def test_an_ordinary_user_cannot_make_a_degree(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    refused = await api.post(
        f"{V2}/student-degrees", json={"name": "Master"}, headers=USER
    )
    made = await api.post(
        f"{V2}/student-degrees", json={"name": "Master"}, headers=ADMIN
    )
    again = await api.post(
        f"{V2}/student-degrees", json={"name": "MASTER"}, headers=ADMIN
    )

    assert refused.status_code == 403
    assert made.status_code == 200, made.text
    assert again.json()["id"] == made.json()["id"]
    assert await _count(profile_engine, "student_degree") == 1


async def test_degrees_are_read_by_everyone_and_written_by_superusers_only(
    api: httpx.AsyncClient,
) -> None:
    degree = await _degree(api)

    listed = await api.get(f"{STUDENTS}/degrees", headers=USER)
    created = await api.post(
        f"{STUDENTS}/degrees", json={"name": "PhD"}, headers=USER
    )
    put = await api.put(
        f"{STUDENTS}/degrees/{degree}", json={"name": "PhD"}, headers=USER
    )
    patched = await api.patch(
        f"{STUDENTS}/degrees/{degree}", json={"name": "PhD"}, headers=USER
    )
    deleted = await api.delete(f"{STUDENTS}/degrees/{degree}", headers=USER)

    assert listed.status_code == 200, listed.text
    assert [d["name"] for d in listed.json()["items"]] == ["Bachelor"]
    assert [r.status_code for r in (created, put, patched, deleted)] == [
        403
    ] * 4


async def test_a_missing_degree_or_group_is_told_by_its_own_code(
    api: httpx.AsyncClient,
) -> None:
    degree_get = await api.get(f"{STUDENTS}/degrees/9999", headers=USER)
    degree_patch = await api.patch(
        f"{STUDENTS}/degrees/9999", json={"name": "PhD"}, headers=ADMIN
    )
    group_get = await api.get(f"{STUDENTS}/groups/9999", headers=USER)
    group_patch = await api.patch(
        f"{STUDENTS}/groups/9999", json={"name": "X"}, headers=ADMIN
    )

    assert degree_get.status_code == degree_patch.status_code == 404
    assert degree_get.json()["detail"] == "STUDENT_DEGREE_NOT_FOUND"
    assert degree_patch.json()["detail"] == "STUDENT_DEGREE_NOT_FOUND"
    assert group_get.status_code == group_patch.status_code == 404
    assert group_get.json()["detail"] == "STUDENT_GROUP_NOT_FOUND"
    assert group_patch.json()["detail"] == "STUDENT_GROUP_NOT_FOUND"


async def test_two_degrees_never_share_a_name(api: httpx.AsyncClient) -> None:
    first = await _degree(api, "Bachelor")
    second = await _degree(api, "Master")

    twin = await api.post(
        f"{STUDENTS}/degrees", json={"name": " bachelor "}, headers=ADMIN
    )
    renamed = await api.patch(
        f"{STUDENTS}/degrees/{second}", json={"name": "BACHELOR"}, headers=ADMIN
    )
    same = await api.patch(
        f"{STUDENTS}/degrees/{first}", json={"name": "bachelor"}, headers=ADMIN
    )

    assert twin.status_code == renamed.status_code == 409
    assert twin.json()["detail"] == "STUDENT_DEGREE_ALREADY_EXISTS"
    assert renamed.json()["detail"] == "STUDENT_DEGREE_ALREADY_EXISTS"
    assert same.status_code == 200, same.text


async def test_a_group_made_by_an_admin_takes_its_faculty_from_the_organization(
    api: httpx.AsyncClient, org: FakeOrg, profile_engine: AsyncEngine
) -> None:
    faculty = await _faculty(org)
    degree = await _degree(api)

    made = await _group(api, degree, faculty)

    assert made.status_code == 200, made.text
    assert made.json()["faculty_id"] == str(faculty)
    assert await _count(profile_engine, "organization") == 1


async def test_a_group_of_an_unknown_degree_or_faculty_is_refused(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    faculty = await _faculty(org)
    degree = await _degree(api)

    no_degree = await _group(api, 9999, faculty)
    no_faculty = await _group(api, degree, uuid4())

    assert no_degree.status_code == 404
    assert no_degree.json()["detail"] == "STUDENT_DEGREE_NOT_FOUND"
    assert no_faculty.status_code == 404
    assert no_faculty.json()["detail"] == "ORGANIZATION_NOT_FOUND"


async def test_an_admin_moves_a_group_to_another_faculty_and_degree(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    law = await _faculty(org, "Law")
    art = await _faculty(org, "Art")
    bachelor = await _degree(api, "Bachelor")
    master = await _degree(api, "Master")
    group = (await _group(api, bachelor, law)).json()["id"]

    moved = await api.patch(
        f"{STUDENTS}/groups/{group}",
        json={"faculty_id": str(art), "degree_id": master},
        headers=ADMIN,
    )
    missing_degree = await api.patch(
        f"{STUDENTS}/groups/{group}", json={"degree_id": 9999}, headers=ADMIN
    )
    missing_faculty = await api.patch(
        f"{STUDENTS}/groups/{group}",
        json={"faculty_id": str(uuid4())},
        headers=ADMIN,
    )

    assert moved.status_code == 200, moved.text
    assert (moved.json()["faculty_id"], moved.json()["degree_id"]) == (
        str(art),
        master,
    )
    assert missing_degree.json()["detail"] == "STUDENT_DEGREE_NOT_FOUND"
    assert missing_faculty.json()["detail"] == "ORGANIZATION_NOT_FOUND"


async def test_a_faculty_never_has_two_groups_of_one_name(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    law = await _faculty(org, "Law")
    art = await _faculty(org, "Art")
    degree = await _degree(api)
    first = (await _group(api, degree, law, "IS-21")).json()["id"]
    other = (await _group(api, degree, law, "IS-22")).json()["id"]
    elsewhere = await _group(api, degree, art, "IS-21")

    twin = await _group(api, degree, law, " is-21 ")
    renamed = await api.patch(
        f"{STUDENTS}/groups/{other}", json={"name": "IS-21"}, headers=ADMIN
    )
    same = await api.patch(
        f"{STUDENTS}/groups/{first}", json={"grade": 3}, headers=ADMIN
    )

    assert elsewhere.status_code == 200, elsewhere.text
    assert twin.status_code == renamed.status_code == 409
    assert twin.json()["detail"] == "STUDENT_GROUP_ALREADY_EXISTS"
    assert renamed.json()["detail"] == "STUDENT_GROUP_ALREADY_EXISTS"
    assert same.status_code == 200, same.text


async def test_a_degree_or_group_in_use_is_not_deleted(
    api: httpx.AsyncClient, org: FakeOrg
) -> None:
    faculty = await _faculty(org)
    degree = await _degree(api)
    group = (await _group(api, degree, faculty)).json()["id"]
    person = (
        await api.post(
            f"{V1}/persons",
            json={"surname": "Ivanov", "name": "Ivan"},
            headers=ADMIN,
        )
    ).json()["id"]
    await api.post(f"{V1}/profiles", json={"id": person}, headers=ADMIN)
    student = await api.post(
        STUDENTS,
        json={"id": person, "student_id": "S-1", "group_id": group},
        headers=ADMIN,
    )

    degree_in_use = await api.delete(
        f"{STUDENTS}/degrees/{degree}", headers=ADMIN
    )
    group_in_use = await api.delete(f"{STUDENTS}/groups/{group}", headers=ADMIN)
    await api.delete(f"{STUDENTS}/{person}", headers=ADMIN)
    group_free = await api.delete(f"{STUDENTS}/groups/{group}", headers=ADMIN)
    degree_free = await api.delete(
        f"{STUDENTS}/degrees/{degree}", headers=ADMIN
    )

    assert student.status_code == 200, student.text
    assert degree_in_use.status_code == group_in_use.status_code == 409
    assert degree_in_use.json()["detail"] == "STUDENT_DEGREE_IN_USE"
    assert group_in_use.json()["detail"] == "STUDENT_GROUP_IN_USE"
    assert group_free.status_code == degree_free.status_code == 200
