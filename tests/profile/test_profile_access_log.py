from datetime import UTC, datetime
from profile.service.account import PersonAccountService
from profile.service.outbox import NotificationOutboxService
from profile.uow.outbox import OutboxUOW
from profile.uow.person import PersonUOW
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.http import AsPerson, principal

from core.enum.profile import PersonLinkSource
from core.schema.message.notify import NotificationRequest

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN_USER = uuid4()
ADMIN = principal(superuser=True, user_id=ADMIN_USER)
NUMBER = "4510 246813"
PASSPORT = {
    "number": NUMBER,
    "expire_date": "2031-02-03",
    "is_foreign": False,
    "name_variant": {"surname": "Ivanova", "name": "Anna"},
}
PASSPORT_FIELDS = [
    "passport.number",
    "passport.issued_authority",
    "passport.issued_date",
    "passport.expire_date",
]
STUDENT_FIELDS = ["student.student_id", "student.study_terms"]


async def _person(api: httpx.AsyncClient, surname: str = "Ivanov") -> UUID:
    created = await api.post(
        f"{V1}/persons", json={"surname": surname, "name": "Ivan"}, headers=ADMIN
    )
    person_id = UUID(created.json()["id"])
    profile = await api.post(
        f"{V1}/profiles", json={"id": str(person_id)}, headers=ADMIN
    )
    assert profile.status_code == 200, profile.text
    return person_id


async def _passport(api: httpx.AsyncClient, me: dict[str, str]) -> str:
    created = await api.post(f"{V1}/passports/my", json=PASSPORT, headers=me)
    assert created.status_code == 200, created.text
    return str(created.json()["id"])


async def _sql(engine: AsyncEngine, sql: str, **params: Any) -> list[Any]:
    async with engine.begin() as conn:
        result = await conn.execute(text(sql), params)
        return list(result.all()) if result.returns_rows else []


async def _journal(engine: AsyncEngine, subject: UUID) -> list[Any]:
    return await _sql(
        engine,
        "SELECT action, via, fields, outcome, notified, actor_user_id, "
        "actor_person_id, request_id_http FROM sensitive_access_log "
        "WHERE subject_person_id = :p ORDER BY created_at, id",
        p=subject,
    )


async def _notices(engine: AsyncEngine, **where: UUID) -> list[Any]:
    column, value = next(iter(where.items()))
    return await _sql(
        engine,
        f"SELECT title, body, data, person_id, user_id FROM notification_outbox "
        f"WHERE {column} = :v ORDER BY created_at",
        v=value,
    )


async def test_the_journal_cannot_be_rewritten(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    await _passport(api, await as_person(owner))

    for statement in (
        "UPDATE sensitive_access_log SET outcome = 'x' WHERE subject_person_id = :p",
        "DELETE FROM sensitive_access_log WHERE subject_person_id = :p",
        "TRUNCATE sensitive_access_log",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            await _sql(profile_engine, statement, p=owner)

    assert len(await _journal(profile_engine, owner)) == 1


async def test_a_superuser_read_is_journaled_and_told_to_the_subject_once_an_hour(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    passport_id = await _passport(api, await as_person(owner))

    first = await api.get(
        f"{V1}/passports/{passport_id}", headers={**ADMIN, "X-Request-ID": "req-42"}
    )
    second = await api.get(f"{V1}/passports", headers=ADMIN)
    journal = await _journal(profile_engine, owner)
    notices = await _notices(profile_engine, person_id=owner)

    assert first.status_code == second.status_code == 200
    created, read, listed = journal
    assert (created.action, created.via, created.notified) == ("read", "self", False)
    assert created.fields == [*PASSPORT_FIELDS, "name_variant.fullname"]
    assert (read.action, read.via, read.outcome, read.notified) == (
        "read",
        "superuser",
        "ok",
        True,
    )
    assert (read.actor_user_id, read.request_id_http) == (ADMIN_USER, "req-42")
    assert (listed.via, listed.notified) == ("superuser", False)
    assert listed.request_id_http and listed.request_id_http != "req-42"
    [(title, body, data, person_id, user_id)] = notices
    assert (title, person_id, user_id) == ("Просмотр ваших данных", owner, None)
    assert "Номер паспорта" in body and "Вариант ФИО из паспорта" in body
    assert "администратор" in body
    assert NUMBER not in body and "Ivanova" not in body
    assert data["kind"] == "sensitive_access"
    assert data["via"] == "superuser"


async def test_the_notice_of_a_superuser_comes_again_after_an_hour(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    passport_id = await _passport(api, await as_person(owner))
    await api.get(f"{V1}/passports/{passport_id}", headers=ADMIN)
    async with profile_engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE sensitive_access_log DISABLE TRIGGER USER")
        )
        await conn.execute(
            text(
                "UPDATE sensitive_access_log SET created_at = created_at - "
                "interval '61 minutes' WHERE subject_person_id = :p"
            ),
            {"p": owner},
        )
        await conn.execute(
            text("ALTER TABLE sensitive_access_log ENABLE TRIGGER USER")
        )

    await api.get(f"{V1}/passports/{passport_id}", headers=ADMIN)

    assert len(await _notices(profile_engine, person_id=owner)) == 2


async def test_an_own_read_is_journaled_without_a_notice(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    me = await as_person(owner)
    passport_id = await _passport(api, me)

    read = await api.get(f"{V1}/passports/my/{passport_id}", headers=me)
    listed = await api.get(f"{V1}/passports/my", headers=me)

    assert read.status_code == listed.status_code == 200
    journal = await _journal(profile_engine, owner)
    assert [(row.via, row.actor_person_id) for row in journal] == [
        ("self", owner)
    ] * 3
    assert await _notices(profile_engine, person_id=owner) == []


async def test_a_refused_passport_is_journaled_as_denied(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    stranger = await _person(api, "Petrov")
    passport_id = await _passport(api, await as_person(owner))

    refused = await api.get(
        f"{V1}/passports/my/{passport_id}", headers=await as_person(stranger)
    )

    assert refused.status_code == 403
    assert NUMBER not in refused.text
    denied = (await _journal(profile_engine, owner))[-1]
    assert (denied.action, denied.via, denied.outcome) == (
        "denied",
        "none",
        "NOT_OWNER",
    )
    assert denied.actor_person_id == stranger
    assert denied.fields == [*PASSPORT_FIELDS, "name_variant.fullname"]


async def test_a_refused_student_card_is_journaled_as_denied(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    stranger = await _person(api, "Petrov")

    refused = await api.get(
        f"{V1}/students/{owner}", headers=await as_person(stranger)
    )

    assert refused.status_code == 404
    [denied] = await _journal(profile_engine, owner)
    assert (denied.action, denied.outcome, denied.fields) == (
        "denied",
        "NOT_OWNER",
        STUDENT_FIELDS,
    )


async def test_a_student_card_read_by_a_superuser_is_journaled(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    faculty_id = uuid4()
    await _sql(
        profile_engine,
        "INSERT INTO organization (id, type) VALUES (:id, 'faculty')",
        id=faculty_id,
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
        json={"id": str(owner), "student_id": "S-7", "group_id": group.json()["id"]},
        headers=ADMIN,
    )
    own = await api.get(f"{V1}/students/{owner}", headers=await as_person(owner))

    assert created.status_code == own.status_code == 200
    journal = await _journal(profile_engine, owner)
    assert [(row.via, row.fields) for row in journal] == [
        ("superuser", STUDENT_FIELDS),
        ("self", STUDENT_FIELDS),
    ]


async def test_no_data_goes_out_when_the_journal_cannot_be_written(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = await _person(api)
    passport_id = await _passport(api, await as_person(owner))

    async def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("journal is down")

    monkeypatch.setattr(
        "profile.repository.access_log.AccessLogRepo.record_many", broken
    )

    with pytest.raises(RuntimeError, match="journal is down"):
        await api.get(f"{V1}/passports/{passport_id}", headers=ADMIN)
    assert await _notices(profile_engine, person_id=owner) == []


async def test_the_subject_reads_who_opened_their_data(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _person(api)
    stranger = await _person(api, "Petrov")
    other = await _person(api, "Sidorov")
    me = await as_person(owner)
    passport_id = await _passport(api, me)
    await _passport(api, await as_person(other))
    await api.get(f"{V1}/passports/{passport_id}", headers=ADMIN)
    await api.get(
        f"{V1}/passports/my/{passport_id}", headers=await as_person(stranger)
    )

    page = await api.get(f"{V2}/access-log/my", headers=me)
    first = await api.get(f"{V2}/access-log/my", params={"limit": 1}, headers=me)
    nobody = await api.get(
        f"{V2}/access-log/my", headers=principal(user_id=uuid4())
    )

    assert page.status_code == 200, page.text
    denied, by_admin, own = page.json()["items"]
    assert (denied["action"], denied["outcome"], denied["actor_name"]) == (
        "denied",
        "NOT_OWNER",
        "Petrov Ivan",
    )
    assert (by_admin["by_administrator"], by_admin["by_self"]) == (True, False)
    assert {f["label"] for f in by_admin["fields"]} >= {"Номер паспорта"}
    assert (own["by_self"], own["actor_name"], own["comment"]) == (True, None, None)
    assert page.json()["pagination"]["total"] == 3
    assert [item["id"] for item in first.json()["items"]] == [denied["id"]]
    assert nobody.json()["items"] == []


async def test_a_relink_tells_the_account_and_a_bootstrap_does_not(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    first = await _person(api)
    second = await _person(api, "Petrov")
    quiet = await _person(api, "Sidorov")
    user_id, quiet_user = uuid4(), uuid4()
    accounts = PersonAccountService(PersonUOW(profile_sessionmaker))

    await accounts.link(user_id, first, source=PersonLinkSource.INVITE)
    await accounts.link(
        user_id,
        second,
        source=PersonLinkSource.ADMIN,
        replace=True,
        actor_id=ADMIN_USER,
    )
    await accounts.link(quiet_user, quiet, source=PersonLinkSource.BOOTSTRAP)

    linked, moved = await _notices(profile_engine, user_id=user_id)
    assert (linked.title, linked.person_id) == ("Привязка аккаунта изменена", None)
    assert "связан с подробной информацией: Ivanov Ivan" in linked.body
    assert "перенесён на другую подробную информацию: Petrov Ivan" in moved.body
    assert "48 ч" in moved.body
    assert moved.data == {"kind": "account_link_changed", "person_id": str(second)}
    assert await _notices(profile_engine, user_id=quiet_user) == []


async def test_a_notice_for_an_account_reaches_notify_by_the_user(
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    user_id = uuid5(NAMESPACE_URL, "notice-account")
    await _sql(
        profile_engine,
        "INSERT INTO notification_outbox (id, user_id, category, title, body, data, "
        "status, attempts, next_attempt_at, created_at) VALUES (:id, :u, 'system', "
        "'t', 'b', '{}', 'pending', 0, :now, :now)",
        id=uuid4(),
        u=user_id,
        now=datetime.now(UTC),
    )
    sent: list[NotificationRequest] = []

    async def send(request: NotificationRequest) -> None:
        sent.append(request)

    publisher = NotificationOutboxService(OutboxUOW(profile_sessionmaker), send)
    await publisher.publish_batch()

    mine = [request for request in sent if request.user_ids == [user_id]]
    assert [request.person_ids for request in mine] == [[]]
