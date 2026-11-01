import time
from profile.service.organization import OrganizationService
from profile.uow.organization import OrganizationUOW
from uuid import UUID, uuid4

import httpx
import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.event import FakeEvent
from support.http import AsPerson, principal

from core.schema.message.org import OrganizationData

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)


async def _person(api: httpx.AsyncClient, surname: str = "Ivanov") -> UUID:
    response = await api.post(
        f"{V1}/persons", json={"surname": surname, "name": "Ivan"}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return UUID(response.json()["id"])


async def _profile(api: httpx.AsyncClient, person_id: UUID) -> None:
    response = await api.post(
        f"{V1}/profiles",
        json={"id": str(person_id), "birthdate": "2001-02-03"},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text


async def _student(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, person_id: UUID
) -> None:
    faculty_id = uuid4()
    async with profile_engine.begin() as conn:
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
    created = await api.post(
        f"{V1}/students",
        json={
            "id": str(person_id),
            "student_id": "S-1",
            "group_id": group.json()["id"],
        },
        headers=ADMIN,
    )
    assert created.status_code == 200, created.text


async def _unit(
    profile_engine: AsyncEngine, kind: str, head_id: UUID | None
) -> UUID:
    unit_id = uuid4()
    async with profile_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, type, principal_id) "
                "VALUES (:id, :type, :head)"
            ),
            {"id": unit_id, "type": kind, "head": head_id},
        )
    return unit_id


async def test_person_read_needs_a_signed_in_user(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)

    anonymous = await api.get(f"{V1}/persons/{person_id}")

    assert anonymous.status_code == 401


async def test_person_read_needs_a_verified_user(
    api: httpx.AsyncClient,
) -> None:
    person_id = await _person(api)

    unverified = await api.get(
        f"{V1}/persons/{person_id}",
        headers=principal(person_id=person_id, verified=False),
    )

    assert unverified.status_code == 403


async def test_a_person_reads_themselves_without_asking_event(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    person_id = await _person(api)

    response = await api.get(
        f"{V1}/persons/{person_id}", headers=await as_person(person_id)
    )

    assert response.status_code == 200, response.text
    assert response.json()["surname"] == "Ivanov"
    assert event.calls == []


async def test_a_stranger_gets_the_same_answer_as_for_a_missing_person(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    person_id = await _person(api)
    stranger = await as_person(await _person(api, "Petrov"))

    hidden = await api.get(f"{V1}/persons/{person_id}", headers=stranger)
    missing = await api.get(f"{V1}/persons/{uuid4()}", headers=stranger)

    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()


async def test_a_person_sharing_a_collective_is_visible(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    colleague_id = await _person(api)
    viewer_id = await _person(api, "Petrov")
    event.share(viewer_id, colleague_id)

    response = await api.get(
        f"{V1}/persons/{colleague_id}", headers=await as_person(viewer_id)
    )

    assert response.status_code == 200, response.text


async def test_a_superuser_reads_any_person_without_asking_event(
    api: httpx.AsyncClient, event: FakeEvent
) -> None:
    person_id = await _person(api)

    response = await api.get(f"{V1}/persons/{person_id}", headers=ADMIN)

    assert response.status_code == 200
    assert event.calls == []


async def test_the_context_audience_is_refused_while_event_is_silent(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    event: FakeEvent,
) -> None:
    colleague_id = await _person(api)
    head_id = await _person(api, "Dean")
    await _unit(profile_engine, "faculty", head_id)
    viewer_id = await _person(api, "Petrov")
    event.share(viewer_id, colleague_id)
    viewer = await as_person(viewer_id)
    event.down = True

    colleague = await api.get(f"{V1}/persons/{colleague_id}", headers=viewer)
    head = await api.get(f"{V1}/persons/{head_id}", headers=viewer)

    assert colleague.status_code == 404
    assert head.status_code == 200, head.text


async def test_person_search_lists_only_the_visible(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    viewer_id = await _person(api, "Smirnov")
    colleague_id = await _person(api, "Smirnova")
    await _person(api, "Smirnenko")
    event.share(viewer_id, colleague_id)
    viewer = await as_person(viewer_id)

    found = await api.get(f"{V1}/persons", params={"search": "Smir"}, headers=viewer)
    hidden = await api.get(
        f"{V1}/persons", params={"search": "Smirnenko"}, headers=viewer
    )
    everyone = await api.get(f"{V1}/persons", params={"search": "Smir"}, headers=ADMIN)

    assert found.status_code == 200, found.text
    assert {item["id"] for item in found.json()["items"]} == {
        str(viewer_id),
        str(colleague_id),
    }
    assert found.json()["pagination"]["total"] == 2
    assert hidden.json()["items"] == []
    assert everyone.json()["pagination"]["total"] == 3


async def test_person_search_without_a_person_finds_nobody(
    api: httpx.AsyncClient,
) -> None:
    await _person(api)

    response = await api.get(
        f"{V1}/persons", headers=principal(person_id=None, user_id=uuid4())
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_person_search_while_event_is_silent_finds_the_open_audience_only(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    event: FakeEvent,
) -> None:
    viewer_id = await _person(api, "Smirnov")
    colleague_id = await _person(api, "Smirnova")
    head_id = await _person(api, "Smirnenko")
    await _unit(profile_engine, "university", head_id)
    event.share(viewer_id, colleague_id)
    event.down = True

    response = await api.get(
        f"{V1}/persons",
        params={"search": "Smir"},
        headers=await as_person(viewer_id),
    )

    assert response.status_code == 200, response.text
    assert {item["id"] for item in response.json()["items"]} == {
        str(viewer_id),
        str(head_id),
    }


async def test_the_profile_list_is_for_superusers(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    person_id = await _person(api)
    await _profile(api, person_id)

    ordinary = await api.get(f"{V1}/profiles", headers=await as_person(person_id))
    by_birthdate = await api.get(
        f"{V1}/profiles",
        params={"birthdate__gte": "2001-02-03"},
        headers=await as_person(person_id),
    )
    admin = await api.get(f"{V1}/profiles", headers=ADMIN)

    assert ordinary.status_code == by_birthdate.status_code == 403
    assert admin.status_code == 200
    assert admin.json()["pagination"]["total"] == 1


async def test_a_profile_is_read_by_its_owner_and_superusers_only(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    person_id = await _person(api)
    await _profile(api, person_id)
    colleague_id = await _person(api, "Petrov")
    event.share(person_id, colleague_id)
    url = f"{V1}/profiles/{person_id}"

    anonymous = await api.get(url)
    unverified = await api.get(
        url, headers=principal(person_id=person_id, verified=False)
    )
    owner = await api.get(url, headers=await as_person(person_id))
    colleague = await api.get(url, headers=await as_person(colleague_id))
    missing = await api.get(
        f"{V1}/profiles/{uuid4()}", headers=await as_person(colleague_id)
    )
    admin = await api.get(url, headers=ADMIN)

    assert anonymous.status_code == 401
    assert unverified.status_code == 403
    assert owner.status_code == 200, owner.text
    assert owner.json()["birthdate"] == "2001-02-03"
    assert colleague.status_code == 404
    assert colleague.json() == missing.json()
    assert admin.status_code == 200


async def test_a_student_card_is_read_by_its_owner_and_superusers_only(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    event: FakeEvent,
) -> None:
    person_id = await _person(api)
    await _profile(api, person_id)
    await _student(api, profile_engine, person_id)
    colleague_id = await _person(api, "Petrov")
    event.share(person_id, colleague_id)
    url = f"{V1}/students/{person_id}"

    anonymous = await api.get(url)
    unverified = await api.get(
        url, headers=principal(person_id=person_id, verified=False)
    )
    owner = await api.get(url, headers=await as_person(person_id))
    colleague = await api.get(url, headers=await as_person(colleague_id))
    missing = await api.get(
        f"{V1}/students/{uuid4()}", headers=await as_person(colleague_id)
    )
    admin = await api.get(url, headers=ADMIN)

    assert anonymous.status_code == 401
    assert unverified.status_code == 403
    assert owner.status_code == 200, owner.text
    assert colleague.status_code == 404
    assert colleague.json() == missing.json()
    assert admin.status_code == 200


async def test_names_need_a_verified_user(api: httpx.AsyncClient) -> None:
    body = {"ids": [str(uuid4())]}

    anonymous = await api.post(f"{V2}/persons/names", json=body)
    unverified = await api.post(
        f"{V2}/persons/names",
        json=body,
        headers=principal(person_id=uuid4(), verified=False),
    )

    assert anonymous.status_code == 401
    assert unverified.status_code == 403


async def test_a_hidden_name_looks_like_a_missing_person(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    viewer_id = await _person(api, "Smirnov")
    colleague_id = await _person(api, "Smirnova")
    stranger_id = await _person(api, "Smirnenko")
    missing_id = uuid4()
    event.share(viewer_id, colleague_id)
    ids = [viewer_id, colleague_id, stranger_id, missing_id]

    response = await api.post(
        f"{V2}/persons/names",
        json={"ids": [str(i) for i in ids]},
        headers=await as_person(viewer_id),
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["id"] for item in items] == [str(i) for i in ids]
    named = {item["id"]: item for item in items}
    assert named[str(colleague_id)] == {
        "id": str(colleague_id),
        "surname": "Smirnova",
        "name": "Ivan",
        "patronymic": None,
    }
    assert named[str(viewer_id)]["surname"] == "Smirnov"
    nameless = {"surname": None, "name": None, "patronymic": None}
    assert {k: v for k, v in named[str(stranger_id)].items() if k != "id"} == nameless
    assert {k: v for k, v in named[str(missing_id)].items() if k != "id"} == nameless


async def test_names_of_oneself_do_not_ask_event(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    viewer_id = await _person(api)

    response = await api.post(
        f"{V2}/persons/names",
        json={"ids": [str(viewer_id)]},
        headers=await as_person(viewer_id),
    )

    assert [item["id"] for item in response.json()["items"]] == [str(viewer_id)]
    assert event.calls == []


async def test_a_superuser_gets_every_existing_name(api: httpx.AsyncClient) -> None:
    first = await _person(api)
    second = await _person(api, "Petrov")
    missing = uuid4()

    response = await api.post(
        f"{V2}/persons/names",
        json={"ids": [str(first), str(second), str(missing)]},
        headers=ADMIN,
    )

    named = {item["id"]: item["surname"] for item in response.json()["items"]}
    assert named == {str(first): "Ivanov", str(second): "Petrov", str(missing): None}


async def test_names_are_bounded_per_request(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    viewer = await as_person(await _person(api))

    response = await api.post(
        f"{V2}/persons/names",
        json={"ids": [str(uuid4()) for _ in range(201)]},
        headers=viewer,
    )

    assert response.status_code == 422


async def test_names_while_event_is_silent_hide_the_context_audience_only(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    viewer_id = await _person(api)
    colleague_id = await _person(api, "Petrov")
    event.share(viewer_id, colleague_id)
    event.down = True

    response = await api.post(
        f"{V2}/persons/names",
        json={"ids": [str(viewer_id), str(colleague_id)]},
        headers=await as_person(viewer_id),
    )

    assert response.status_code == 200, response.text
    named = {item["id"]: item["surname"] for item in response.json()["items"]}
    assert named == {str(viewer_id): "Ivanov", str(colleague_id): None}


async def _invite(api: httpx.AsyncClient, person_id: UUID) -> str:
    response = await api.post(
        f"{V2}/persons/{person_id}/invite", json={}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


async def test_an_invite_names_its_person_without_signing_in(
    api: httpx.AsyncClient,
) -> None:
    person_id = await _person(api)
    token = await _invite(api, person_id)

    response = await api.post(f"{V2}/invites/preview", json={"token": token})

    assert response.status_code == 200, response.text
    assert response.json() == {
        "surname": "Ivanov",
        "name": "Ivan",
        "patronymic": None,
    }


async def test_a_forged_invite_names_nobody(api: httpx.AsyncClient) -> None:
    person_id = await _person(api)
    forged = jwt.encode(
        {
            "person_id": str(person_id),
            "aud": ["invite"],
            "iss": "profile",
            "exp": int(time.time()) + 600,
        },
        "not-the-profile-key",
        algorithm="HS256",
    )

    garbage = await api.post(f"{V2}/invites/preview", json={"token": "garbage"})
    wrong_key = await api.post(f"{V2}/invites/preview", json={"token": forged})

    assert garbage.status_code == wrong_key.status_code == 400
    assert garbage.json()["detail"] == "INVITE_TOKEN_INVALID"
    assert wrong_key.json()["detail"] == "INVITE_TOKEN_INVALID"


async def test_an_invite_of_a_deleted_person_names_nobody(
    api: httpx.AsyncClient,
) -> None:
    person_id = await _person(api)
    token = await _invite(api, person_id)
    await api.delete(f"{V1}/persons/{person_id}", headers=ADMIN)

    response = await api.post(f"{V2}/invites/preview", json={"token": token})

    assert response.status_code == 404
    assert response.json()["detail"] == "INVITE_PERSON_NOT_FOUND"


async def test_an_invite_of_a_person_with_an_account_names_nobody(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    person_id = await _person(api)
    token = await _invite(api, person_id)
    await as_person(person_id)

    response = await api.post(f"{V2}/invites/preview", json={"token": token})

    assert response.status_code == 400
    assert response.json()["detail"] == "PERSON_ALREADY_HAS_ACCOUNT"


async def test_the_head_of_a_university_or_a_faculty_is_visible_to_everyone(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    rector_id = await _person(api, "Rector")
    dean_id = await _person(api, "Dean")
    leader_id = await _person(api, "Leader")
    stranger_id = await _person(api, "Stranger")
    stranger = await as_person(stranger_id)
    await _unit(profile_engine, "university", rector_id)
    await _unit(profile_engine, "faculty", dean_id)
    await _unit(profile_engine, "collective", leader_id)

    rector = await api.get(f"{V1}/persons/{rector_id}", headers=stranger)
    dean = await api.get(f"{V1}/persons/{dean_id}", headers=stranger)
    leader = await api.get(f"{V1}/persons/{leader_id}", headers=stranger)
    listed = await api.get(f"{V1}/persons", headers=stranger)
    profile = await api.get(f"{V1}/profiles/{rector_id}", headers=stranger)

    assert rector.status_code == dean.status_code == 200
    assert leader.status_code == 404
    assert {item["id"] for item in listed.json()["items"]} == {
        str(stranger_id),
        str(rector_id),
        str(dean_id),
    }
    assert profile.status_code == 404


async def test_an_unverified_viewer_does_not_get_the_open_audience(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    head_id = await _person(api, "Dean")
    await _unit(profile_engine, "faculty", head_id)

    response = await api.get(
        f"{V1}/persons/{head_id}", headers=principal(person_id=uuid4(), verified=False)
    )

    assert response.status_code == 403


async def test_an_organization_event_brings_the_head_to_the_projection(
    api: httpx.AsyncClient,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    as_person: AsPerson,
) -> None:
    head_id = await _person(api, "Dean")
    stranger = await as_person(await _person(api, "Stranger"))
    unit_id = uuid4()
    service = OrganizationService(OrganizationUOW(profile_sessionmaker))
    announcement = OrganizationData(id=unit_id, name="Physics", type="faculty")

    await service.update([announcement])
    before = await api.get(f"{V1}/persons/{head_id}", headers=stranger)
    await service.update([announcement.model_copy(update={"principal_id": head_id})])
    after = await api.get(f"{V1}/persons/{head_id}", headers=stranger)

    assert before.status_code == 404
    assert after.status_code == 200, after.text
