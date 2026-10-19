from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

from core.broker.rpc import RpcError
from core.schema.message.core import MQError

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)
PERSON = {"surname": "Ivanov", "name": "Ivan", "patronymic": "Ivanovich"}


@pytest.fixture
def linked(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    calls: list[Any] = []

    async def link(topic: str, request: Any, response_model: Any, **_: Any) -> None:
        calls.append((topic, request))

    monkeypatch.setattr("profile.service.person.rpc_call", link)
    return calls


async def _count(engine: AsyncEngine, table: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()


async def test_a_user_creates_their_own_person_and_it_is_linked(
    api: httpx.AsyncClient, linked: list[Any], published: list[tuple[str, Any]]
) -> None:
    response = await api.post(f"{V2}/persons/my", json=PERSON, headers=principal())

    assert response.status_code == 200, response.text
    created = response.json()
    assert (created["surname"], created["name"]) == ("Ivanov", "Ivan")
    assert created["created_at"]
    assert [(topic, str(request.person_id)) for topic, request in linked] == [
        ("rpc.user.link-person", created["id"])
    ]
    assert [name for name, _ in published] == ["on_person_created"]


async def test_the_person_is_linked_to_the_account_of_the_caller(
    api: httpx.AsyncClient, linked: list[Any]
) -> None:
    from core.utils.jwt import create_jwt_auth

    headers = principal()
    token = headers["Authorization"].split()[1]
    caller = create_jwt_auth().extract_user_snapshot(token)

    await api.post(f"{V2}/persons/my", json=PERSON, headers=headers)

    assert linked[0][1].user_id == caller.id


async def test_a_user_with_a_person_cannot_create_another(
    api: httpx.AsyncClient,
    linked: list[Any],
    published: list[tuple[str, Any]],
    profile_engine: AsyncEngine,
) -> None:
    response = await api.post(
        f"{V2}/persons/my", json=PERSON, headers=principal(person_id=uuid4())
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "ACCOUNT_ALREADY_LINKED"
    assert linked == []
    assert published == []
    assert await _count(profile_engine, "person") == 0


async def test_a_refused_link_leaves_no_person_behind(
    api: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    published: list[tuple[str, Any]],
    profile_engine: AsyncEngine,
) -> None:
    async def refuse(*_: Any, **__: Any) -> None:
        raise RpcError(MQError(code=400, detail="ACCOUNT_ALREADY_LINKED", extra={}))

    monkeypatch.setattr("profile.service.person.rpc_call", refuse)

    response = await api.post(f"{V2}/persons/my", json=PERSON, headers=principal())

    assert response.status_code == 400
    assert response.json()["detail"] == "ACCOUNT_ALREADY_LINKED"
    assert published == []
    assert await _count(profile_engine, "person") == 0


async def test_an_unanswered_link_keeps_the_person_and_announces_it(
    api: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    published: list[tuple[str, Any]],
    profile_engine: AsyncEngine,
) -> None:
    async def silent(*_: Any, **__: Any) -> None:
        raise TimeoutError

    monkeypatch.setattr("profile.service.person.rpc_call", silent)

    with pytest.raises(TimeoutError):
        await api.post(f"{V2}/persons/my", json=PERSON, headers=principal())

    assert [name for name, _ in published] == ["on_person_created"]
    assert await _count(profile_engine, "person") == 1


async def test_creating_a_person_needs_a_sign_in(api: httpx.AsyncClient) -> None:
    response = await api.post(f"{V2}/persons/my", json=PERSON)

    assert response.status_code in (401, 403)


async def _classroom(profile_engine: AsyncEngine, api: httpx.AsyncClient) -> int:
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
    assert group.status_code == 200, group.text
    return group.json()["id"]


async def test_my_student_card_lifecycle(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    group_id = await _classroom(profile_engine, api)
    person = await api.post(f"{V1}/persons", json=PERSON, headers=ADMIN)
    person_id = person.json()["id"]
    me = principal(person_id=UUID(person_id))
    body = {"student_id": "S-1", "group_id": group_id, "is_budget": True}

    no_profile = await api.put(f"{V2}/students/my", json=body, headers=me)
    await api.put(f"{V1}/profiles/my", json={}, headers=me)
    missing = await api.get(f"{V2}/students/my", headers=me)
    put = await api.put(f"{V2}/students/my", json=body, headers=me)
    patched = await api.patch(
        f"{V2}/students/my", json={"is_full": True, "student_id": "S-2"}, headers=me
    )
    read = await api.get(f"{V2}/students/my", headers=me)
    deleted = await api.delete(f"{V2}/students/my", headers=me)
    gone = await api.get(f"{V2}/students/my", headers=me)

    assert no_profile.status_code == 404
    assert no_profile.json()["detail"] == "PROFILE_NOT_FOUND"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "STUDENT_NOT_FOUND"
    assert put.status_code == 200, put.text
    assert put.json()["id"] == person_id
    assert put.json()["group"]["name"] == "G-1"
    assert patched.status_code == 200, patched.text
    assert (patched.json()["student_id"], patched.json()["is_full"]) == ("S-2", True)
    assert patched.json()["is_budget"] is True
    assert read.json()["student_id"] == "S-2"
    assert deleted.status_code == 200
    assert gone.status_code == 404


async def test_my_student_card_needs_an_attached_person(
    api: httpx.AsyncClient,
) -> None:
    me = principal()

    responses = [
        await api.get(f"{V2}/students/my", headers=me),
        await api.put(
            f"{V2}/students/my", json={"student_id": "S", "group_id": 1}, headers=me
        ),
        await api.patch(f"{V2}/students/my", json={"is_full": True}, headers=me),
        await api.delete(f"{V2}/students/my", headers=me),
    ]

    assert [r.status_code for r in responses] == [400, 400, 400, 400]
    assert {r.json()["detail"] for r in responses} == {"ATTACHED_PERSON_REQUIRED"}


async def test_a_student_card_is_only_the_callers_own(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    group_id = await _classroom(profile_engine, api)
    owner = (await api.post(f"{V1}/persons", json=PERSON, headers=ADMIN)).json()["id"]
    other = (
        await api.post(
            f"{V1}/persons", json={"surname": "Petrov", "name": "Petr"}, headers=ADMIN
        )
    ).json()["id"]
    await api.put(
        f"{V1}/profiles/my", json={}, headers=principal(person_id=UUID(owner))
    )
    await api.put(
        f"{V2}/students/my",
        json={"student_id": "S-1", "group_id": group_id},
        headers=principal(person_id=UUID(owner)),
    )

    strangers_view = await api.get(
        f"{V2}/students/my", headers=principal(person_id=UUID(other))
    )

    assert strangers_view.status_code == 404
