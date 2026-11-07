import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from profile.dependency.access_request import EXPORT_LIMIT
from profile.registry import PersonalField
from profile.service.personal_data import PersonalDataService
from profile.uow.person_key import PersonalDataUOW
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.event import FakeEvent
from support.http import AsPerson, principal

from core.config.settings import settings
from core.enum.rpc import EventRPC

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)
COMMENT = "Списки на выезд в лагерь «Солнечный»"
NUMBER = "4510 246813"
FOREIGN = "72 1234567"
PHONE = "+7 900 000-00-00"
PASSPORT_FIELDS = ["passport.number", "passport.expire_date"]
EVERYTHING = [
    "profile.birthdate",
    "profile.diet",
    "contact.phone",
    "passport.number",
    "passport.expire_date",
    "name_variant.fullname",
]


@dataclass
class World:
    collective: UUID
    leader: UUID
    alice: UUID
    bob: UUID
    carol: UUID
    leader_h: dict[str, str]
    alice_h: dict[str, str]
    bob_h: dict[str, str]


async def _person(api: httpx.AsyncClient, surname: str) -> UUID:
    created = await api.post(
        f"{V1}/persons", json={"surname": surname, "name": "Ivan"}, headers=ADMIN
    )
    person_id = UUID(created.json()["id"])
    profile = await api.post(
        f"{V1}/profiles", json={"id": str(person_id)}, headers=ADMIN
    )
    assert profile.status_code == 200, profile.text
    return person_id


async def _sql(engine: AsyncEngine, sql: str, **params: Any) -> list[Any]:
    async with engine.begin() as conn:
        result = await conn.execute(text(sql), params)
        return list(result.all()) if result.returns_rows else []


@pytest.fixture
async def world(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> World:
    leader = await _person(api, "Leader")
    alice = await _person(api, "Alice")
    bob = await _person(api, "Bob")
    carol = await _person(api, "Carol")
    collective = uuid4()
    event.collective(collective, leader, {leader, alice, bob, carol}, name="Ансамбль")
    return World(
        collective=collective,
        leader=leader,
        alice=alice,
        bob=bob,
        carol=carol,
        leader_h=await as_person(leader),
        alice_h=await as_person(alice),
        bob_h=await as_person(bob),
    )


def _in(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


async def _ask(
    api: httpx.AsyncClient,
    world: World,
    fields: list[str] | None = None,
    headers: dict[str, str] | None = None,
    **body: Any,
) -> httpx.Response:
    return await api.post(
        f"{V2}/access-requests",
        json={
            "collective_id": str(world.collective),
            "fields": fields or PASSPORT_FIELDS,
            "comment": COMMENT,
            "expires_at": _in(7),
            **body,
        },
        headers=world.leader_h if headers is None else headers,
    )


async def _asked(
    api: httpx.AsyncClient, world: World, fields: list[str] | None = None
) -> str:
    response = await _ask(api, world, fields)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _grant(
    api: httpx.AsyncClient, headers: dict[str, str], request_id: str
) -> dict[str, Any]:
    incoming = await api.get(f"{V2}/grants/incoming", headers=headers)
    assert incoming.status_code == 200, incoming.text
    [grant] = [g for g in incoming.json()["items"] if g["request_id"] == request_id]
    return grant


async def _answer(
    api: httpx.AsyncClient,
    headers: dict[str, str],
    request_id: str,
    decision: str = "approve",
) -> httpx.Response:
    grant = await _grant(api, headers, request_id)
    return await api.post(f"{V2}/grants/{grant['id']}/{decision}", headers=headers)


async def _export(
    api: httpx.AsyncClient,
    world: World,
    request_id: str,
    fields: list[str] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return await api.post(
        f"{V2}/access-requests/{request_id}/export",
        json=None if fields is None else {"fields": fields},
        headers=world.leader_h if headers is None else headers,
    )


async def _journal(engine: AsyncEngine, request_id: str) -> list[Any]:
    return await _sql(
        engine,
        "SELECT action, via, subject_person_id, grant_id, fields, outcome, "
        "notified, actor_person_id FROM sensitive_access_log "
        "WHERE request_id = :r ORDER BY created_at, action, subject_person_id",
        r=UUID(request_id),
    )


async def _notices(engine: AsyncEngine, person_id: UUID) -> list[Any]:
    return await _sql(
        engine,
        "SELECT title, body, data FROM notification_outbox "
        "WHERE person_id = :p ORDER BY created_at",
        p=person_id,
    )


async def _expire(engine: AsyncEngine, request_id: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE access_request DISABLE TRIGGER USER"))
        await conn.execute(
            text(
                "UPDATE access_request SET expires_at = now() - interval '1 minute' "
                "WHERE id = :r"
            ),
            {"r": UUID(request_id)},
        )
        await conn.execute(text("ALTER TABLE access_request ENABLE TRIGGER USER"))


async def _fill(api: httpx.AsyncClient, engine: AsyncEngine, world: World) -> None:
    for body in (
        {
            "number": NUMBER,
            "expire_date": "2031-02-03",
            "is_foreign": False,
            "name_variant": {"surname": "Ivanova", "name": "Anna"},
        },
        {"number": FOREIGN, "expire_date": "2029-01-01", "is_foreign": True},
    ):
        created = await api.post(
            f"{V1}/passports/my", json=body, headers=world.alice_h
        )
        assert created.status_code == 200, created.text
    [(diet,)] = await _sql(
        engine, "INSERT INTO diet (name) VALUES ('Вегетарианская') RETURNING id"
    )
    await _sql(
        engine,
        "UPDATE profile SET birthdate = '2003-05-06', diet_id = :d WHERE id = :p",
        d=diet,
        p=world.alice,
    )
    for kind, value in (("phone", PHONE), ("email", "alice@example.org")):
        await _sql(
            engine,
            "INSERT INTO contact (id, person_id, type, value, is_main, created_at) "
            "VALUES (:id, :p, CAST(:t AS contact_type), :v, true, now())",
            id=uuid4(),
            p=world.alice,
            t=kind,
            v=value,
        )


async def test_a_leader_asks_the_active_members_of_a_confirmed_collective(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    response = await _ask(api, world)
    body = response.json()
    journal = await _journal(profile_engine, body["id"])
    [(title, notice, data)] = await _notices(profile_engine, world.alice)

    assert response.status_code == 201, response.text
    assert body["collective_name"] == "Ансамбль"
    assert body["comment"] == COMMENT
    assert [field["key"] for field in body["fields"]] == PASSPORT_FIELDS
    assert body["is_expired"] is False
    assert {g["person_id"]: g["status"] for g in body["grants"]} == {
        str(world.alice): "pending",
        str(world.bob): "pending",
        str(world.carol): "pending",
    }
    assert {row.subject_person_id for row in journal} == {
        world.alice,
        world.bob,
        world.carol,
    }
    assert {(row.action, row.via, row.outcome) for row in journal} == {
        ("request_created", "none", "ok")
    }
    assert all(row.fields == PASSPORT_FIELDS for row in journal)
    assert all(row.actor_person_id == world.leader for row in journal)
    assert title == "Запрос доступа к вашим данным"
    assert COMMENT in notice and "Ансамбль" in notice and "Номер паспорта" in notice
    assert data["kind"] == "access_request"
    assert data["request_id"] == body["id"]
    assert await _notices(profile_engine, world.leader) == []


async def test_the_comment_is_kept_as_plain_text(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    comment = "  <b>Поездка</b> & пропуска на объект  "

    response = await _ask(api, world, comment=comment)
    [(_, notice, _)] = await _notices(profile_engine, world.alice)
    incoming = await _grant(api, world.alice_h, response.json()["id"])

    assert response.status_code == 201, response.text
    assert response.json()["comment"] == comment.strip()
    assert incoming["comment"] == comment.strip()
    assert f"«{comment.strip()}»" in notice


@pytest.mark.parametrize(
    "who", ["stranger", "member", "superuser", "unlinked", "unverified_collective"]
)
async def test_only_the_leader_of_a_confirmed_collective_asks(
    api: httpx.AsyncClient,
    world: World,
    event: FakeEvent,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    who: str,
) -> None:
    headers = world.leader_h
    expected = "NOT_COLLECTIVE_PRINCIPAL"
    if who == "stranger":
        headers = await as_person(await _person(api, "Stranger"))
    elif who == "member":
        headers = world.alice_h
    elif who == "superuser":
        headers = ADMIN
    elif who == "unlinked":
        headers = principal()
    else:
        event.unverified.add(world.collective)
        expected = "COLLECTIVE_NOT_VERIFIED"

    response = await _ask(api, world, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == expected
    assert await _notices(profile_engine, world.alice) == []


@pytest.mark.parametrize(
    ("headers", "status"),
    [({}, 401), (principal(verified=False), 403)],
)
async def test_an_anonymous_or_unverified_account_cannot_ask_or_answer(
    api: httpx.AsyncClient, world: World, headers: dict[str, str], status: int
) -> None:
    asked = await _ask(api, world, headers=headers)
    incoming = await api.get(f"{V2}/grants/incoming", headers=headers)
    approved = await api.post(f"{V2}/grants/{uuid4()}/approve", headers=headers)
    mine = await api.get(f"{V2}/access-requests", headers=headers)

    assert asked.status_code == incoming.status_code == status
    assert approved.status_code == mine.status_code == status


@pytest.mark.parametrize(
    "topic",
    [EventRPC.COLLECTIVE_PRINCIPAL_CHECK, EventRPC.COLLECTIVE_ACTIVE_MEMBERS],
)
async def test_no_request_is_made_while_event_does_not_answer(
    api: httpx.AsyncClient,
    world: World,
    event: FakeEvent,
    profile_engine: AsyncEngine,
    topic: EventRPC,
) -> None:
    event.down_topics.add(topic)

    response = await _ask(api, world)
    mine = await api.get(f"{V2}/access-requests", headers=world.leader_h)

    assert response.status_code == 503
    assert response.json()["detail"] == "EVENT_SERVICE_UNAVAILABLE"
    assert mine.json()["items"] == []
    assert await _notices(profile_engine, world.alice) == []


@pytest.mark.parametrize(
    ("comment", "status"),
    [
        ("x" * 9, 422),
        ("   " + "x" * 9 + "   ", 422),
        ("x" * 10, 201),
        ("x" * 500, 201),
        ("x" * 501, 422),
        ("", 422),
    ],
)
async def test_the_comment_is_required_within_its_bounds(
    api: httpx.AsyncClient, world: World, comment: str, status: int
) -> None:
    response = await _ask(api, world, comment=comment)

    assert response.status_code == status, response.text
    if status == 422:
        assert response.json()["detail"] == "ACCESS_COMMENT_LENGTH"


@pytest.mark.parametrize(
    "fields",
    [
        ["passport.nubmer"],
        ["profile.workplace"],
        ["passport.number", "passport.number"],
    ],
)
async def test_only_grantable_fields_are_asked_for(
    api: httpx.AsyncClient, world: World, fields: list[str]
) -> None:
    response = await _ask(api, world, fields)

    assert response.status_code == 422
    assert response.json()["detail"] == "ACCESS_FIELD_NOT_GRANTABLE"


@pytest.mark.parametrize("days", [-1, 31])
async def test_the_term_of_a_request_is_bounded(
    api: httpx.AsyncClient, world: World, days: int
) -> None:
    response = await _ask(api, world, expires_at=_in(days))
    naive = await _ask(
        api, world, expires_at=(datetime.now() + timedelta(days=1)).isoformat()
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "ACCESS_EXPIRES_OUT_OF_RANGE"
    assert naive.status_code == 422


async def test_the_grantable_fields_are_listed_from_the_registry(
    api: httpx.AsyncClient, world: World
) -> None:
    response = await api.get(f"{V2}/access-requests/fields", headers=world.leader_h)
    keys = [field["key"] for field in response.json()]

    assert response.status_code == 200
    assert "passport.number" in keys and "name_variant.fullname" in keys
    assert "profile.workplace" not in keys


async def test_a_request_never_changes(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    request_id = await _asked(api, world)

    for statement in (
        "UPDATE access_request SET comment = 'другое' WHERE id = :r",
        "DELETE FROM access_request WHERE id = :r",
        "TRUNCATE access_request CASCADE",
        "UPDATE access_request_field SET field_key = 'x' WHERE request_id = :r",
        "DELETE FROM access_request_field WHERE request_id = :r",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            await _sql(profile_engine, statement, r=UUID(request_id))

    read = await api.get(f"{V2}/access-requests/{request_id}", headers=world.leader_h)
    assert read.json()["comment"] == COMMENT


@pytest.mark.parametrize(
    ("steps", "codes", "status"),
    [
        (["approve"], [200], "active"),
        (["approve", "approve"], [200, 409], "active"),
        (["approve", "decline"], [200, 409], "active"),
        (["approve", "revoke"], [200, 200], "revoked"),
        (["approve", "revoke", "revoke"], [200, 200, 409], "revoked"),
        (["approve", "revoke", "approve"], [200, 200, 409], "revoked"),
        (["decline"], [200], "declined"),
        (["decline", "approve"], [200, 409], "declined"),
        (["decline", "revoke"], [200, 409], "declined"),
        (["revoke"], [409], "pending"),
    ],
)
async def test_a_grant_moves_only_along_its_transitions(
    api: httpx.AsyncClient,
    world: World,
    profile_engine: AsyncEngine,
    steps: list[str],
    codes: list[int],
    status: str,
) -> None:
    request_id = await _asked(api, world)

    answers = [await _answer(api, world.alice_h, request_id, step) for step in steps]
    grant = await _grant(api, world.alice_h, request_id)
    journal = await _journal(profile_engine, request_id)

    assert [answer.status_code for answer in answers] == codes
    assert all(
        answer.json()["detail"] == "GRANT_STATE_CONFLICT"
        for answer in answers
        if answer.status_code == 409
    )
    assert grant["status"] == status
    assert (grant["decided_at"] is None) == (status == "pending")
    assert (grant["revoked_at"] is not None) == (status == "revoked")
    decisions = [row for row in journal if row.action.startswith("grant_")]
    assert [row.action for row in decisions] == [
        f"grant_{step}d" if step != "approve" else "grant_approved"
        for step, code in zip(steps, codes, strict=True)
        if code == 200
    ]
    assert all(
        (row.via, row.subject_person_id, row.actor_person_id)
        == ("self", world.alice, world.alice)
        for row in decisions
    )


async def test_only_the_subject_answers_their_grant(
    api: httpx.AsyncClient, world: World
) -> None:
    request_id = await _asked(api, world)
    grant = await _grant(api, world.alice_h, request_id)

    by_others = [
        await api.post(f"{V2}/grants/{grant['id']}/approve", headers=headers)
        for headers in (world.bob_h, world.leader_h, ADMIN)
    ]
    leader_incoming = await api.get(f"{V2}/grants/incoming", headers=world.leader_h)

    assert {response.status_code for response in by_others} == {404}
    assert {response.json()["detail"] for response in by_others} == {"GRANT_NOT_FOUND"}
    assert (await _grant(api, world.alice_h, request_id))["status"] == "pending"
    assert leader_incoming.json()["items"] == []


async def test_an_expired_request_is_neither_approved_nor_exported(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    request_id = await _asked(api, world)
    await _answer(api, world.bob_h, request_id)
    await _expire(profile_engine, request_id)

    approved = await _answer(api, world.alice_h, request_id)
    declined = await _answer(api, world.alice_h, request_id, "decline")
    exported = await _export(api, world, request_id)
    read = await api.get(f"{V2}/access-requests/{request_id}", headers=world.leader_h)
    journal = await _journal(profile_engine, request_id)

    assert approved.status_code == 409
    assert approved.json()["detail"] == "ACCESS_REQUEST_EXPIRED"
    assert declined.status_code == 200
    assert exported.status_code == 409
    assert exported.json()["detail"] == "ACCESS_REQUEST_EXPIRED"
    assert read.json()["is_expired"] is True
    assert {g["person_id"]: g["status"] for g in read.json()["grants"]} == {
        str(world.alice): "declined",
        str(world.bob): "expired",
        str(world.carol): "expired",
    }
    [refused] = [row for row in journal if row.action == "denied"]
    assert (refused.subject_person_id, refused.outcome) == (None, "REQUEST_EXPIRED")
    assert not [row for row in journal if row.action == "export"]


async def test_an_approval_waits_out_the_pause_after_a_link_change(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    request_id = await _asked(api, world)
    await _sql(
        profile_engine,
        "INSERT INTO person_account_history (id, user_id, old_person_id, "
        "new_person_id, action, source, created_at) "
        "VALUES (:id, :u, NULL, :p, 'linked', 'admin', now())",
        id=uuid4(),
        u=uuid4(),
        p=world.alice,
    )

    approved = await _answer(api, world.alice_h, request_id)
    declined = await _answer(api, world.alice_h, request_id, "decline")

    assert approved.status_code == 409
    assert approved.json()["detail"] == "GRANT_COOLDOWN"
    assert declined.status_code == 200


async def test_the_export_hands_out_the_records_of_active_grants_only(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world, EVERYTHING)
    await _answer(api, world.alice_h, request_id)
    await _answer(api, world.bob_h, request_id, "decline")
    alice_grant = await _grant(api, world.alice_h, request_id)

    response = await _export(api, world, request_id)
    body = response.json()
    journal = await _journal(profile_engine, request_id)
    notices = await _notices(profile_engine, world.alice)

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert [field["key"] for field in body["fields"]] == EVERYTHING
    [subject] = body["subjects"]
    assert subject["person_id"] == str(world.alice)
    profile, contact, *passports = subject["records"]
    assert profile == {
        "profile.birthdate": "2003-05-06",
        "profile.diet": "Вегетарианская",
    }
    assert contact == {"contact.phone": PHONE}
    assert sorted(passports, key=lambda record: record["passport.number"]) == [
        {
            "passport.number": NUMBER,
            "passport.expire_date": "2031-02-03",
            "name_variant.fullname": {
                "surname": "Ivanova",
                "name": "Anna",
                "patronymic": None,
            },
        },
        {"passport.number": FOREIGN, "passport.expire_date": "2029-01-01"},
    ]
    assert body["skipped"] == sorted(
        [
            {"person_id": str(world.bob), "status": "declined"},
            {"person_id": str(world.carol), "status": "pending"},
        ],
        key=lambda item: item["person_id"],
    )
    exports = [row for row in journal if row.action == "export"]
    assert {(row.subject_person_id, row.via) for row in exports} == {
        (None, "grant"),
        (world.alice, "grant"),
    }
    [personal] = [row for row in exports if row.subject_person_id == world.alice]
    assert personal.grant_id == UUID(alice_grant["id"])
    assert personal.fields == EVERYTHING
    assert personal.notified is True
    title, notice, data = notices[-1]
    assert title == "Выгрузка ваших данных"
    assert COMMENT in notice and "Ансамбль" in notice and "Номер паспорта" in notice
    assert NUMBER not in notice and PHONE not in notice and "Ivanova" not in notice
    assert data["kind"] == "access_export"
    assert [n.title for n in await _notices(profile_engine, world.bob)] == [
        "Запрос доступа к вашим данным"
    ]


async def test_an_export_of_some_fields_returns_only_those(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world, EVERYTHING)
    await _answer(api, world.alice_h, request_id)

    response = await _export(api, world, request_id, ["contact.phone"])

    assert response.status_code == 200, response.text
    assert response.json()["subjects"][0]["records"] == [{"contact.phone": PHONE}]


@pytest.mark.parametrize(
    ("case", "status", "code", "outcome"),
    [
        ("not_grantee", 404, "ACCESS_REQUEST_NOT_FOUND", "NOT_GRANTEE"),
        ("not_principal", 403, "NOT_COLLECTIVE_PRINCIPAL", "NOT_PRINCIPAL"),
        ("not_verified", 403, "COLLECTIVE_NOT_VERIFIED", "COLLECTIVE_NOT_VERIFIED"),
        ("field", 422, "ACCESS_FIELD_NOT_REQUESTED", "FIELD_NOT_REQUESTED"),
        ("principal_down", 503, "EVENT_SERVICE_UNAVAILABLE", "EVENT_UNAVAILABLE"),
        ("members_down", 503, "EVENT_SERVICE_UNAVAILABLE", "EVENT_UNAVAILABLE"),
    ],
)
async def test_each_check_of_the_export_refuses_on_its_own(
    api: httpx.AsyncClient,
    world: World,
    event: FakeEvent,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    case: str,
    status: int,
    code: str,
    outcome: str,
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world)
    await _answer(api, world.alice_h, request_id)
    headers = world.leader_h
    fields = None
    if case == "not_grantee":
        headers = await as_person(await _person(api, "Other"))
    elif case == "not_principal":
        event.leaders[world.collective] = world.bob
    elif case == "not_verified":
        event.unverified.add(world.collective)
    elif case == "field":
        fields = ["passport.number", "profile.birthdate"]
    elif case == "principal_down":
        event.down_topics.add(EventRPC.COLLECTIVE_PRINCIPAL_CHECK)
    else:
        event.down_topics.add(EventRPC.COLLECTIVE_ACTIVE_MEMBERS)

    response = await _export(api, world, request_id, fields, headers)
    journal = await _journal(profile_engine, request_id)

    assert response.status_code == status
    assert response.json()["detail"] == code
    assert NUMBER not in response.text
    [refused] = [row for row in journal if row.action == "denied"]
    assert (refused.subject_person_id, refused.via, refused.outcome) == (
        None,
        "none",
        outcome,
    )
    assert not [row for row in journal if row.action == "export"]
    assert [n.title for n in await _notices(profile_engine, world.alice)] == [
        "Запрос доступа к вашим данным"
    ]


async def test_a_member_who_left_is_skipped_and_journaled(
    api: httpx.AsyncClient,
    world: World,
    event: FakeEvent,
    profile_engine: AsyncEngine,
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world)
    await _answer(api, world.alice_h, request_id)
    await _answer(api, world.bob_h, request_id)
    event.members[world.collective].discard(world.alice)

    response = await _export(api, world, request_id)
    journal = await _journal(profile_engine, request_id)

    assert response.status_code == 200, response.text
    assert [s["person_id"] for s in response.json()["subjects"]] == [str(world.bob)]
    assert {"person_id": str(world.alice), "status": "not_member"} in response.json()[
        "skipped"
    ]
    assert NUMBER not in response.text
    [refused] = [row for row in journal if row.action == "denied"]
    assert (refused.subject_person_id, refused.outcome) == (world.alice, "NOT_MEMBER")
    assert world.alice not in {
        row.subject_person_id for row in journal if row.action == "export"
    }
    assert [n.title for n in await _notices(profile_engine, world.alice)] == [
        "Запрос доступа к вашим данным"
    ]


async def test_a_member_who_joined_later_gets_no_grant(
    api: httpx.AsyncClient,
    world: World,
    event: FakeEvent,
    as_person: AsPerson,
) -> None:
    request_id = await _asked(api, world)
    newcomer = await _person(api, "Newcomer")
    newcomer_h = await as_person(newcomer)
    event.members[world.collective].add(newcomer)
    await _answer(api, world.alice_h, request_id)

    incoming = await api.get(f"{V2}/grants/incoming", headers=newcomer_h)
    exported = await _export(api, world, request_id)
    everyone = {
        *(s["person_id"] for s in exported.json()["subjects"]),
        *(s["person_id"] for s in exported.json()["skipped"]),
    }

    assert incoming.json()["items"] == []
    assert str(newcomer) not in everyone


async def test_the_subject_sees_the_request_and_its_comment_in_their_journal(
    api: httpx.AsyncClient, world: World, profile_engine: AsyncEngine
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world)
    await _answer(api, world.alice_h, request_id)
    await _export(api, world, request_id)

    response = await api.get(f"{V2}/access-log/my", headers=world.alice_h)
    entries = [
        entry for entry in response.json()["items"] if entry["request_id"] == request_id
    ]

    assert [entry["action"] for entry in entries] == [
        "export",
        "grant_approved",
        "request_created",
    ]
    assert {entry["comment"] for entry in entries} == {COMMENT}
    assert {entry["collective_name"] for entry in entries} == {"Ансамбль"}
    export, approved, created = entries
    assert export["actor_name"] == created["actor_name"] == "Leader Ivan"
    assert approved["by_self"] is True


async def test_the_leader_reads_only_their_own_requests(
    api: httpx.AsyncClient, world: World, as_person: AsPerson
) -> None:
    request_id = await _asked(api, world)
    other = await as_person(await _person(api, "Other"))

    mine = await api.get(
        f"{V2}/access-requests",
        params={"collective_id": str(world.collective)},
        headers=world.leader_h,
    )
    elsewhere = await api.get(
        f"{V2}/access-requests", params={"collective_id": str(uuid4())},
        headers=world.leader_h,
    )
    by_other = await api.get(f"{V2}/access-requests/{request_id}", headers=other)
    by_member = await api.get(
        f"{V2}/access-requests/{request_id}", headers=world.alice_h
    )
    others_list = await api.get(f"{V2}/access-requests", headers=other)

    assert [item["id"] for item in mine.json()["items"]] == [request_id]
    assert elsewhere.json()["items"] == []
    assert by_other.status_code == by_member.status_code == 404
    assert others_list.json()["items"] == []


async def test_exports_are_rate_limited(
    api: httpx.AsyncClient,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ACCESS_EXPORTS_PER_HOUR", 1)
    EXPORT_LIMIT.reset()
    request_id = await _asked(api, world)
    try:
        first = await _export(api, world, request_id)
        second = await _export(api, world, request_id)
    finally:
        EXPORT_LIMIT.reset()

    assert first.status_code == 200, first.text
    assert second.status_code == 429
    assert second.json()["detail"] == "TOO_MANY_REQUESTS"
    assert int(second.headers["retry-after"]) > 0


async def test_no_value_reaches_the_logs(
    api: httpx.AsyncClient,
    world: World,
    profile_engine: AsyncEngine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await _fill(api, profile_engine, world)
    request_id = await _asked(api, world, EVERYTHING)
    await _answer(api, world.alice_h, request_id)

    with caplog.at_level(logging.DEBUG):
        response = await _export(api, world, request_id)

    assert response.status_code == 200
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert NUMBER not in logged and FOREIGN not in logged and "Ivanova" not in logged


async def test_a_field_registered_in_a_fixture_goes_the_whole_way(
    api: httpx.AsyncClient,
    world: World,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    secret_note: PersonalField,
) -> None:
    row_id = uuid4()
    async with PersonalDataUOW(profile_sessionmaker) as uow:
        sealed = await PersonalDataService(uow)._seal(  # pyright: ignore[reportPrivateUsage]
            "secret_note",
            world.alice,
            row_id,
            {"body": "ключ под ковриком", "due": date(2030, 5, 6), "flag": True},
        )
        await uow.commit()
    await _sql(
        profile_engine,
        "INSERT INTO secret_note VALUES (:id, :person, :body, :due, :flag)",
        id=row_id,
        person=world.alice,
        body=sealed["body"],
        due=sealed["due"],
        flag=sealed["flag"],
    )
    fields = await api.get(f"{V2}/access-requests/fields", headers=world.leader_h)

    request_id = await _asked(api, world, [secret_note.key])
    approved = await _answer(api, world.alice_h, request_id)
    response = await _export(api, world, request_id)
    journal = await _journal(profile_engine, request_id)
    title, notice, _ = (await _notices(profile_engine, world.alice))[-1]

    assert secret_note.key in [field["key"] for field in fields.json()]
    assert approved.status_code == 200
    assert response.status_code == 200, response.text
    assert response.json()["subjects"][0]["records"] == [
        {
            secret_note.key: {
                "body": "ключ под ковриком",
                "due": "2030-05-06",
                "flag": True,
            }
        }
    ]
    assert {row.action for row in journal} == {
        "request_created",
        "grant_approved",
        "export",
    }
    assert title == "Выгрузка ваших данных"
    assert "Секретная заметка" in notice and "ключ" not in notice
