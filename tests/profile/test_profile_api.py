from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/profile/v1"
ADMIN = principal(superuser=True)


async def _person(api: httpx.AsyncClient, surname: str = "Ivanov") -> UUID:
    response = await api.post(
        f"{BASE}/persons", json={"surname": surname, "name": "Ivan"}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return UUID(response.json()["id"])


async def _profile(api: httpx.AsyncClient, person_id: UUID) -> None:
    response = await api.post(
        f"{BASE}/profiles", json={"id": str(person_id)}, headers=ADMIN
    )
    assert response.status_code == 200, response.text


def _as(person_id: UUID) -> dict[str, str]:
    return principal(person_id=person_id)


async def test_person_read_exposes_timestamps(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)

    response = await api.get(f"{BASE}/persons/{person_id}", headers=ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["created_at"]
    assert response.json()["edited_at"] is None

    patched = await api.patch(
        f"{BASE}/persons/{person_id}", json={"name": "Petr"}, headers=ADMIN
    )
    assert patched.json()["edited_at"] is not None


async def test_my_contact_lifecycle(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    me = _as(person_id)

    created = await api.post(
        f"{BASE}/contacts/my",
        json={"type": "email", "value": "a@b.c"},
        headers=me,
    )
    contact_id = created.json()["id"]
    listed = await api.get(f"{BASE}/contacts/my", headers=me)
    replaced = await api.put(
        f"{BASE}/contacts/my/{contact_id}",
        json={"type": "phone", "value": "+7000", "is_main": True},
        headers=me,
    )
    patched = await api.patch(
        f"{BASE}/contacts/my/{contact_id}", json={"value": "+7111"}, headers=me
    )
    deleted = await api.delete(f"{BASE}/contacts/my/{contact_id}", headers=me)
    after = await api.get(f"{BASE}/contacts/my", headers=me)

    assert created.status_code == 200, created.text
    assert created.json()["person_id"] == str(person_id)
    assert created.json()["created_at"]
    assert [c["id"] for c in listed.json()["items"]] == [contact_id]
    assert replaced.status_code == 200, replaced.text
    assert (replaced.json()["type"], replaced.json()["is_main"]) == ("phone", True)
    assert patched.status_code == 200, patched.text
    assert (patched.json()["value"], patched.json()["is_main"]) == ("+7111", True)
    assert patched.json()["edited_at"] is not None
    assert deleted.status_code == 200
    assert after.json()["items"] == []


async def test_contact_endpoints_take_json_bodies(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    contact = await api.post(
        f"{BASE}/contacts",
        json={"person_id": str(person_id), "type": "email", "value": "a@b.c"},
        headers=ADMIN,
    )
    contact_id = contact.json()["id"]

    replaced = await api.put(
        f"{BASE}/contacts/{contact_id}",
        json={"person_id": str(person_id), "type": "tg", "value": "@ivan"},
        headers=ADMIN,
    )
    patched = await api.patch(
        f"{BASE}/contacts/{contact_id}", json={"is_main": True}, headers=ADMIN
    )

    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["value"] == "@ivan"
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_main"] is True
    assert patched.json()["value"] == "@ivan"


async def test_contacts_are_visible_only_to_their_owner_and_superusers(
    api: httpx.AsyncClient,
) -> None:
    owner_id = await _person(api)
    stranger_id = await _person(api, "Petrov")
    contact = await api.post(
        f"{BASE}/contacts",
        json={"person_id": str(owner_id), "type": "email", "value": "a@b.c"},
        headers=ADMIN,
    )
    contact_id = contact.json()["id"]

    own = await api.get(f"{BASE}/contacts/{contact_id}", headers=_as(owner_id))
    foreign = await api.get(f"{BASE}/contacts/{contact_id}", headers=_as(stranger_id))
    own_list = await api.get(
        f"{BASE}/persons/{owner_id}/contacts", headers=_as(owner_id)
    )
    foreign_list = await api.get(
        f"{BASE}/persons/{owner_id}/contacts", headers=_as(stranger_id)
    )
    forged = await api.post(
        f"{BASE}/contacts",
        json={"person_id": str(owner_id), "type": "email", "value": "x@y.z"},
        headers=_as(stranger_id),
    )

    assert own.status_code == 200
    assert foreign.status_code == 403
    assert own_list.status_code == 200
    assert foreign_list.status_code == 403
    assert forged.status_code == 403


async def test_diets_use_integer_ids_and_id_free_bodies(
    api: httpx.AsyncClient,
) -> None:
    created = await api.post(
        f"{BASE}/diets", json={"name": "Vegan", "description": "x"}, headers=ADMIN
    )
    diet_id = created.json()["id"]
    user = principal(person_id=uuid4())

    read = await api.get(f"{BASE}/diets/{diet_id}", headers=user)
    replaced = await api.put(
        f"{BASE}/diets/{diet_id}", json={"name": "Halal"}, headers=ADMIN
    )
    patched = await api.patch(
        f"{BASE}/diets/{diet_id}", json={"description": "no pork"}, headers=ADMIN
    )
    forbidden = await api.patch(
        f"{BASE}/diets/{diet_id}", json={"name": "Raw"}, headers=user
    )
    deleted = await api.delete(f"{BASE}/diets/{diet_id}", headers=ADMIN)
    gone = await api.get(f"{BASE}/diets/{diet_id}", headers=user)

    assert isinstance(diet_id, int)
    assert read.status_code == 200
    assert (replaced.json()["name"], replaced.json()["description"]) == ("Halal", None)
    assert (patched.json()["name"], patched.json()["description"]) == (
        "Halal",
        "no pork",
    )
    assert forbidden.status_code == 403
    assert deleted.status_code == 200
    assert gone.status_code == 404


async def test_my_profile_cannot_be_used_to_edit_somebody_elses(
    api: httpx.AsyncClient,
) -> None:
    mine = await _person(api)
    theirs = await _person(api, "Petrov")
    await _profile(api, mine)
    await _profile(api, theirs)

    replaced = await api.put(
        f"{BASE}/profiles/my",
        json={"id": str(theirs), "birthdate": "2000-01-02"},
        headers=_as(mine),
    )
    patched = await api.patch(
        f"{BASE}/profiles/my", json={"birthdate": "2001-02-03"}, headers=_as(mine)
    )
    own = await api.get(f"{BASE}/profiles/{mine}", headers=ADMIN)
    other = await api.get(f"{BASE}/profiles/{theirs}", headers=ADMIN)

    assert replaced.status_code == 200, replaced.text
    assert patched.status_code == 200, patched.text
    assert own.json()["birthdate"] == "2001-02-03"
    assert other.json()["birthdate"] is None
    assert own.json()["created_at"]


async def test_my_passport_lifecycle(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    await _profile(api, person_id)
    me = _as(person_id)
    body = {
        "number": "1234",
        "expire_date": "2030-01-01",
        "is_foreign": False,
        "name_variant": {"surname": "Ivanova", "name": "Anna"},
    }

    created = await api.post(f"{BASE}/passports/my", json=body, headers=me)
    passport_id = created.json()["id"]
    listed = await api.get(f"{BASE}/passports/my", headers=me)
    read = await api.get(f"{BASE}/passports/my/{passport_id}", headers=me)
    patched = await api.patch(
        f"{BASE}/passports/my/{passport_id}", json={"number": "9999"}, headers=me
    )
    replaced = await api.put(
        f"{BASE}/passports/my/{passport_id}",
        json={**body, "is_foreign": True},
        headers=me,
    )
    deleted = await api.delete(f"{BASE}/passports/my/{passport_id}", headers=me)
    after = await api.get(f"{BASE}/passports/my", headers=me)

    assert created.status_code == 200, created.text
    assert created.json()["profile_id"] == str(person_id)
    assert created.json()["created_at"]
    assert listed.json()["items"] == [
        {
            "id": passport_id,
            "number": "1234",
            "expire_date": "2030-01-01",
            "is_foreign": False,
        }
    ]
    assert read.json()["name_variant"]["surname"] == "Ivanova"
    assert patched.json()["number"] == "9999"
    assert patched.json()["edited_at"] is not None
    assert replaced.json()["is_foreign"] is True
    assert deleted.status_code == 200
    assert after.json()["items"] == []


async def test_a_passport_belongs_to_its_owner(api: httpx.AsyncClient) -> None:
    owner = await _person(api)
    stranger = await _person(api, "Petrov")
    await _profile(api, owner)
    await _profile(api, stranger)
    created = await api.post(
        f"{BASE}/passports/my",
        json={"number": "1", "expire_date": "2030-01-01", "is_foreign": False},
        headers=_as(owner),
    )
    passport_id = created.json()["id"]

    read = await api.get(f"{BASE}/passports/my/{passport_id}", headers=_as(stranger))
    patched = await api.patch(
        f"{BASE}/passports/my/{passport_id}",
        json={"number": "2"},
        headers=_as(stranger),
    )
    deleted = await api.delete(
        f"{BASE}/passports/my/{passport_id}", headers=_as(stranger)
    )
    as_admin = await api.get(f"{BASE}/passports/{passport_id}", headers=ADMIN)

    assert read.status_code == 403
    assert patched.status_code == 403
    assert deleted.status_code == 403
    assert as_admin.json()["number"] == "1"


async def test_name_variant_endpoints(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    await _profile(api, person_id)
    passport = await api.post(
        f"{BASE}/passports/my",
        json={"number": "1", "expire_date": "2030-01-01", "is_foreign": False},
        headers=_as(person_id),
    )
    passport_id = passport.json()["id"]
    url = f"{BASE}/passports/{passport_id}/name-variant"

    missing = await api.get(url, headers=ADMIN)
    put = await api.put(url, json={"surname": "Petrova", "name": "Olga"}, headers=ADMIN)
    read = await api.get(url, headers=ADMIN)
    patched = await api.patch(url, json={"name": "Maria"}, headers=ADMIN)
    deleted = await api.delete(url, headers=ADMIN)
    gone = await api.get(url, headers=ADMIN)

    assert missing.status_code == 404
    assert missing.json()["detail"] == "NAME_VARIANT_NOT_FOUND"
    assert put.status_code == 200, put.text
    assert read.json()["surname"] == "Petrova"
    assert (patched.json()["name"], patched.json()["surname"]) == ("Maria", "Petrova")
    assert deleted.status_code == 200
    assert gone.json()["detail"] == "NAME_VARIANT_NOT_FOUND"


async def _classroom(profile_engine: AsyncEngine, api: httpx.AsyncClient) -> int:
    faculty_id = uuid4()
    async with profile_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO organization (id, type) VALUES (:id, 'faculty')"),
            {"id": faculty_id},
        )
    degree = await api.post(
        f"{BASE}/students/degrees", json={"name": "Bachelor"}, headers=ADMIN
    )
    group = await api.post(
        f"{BASE}/students/groups",
        json={
            "name": "G-1",
            "degree_id": degree.json()["id"],
            "faculty_id": str(faculty_id),
            "grade": 1,
        },
        headers=ADMIN,
    )
    assert group.status_code == 200, group.text
    return group.json()["id"]


async def test_student_enrolment_lifecycle(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    group_id = await _classroom(profile_engine, api)
    person_id = await _person(api)
    await _profile(api, person_id)
    body = {"id": str(person_id), "student_id": "S-1", "group_id": group_id}

    forbidden = await api.post(f"{BASE}/students", json=body, headers=_as(person_id))
    created = await api.post(f"{BASE}/students", json=body, headers=ADMIN)
    again = await api.post(f"{BASE}/students", json=body, headers=ADMIN)
    patched = await api.patch(
        f"{BASE}/students/{person_id}", json={"is_budget": True}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/students/{person_id}",
        json={"student_id": "S-2", "group_id": group_id},
        headers=ADMIN,
    )
    read = await api.get(f"{BASE}/students/{person_id}", headers=_as(person_id))
    deleted = await api.delete(f"{BASE}/students/{person_id}", headers=ADMIN)
    gone = await api.get(f"{BASE}/students/{person_id}", headers=_as(person_id))
    profile = await api.get(f"{BASE}/profiles/{person_id}", headers=ADMIN)

    assert forbidden.status_code == 403
    assert created.status_code == 200, created.text
    assert created.json()["created_at"]
    assert created.json()["group"]["name"] == "G-1"
    assert again.status_code == 400
    assert again.json()["detail"] == "STUDENT_ALREADY_EXISTS"
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_budget"] is True
    assert replaced.status_code == 200, replaced.text
    assert (replaced.json()["student_id"], replaced.json()["is_budget"]) == (
        "S-2",
        None,
    )
    assert read.json()["person"]["id"] == str(person_id)
    assert deleted.status_code == 200
    assert gone.status_code == 404
    assert profile.status_code == 200


async def test_enrolling_requires_an_existing_profile(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    group_id = await _classroom(profile_engine, api)
    person_id = await _person(api)

    without_profile = await api.post(
        f"{BASE}/students",
        json={"id": str(person_id), "student_id": "S-1", "group_id": group_id},
        headers=ADMIN,
    )
    patching_nobody = await api.patch(
        f"{BASE}/students/{person_id}", json={"is_active": False}, headers=ADMIN
    )

    assert without_profile.status_code == 404
    assert without_profile.json()["detail"] == "PROFILE_NOT_FOUND"
    assert patching_nobody.status_code == 404
    assert patching_nobody.json()["detail"] == "STUDENT_NOT_FOUND"


async def test_degree_and_group_endpoints_use_integer_ids(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    group_id = await _classroom(profile_engine, api)

    group = await api.get(f"{BASE}/students/groups/{group_id}", headers=ADMIN)
    patched = await api.patch(
        f"{BASE}/students/groups/{group_id}", json={"grade": 2}, headers=ADMIN
    )

    assert group.status_code == 200, group.text
    assert patched.json()["grade"] == 2
