import logging
from collections.abc import Iterator
from datetime import date
from profile.crypto import (
    DekCache,
    Health,
    KeyProviderUnavailableError,
    KeyRef,
    KeyRing,
    WrappedKey,
    install_dek_cache,
    install_keyring,
)
from profile.dto.access import ViewerDTO
from profile.models import PersonORM
from profile.registry import PersonalField
from profile.registry.validate import problems
from profile.service.personal_data import PersonalDataService
from profile.uow.person_key import PersonalDataUOW
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import Column as SAColumn
from sqlalchemy import LargeBinary, MetaData, Table, Uuid, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.http import AsPerson, principal

BASE = "/profile/v1"
ADMIN = principal(superuser=True)
NUMBER = "4510 987654"
AUTHORITY = "ОВД Тверского района"
BODY = {
    "number": NUMBER,
    "expire_date": "2031-02-03",
    "issued_date": "2021-02-03",
    "issued_authority": AUTHORITY,
    "is_foreign": False,
}


class SilentProvider:
    provider_id = "local"

    async def wrap(self, plaintext_key: bytes, context: bytes) -> WrappedKey:
        raise KeyProviderUnavailableError("down")

    async def unwrap(self, wrapped: WrappedKey, context: bytes) -> bytes:
        raise KeyProviderUnavailableError("down")

    async def current_key_ref(self) -> KeyRef:
        raise KeyProviderUnavailableError("down")

    async def health(self) -> Health:
        return Health.UNAVAILABLE

    async def close(self) -> None:
        return None


@pytest.fixture
def silent_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    install_keyring(KeyRing(SilentProvider()))
    install_dek_cache(DekCache(0, 0))
    monkeypatch.setattr("profile.service.key_health._last", None)
    try:
        yield
    finally:
        install_keyring(None)
        install_dek_cache(None)


async def _owner(api: httpx.AsyncClient) -> UUID:
    created = await api.post(
        f"{BASE}/persons", json={"surname": "Ivanov", "name": "Ivan"}, headers=ADMIN
    )
    person_id = UUID(created.json()["id"])
    profile = await api.post(
        f"{BASE}/profiles", json={"id": str(person_id)}, headers=ADMIN
    )
    assert profile.status_code == 200, profile.text
    return person_id


async def _passport(api: httpx.AsyncClient, me: dict[str, str], **body: Any) -> str:
    created = await api.post(f"{BASE}/passports/my", json={**BODY, **body}, headers=me)
    assert created.status_code == 200, created.text
    return str(created.json()["id"])


async def _rows(engine: AsyncEngine, sql: str, **params: Any) -> list[Any]:
    async with engine.connect() as conn:
        return list((await conn.execute(text(sql), params)).all())


async def test_a_passport_is_stored_as_ciphertext_and_read_back(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _owner(api)
    me = await as_person(owner)
    passport_id = await _passport(api, me)
    bare = await _passport(api, me, issued_date=None, issued_authority=None)

    [stored] = await _rows(
        profile_engine,
        "SELECT number, expire_date, issued_date, issued_authority FROM passport "
        "WHERE id = :id",
        id=passport_id,
    )
    [empty] = await _rows(
        profile_engine,
        "SELECT issued_date, issued_authority FROM passport WHERE id = :id",
        id=bare,
    )
    [key] = await _rows(
        profile_engine,
        "SELECT key_ref, dek_version, wrapped_dek FROM person_key "
        "WHERE person_id = :p",
        p=owner,
    )
    read = await api.get(f"{BASE}/passports/my/{passport_id}", headers=me)
    listed = await api.get(f"{BASE}/passports", headers=ADMIN)

    assert all(isinstance(value, bytes) for value in stored)
    joined = b"".join(stored)
    for plain in (NUMBER, AUTHORITY, "2031-02-03", "2021-02-03"):
        assert plain.encode() not in joined
    assert tuple(empty) == (None, None)
    assert (key.key_ref, key.dek_version) == ("local:kek:1", 1)
    assert read.status_code == 200, read.text
    assert {k: read.json()[k] for k in BODY} == BODY
    assert sorted(item["number"] for item in listed.json()["items"]) == [NUMBER] * 2


async def test_a_change_is_encrypted_again_with_the_same_person_key(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _owner(api)
    me = await as_person(owner)
    passport_id = await _passport(api, me)
    before = await _rows(
        profile_engine, "SELECT number FROM passport WHERE id = :id", id=passport_id
    )

    patched = await api.patch(
        f"{BASE}/passports/{passport_id}", json={"number": "1111 222222"}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/passports/my/{passport_id}",
        json={**BODY, "issued_authority": "МВД"},
        headers=me,
    )
    after = await _rows(
        profile_engine, "SELECT number FROM passport WHERE id = :id", id=passport_id
    )
    keys = await _rows(
        profile_engine, "SELECT 1 FROM person_key WHERE person_id = :p", p=owner
    )

    assert patched.json()["number"] == "1111 222222"
    assert (replaced.json()["number"], replaced.json()["issued_authority"]) == (
        NUMBER,
        "МВД",
    )
    assert before != after
    assert len(keys) == 1


async def test_a_value_moved_to_another_row_cannot_be_read(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _owner(api)
    me = await as_person(owner)
    first = await _passport(api, me)
    second = await _passport(api, me, number="0000 111111")
    async with profile_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE passport SET number = (SELECT number FROM passport "
                "WHERE id = :from_) WHERE id = :to"
            ),
            {"from_": second, "to": first},
        )

    moved = await api.get(f"{BASE}/passports/{first}", headers=ADMIN)
    untouched = await api.get(f"{BASE}/passports/{second}", headers=ADMIN)

    assert moved.status_code == 503
    assert moved.json()["detail"] == "PERSONAL_DATA_UNAVAILABLE"
    assert "0000" not in moved.text
    assert untouched.json()["number"] == "0000 111111"


async def test_a_silent_key_provider_refuses_reads_and_writes(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    silent_keys: None,
) -> None:
    install_keyring(None)
    owner = await _owner(api)
    newcomer = await _owner(api)
    passport_id = await _passport(api, await as_person(owner))
    install_keyring(KeyRing(SilentProvider()))

    read = await api.get(f"{BASE}/passports/{passport_id}", headers=ADMIN)
    written = await api.post(
        f"{BASE}/passports/my", json=BODY, headers=await as_person(newcomer)
    )
    health = await api.get("/profile/v2/health/keys")
    stored = await _rows(
        profile_engine, "SELECT 1 FROM passport WHERE profile_id = :p", p=newcomer
    )

    assert (read.status_code, read.json()["detail"]) == (
        503,
        "PERSONAL_DATA_UNAVAILABLE",
    )
    assert written.status_code == 503
    assert stored == []
    assert (health.status_code, health.json()) == (503, {"status": "unavailable"})


async def test_the_key_health_is_ok_while_the_provider_answers(
    api: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("profile.service.key_health._last", None)

    health = await api.get("/profile/v2/health/keys")

    assert (health.status_code, health.json()) == (200, {"status": "ok"})


async def test_a_deleted_person_takes_its_data_key_along(
    api: httpx.AsyncClient, as_person: AsPerson, profile_engine: AsyncEngine
) -> None:
    owner = await _owner(api)
    await _passport(api, await as_person(owner))

    deleted = await api.delete(f"{BASE}/persons/{owner}", headers=ADMIN)
    keys = await _rows(
        profile_engine, "SELECT 1 FROM person_key WHERE person_id = :p", p=owner
    )

    assert deleted.status_code == 200, deleted.text
    assert keys == []


async def test_passport_values_never_reach_the_logs(
    api: httpx.AsyncClient, as_person: AsPerson, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    owner = await _owner(api)
    me = await as_person(owner)
    passport_id = await _passport(api, me)
    await api.get(f"{BASE}/passports/my/{passport_id}", headers=me)
    await api.patch(
        f"{BASE}/passports/{passport_id}", json={"number": "7777 333333"}, headers=ADMIN
    )
    await api.get(f"{BASE}/passports", headers=ADMIN)

    logged = caplog.text + "".join(str(r.args) for r in caplog.records)
    for plain in (NUMBER, "7777 333333", AUTHORITY):
        assert plain not in logged


async def test_passports_are_not_searched_or_sorted_by_their_values(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    owner = await _owner(api)
    passport_id = await _passport(api, await as_person(owner))

    by_value = await api.get(
        f"{BASE}/passports", params={"search": "987654"}, headers=ADMIN
    )
    by_id = await api.get(
        f"{BASE}/passports", params={"search": passport_id[:8]}, headers=ADMIN
    )
    sorted_by_number = await api.get(
        f"{BASE}/passports", params={"order_by": "number"}, headers=ADMIN
    )

    assert by_value.json()["items"] == []
    assert [item["id"] for item in by_id.json()["items"]] == [passport_id]
    assert sorted_by_number.status_code == 422


async def test_a_new_registered_field_is_encrypted_without_new_code(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    secret_note: PersonalField,
) -> None:
    person_id = await _owner(api)
    row_id = uuid4()
    plain = {
        "id": row_id,
        "body": "ключ под ковриком",
        "due": date(2030, 5, 6),
        "flag": True,
    }
    metadata = MetaData()
    for table in PersonORM.metadata.tables.values():
        table.to_metadata(metadata)
    Table(
        "secret_note",
        metadata,
        SAColumn("id", Uuid, primary_key=True),
        SAColumn("person_id", Uuid),
        *(SAColumn(name, LargeBinary) for name in ("body", "due", "flag")),
    )
    try:
        async with PersonalDataUOW(profile_sessionmaker) as uow:
            sealed = await PersonalDataService(uow)._seal(
                "secret_note", person_id, row_id, plain
            )
            await uow.commit()
        async with profile_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO secret_note VALUES (:id, :person, :body, :due, :flag)"
                ),
                {**sealed, "person": person_id},
            )
        [stored] = await _rows(
            profile_engine,
            "SELECT body, due, flag FROM secret_note WHERE id = :id",
            id=row_id,
        )
        async with PersonalDataUOW(profile_sessionmaker) as uow:
            [opened] = await PersonalDataService(uow)._open(
                "secret_note",
                [(person_id, row_id, dict(stored._mapping))],
                ViewerDTO(user_id=uuid4(), person_id=None, is_superuser=True),
            )
            await uow.commit()
        journal = await _rows(
            profile_engine,
            "SELECT action, via, fields FROM sensitive_access_log "
            "WHERE subject_person_id = :p",
            p=person_id,
        )
    finally:
        async with profile_engine.begin() as conn:
            await conn.execute(text("DROP TABLE secret_note"))

    assert problems([secret_note], metadata) == []
    assert all(isinstance(value, bytes) for value in stored)
    assert "ключ".encode() not in b"".join(stored)
    assert opened == {"body": plain["body"], "due": plain["due"], "flag": True}
    assert [tuple(row) for row in journal] == [
        ("read", "superuser", ["secret_note.content"])
    ]
