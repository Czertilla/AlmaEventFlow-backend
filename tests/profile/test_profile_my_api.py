import asyncio
from typing import Any
from uuid import UUID, uuid4

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import AsPerson, principal

V1 = "/profile/v1"
V2 = "/profile/v2/profiles/my"
ADMIN = principal(superuser=True)


async def _count(engine: AsyncEngine, table: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def _classroom(engine: AsyncEngine, api: httpx.AsyncClient) -> dict[str, Any]:
    faculty_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO organization (id, type) VALUES (:id, 'faculty')"),
            {"id": faculty_id},
        )
    degree = await api.post(
        f"{V1}/students/degrees", json={"name": "Bachelor"}, headers=ADMIN
    )
    group = await api.post(
        f"{V1}/students/groups",
        json={
            "name": "G-1",
            "degree_id": degree.json()["id"],
            "faculty_id": str(faculty_id),
            "grade": 1,
        },
        headers=ADMIN,
    )
    diet = await api.post(f"{V1}/diets", json={"name": "Vegan"}, headers=ADMIN)
    return {
        "faculty": str(faculty_id),
        "group": group.json()["id"],
        "diet": diet.json()["id"],
    }


def _form(seed: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "surname": "Ivanova",
        "name": "Maria",
        "patronymic": "Sergeevna",
        "birthdate": "2004-05-06",
        "workplace_id": seed["faculty"],
        "diet_id": seed["diet"],
        "student": {
            "student_id": "S-77",
            "group_id": seed["group"],
            "faculty_id": seed["faculty"],
            "is_budget": True,
        },
        "contacts": [
            {"type": "email", "value": "m@example.com", "is_main": True},
            {"type": "tg", "value": "@maria"},
        ],
    }
    return body | overrides


def _newcomer() -> tuple[UUID, dict[str, str]]:
    user_id = uuid4()
    return user_id, principal(user_id=user_id)


async def test_a_user_makes_the_whole_profile_in_one_request(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
) -> None:
    seed = await _classroom(profile_engine, api)
    user_id, headers = _newcomer()

    response = await api.post(V2, json=_form(seed), headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["surname"], body["name"], body["patronymic"]) == (
        "Ivanova",
        "Maria",
        "Sergeevna",
    )
    assert body["birthdate"] == "2004-05-06"
    assert body["diet"]["name"] == "Vegan"
    assert body["student"]["student_id"] == "S-77"
    assert body["student"]["group"]["name"] == "G-1"
    assert [(c["type"], c["is_main"]) for c in body["contacts"]] == [
        ("email", True),
        ("tg", True),
    ]
    assert [name for name, _ in published] == [
        "on_person_created",
        "on_person_link_changed",
    ]
    link = published[1][1][0]
    assert (link.user_id, str(link.person_id)) == (user_id, body["id"])
    for table in ("person", "person_account", "profile", "student", "contact"):
        assert await _count(profile_engine, table) >= 1


async def test_the_profile_is_found_by_the_link_not_by_the_token(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()
    before = await api.get(V2, headers=headers)
    created = await api.post(V2, json=_form(seed), headers=headers)

    after = await api.get(V2, headers=headers)
    v1 = await api.get(f"{V1}/persons/my", headers=headers)

    assert before.status_code == 404
    assert before.json()["detail"] == "PROFILE_NOT_FOUND"
    assert after.status_code == 200
    assert after.json()["id"] == created.json()["id"]
    assert v1.status_code == 200
    assert v1.json()["surname"] == "Ivanova"


async def test_a_second_profile_is_refused(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()
    await api.post(V2, json=_form(seed), headers=headers)
    published.clear()

    again = await api.post(V2, json=_form(seed, surname="Other"), headers=headers)

    assert again.status_code == 403
    assert again.json()["detail"] == "PROFILE_ALREADY_EXISTS"
    assert await _count(profile_engine, "person") == 1
    assert published == []


async def test_two_simultaneous_attempts_make_one_profile(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()

    first, second = await asyncio.gather(
        api.post(V2, json=_form(seed), headers=headers),
        api.post(V2, json=_form(seed), headers=headers),
    )

    assert sorted([first.status_code, second.status_code]) == [200, 403]
    assert await _count(profile_engine, "person") == 1
    assert await _count(profile_engine, "person_account") == 1


@pytest.mark.parametrize(
    ("override", "detail"),
    [
        ({"diet_id": 9999}, "DIET_NOT_FOUND"),
        ({"workplace_id": str(uuid4())}, "ORGANIZATION_NOT_FOUND"),
        ({"student": {"student_id": "S", "group_id": 9999}}, "STUDENT_GROUP_NOT_FOUND"),
    ],
)
async def test_a_bad_reference_leaves_nothing_behind(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
    override: dict[str, Any],
    detail: str,
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()

    response = await api.post(V2, json=_form(seed, **override), headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == detail
    for table in ("person", "person_account", "profile", "student", "contact"):
        assert await _count(profile_engine, table) == 0
    assert published == []


async def test_a_claimed_person_without_a_link_blocks_a_second_profile(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    existing = (
        await api.post(
            f"{V1}/persons", json={"surname": "Old", "name": "Record"}, headers=ADMIN
        )
    ).json()["id"]
    stale = principal(person_id=UUID(existing))
    ghost = principal(person_id=uuid4())

    blocked = await api.post(V2, json=_form(seed), headers=stale)
    allowed = await api.post(V2, json=_form(seed), headers=ghost)

    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "ACCOUNT_LINK_OUT_OF_SYNC"
    assert allowed.status_code == 200, allowed.text


async def test_the_profile_is_replaced_as_a_whole(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()
    created = (await api.post(V2, json=_form(seed), headers=headers)).json()
    kept = created["contacts"][0]
    published.clear()

    replaced = await api.put(
        V2,
        json=_form(
            seed,
            name="Anna",
            birthdate=None,
            diet_id=None,
            student=None,
            contacts=[
                {"id": kept["id"], "type": "phone", "value": "+7000", "is_main": True},
                {"type": "vk", "value": "anna"},
            ],
        ),
        headers=headers,
    )

    assert replaced.status_code == 200, replaced.text
    body = replaced.json()
    assert (body["id"], body["name"]) == (created["id"], "Anna")
    assert body["birthdate"] is None and body["diet"] is None
    assert body["student"] is None
    assert body["edited_at"] is not None
    assert [(c["type"], c["value"], c["is_main"]) for c in body["contacts"]] == [
        ("phone", "+7000", True),
        ("vk", "anna", True),
    ]
    assert body["contacts"][0]["id"] == kept["id"]
    assert [name for name, _ in published if name != "on_person_link_changed"] == [
        "on_person_updated"
    ]
    assert await _count(profile_engine, "student") == 0
    assert await _count(profile_engine, "contact") == 2


async def test_a_student_card_can_be_added_later(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()
    await api.post(V2, json=_form(seed, student=None), headers=headers)

    replaced = await api.put(V2, json=_form(seed), headers=headers)

    assert replaced.json()["student"]["student_id"] == "S-77"


async def test_a_contact_of_somebody_else_cannot_be_claimed(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    _, mine = _newcomer()
    _, theirs = _newcomer()
    await api.post(V2, json=_form(seed), headers=mine)
    stranger = (await api.post(V2, json=_form(seed), headers=theirs)).json()

    response = await api.put(
        V2,
        json=_form(
            seed,
            contacts=[
                {"id": stranger["contacts"][0]["id"], "type": "email", "value": "x@y.z"}
            ],
        ),
        headers=mine,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "CONTACT_NOT_FOUND"
    assert (await api.get(V2, headers=theirs)).json()["contacts"][0]["value"] == (
        "m@example.com"
    )


async def test_replacing_a_missing_profile_is_not_found(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)

    response = await api.put(V2, json=_form(seed), headers=principal())

    assert response.status_code == 404
    assert response.json()["detail"] == "PROFILE_NOT_FOUND"


async def test_the_form_is_validated(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)

    blank = await api.post(V2, json=_form(seed, surname="  "), headers=principal())
    unauthenticated = await api.post(V2, json=_form(seed))

    assert blank.status_code == 422
    assert unauthenticated.status_code in (401, 403)


async def test_a_token_that_disagrees_with_the_link_is_answered_and_announced_once(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    published: list[tuple[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("profile.service.account._announced", {})
    person_id = UUID(
        (
            await api.post(
                f"{V1}/persons", json={"surname": "A", "name": "B"}, headers=ADMIN
            )
        ).json()["id"]
    )
    linked = await as_person(person_id)
    link_user = UUID(
        jwt.decode(
            linked["Authorization"].split()[1], options={"verify_signature": False}
        )["sub"]
    )
    stale = principal(person_id=uuid4(), user_id=link_user)

    first = await api.get(f"{V1}/persons/my", headers=stale)
    second = await api.get(f"{V1}/persons/my", headers=stale)
    matching = await api.get(f"{V1}/persons/my", headers=linked)

    assert [first.status_code, second.status_code, matching.status_code] == [
        200,
        200,
        200,
    ]
    assert first.json()["id"] == str(person_id)
    announced = [
        payload for name, payload in published if name == "on_person_link_changed"
    ]
    assert len(announced) == 1
    assert (announced[0][0].user_id, announced[0][0].person_id) == (
        link_user,
        person_id,
    )


async def test_only_superusers_make_a_person_directly(
    api: httpx.AsyncClient,
) -> None:
    body = {"surname": "Flood", "name": "Risk"}

    ordinary = await api.post(f"{V1}/persons", json=body, headers=principal())
    admin = await api.post(f"{V1}/persons", json=body, headers=ADMIN)

    assert ordinary.status_code == 403
    assert admin.status_code == 200


async def test_each_type_of_contact_has_exactly_one_main(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    seed = await _classroom(profile_engine, api)
    _, headers = _newcomer()
    contacts = [
        {"type": "email", "value": "a@example.com"},
        {"type": "email", "value": "b@example.com", "is_main": True},
        {"type": "email", "value": "c@example.com", "is_main": True},
        {"type": "phone", "value": "+7000"},
        {"type": "phone", "value": "+7111"},
    ]

    created = await api.post(V2, json=_form(seed, contacts=contacts), headers=headers)

    assert [(c["value"], c["is_main"]) for c in created.json()["contacts"]] == [
        ("a@example.com", False),
        ("b@example.com", True),
        ("c@example.com", False),
        ("+7000", True),
        ("+7111", False),
    ]


def test_the_main_contact_of_a_type_is_the_first_one_marked_else_the_first() -> None:
    from profile.dto.my_profile import MyContactDTO
    from profile.enum.contact import ContactType
    from profile.service.my_profile import main_flags

    def contact(kind: ContactType, main: bool = False) -> MyContactDTO:
        return MyContactDTO(type=kind, value="x", is_main=main)

    assert main_flags([]) == []
    assert main_flags([contact(ContactType.vk)]) == [True]
    assert main_flags(
        [
            contact(ContactType.tg),
            contact(ContactType.vk),
            contact(ContactType.tg, True),
            contact(ContactType.vk, True),
        ]
    ) == [False, False, True, True]
