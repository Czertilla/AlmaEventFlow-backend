import shutil
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from profile.crypto import KeyRing, cipher, dek_cache, install_keyring
from profile.crypto.keygen import create
from profile.crypto.local import LocalKeyProvider
from profile.crypto.vault import AppRoleAuth, VaultTransitProvider
from profile.dto.key_maintenance import DestroyKeyDTO
from profile.enum.audience import Audience
from profile.manage.keys import parser, run
from profile.registry import Column, PersonalField, Source
from profile.registry.validate import problems
from profile.service.key_maintenance import KeyMaintenanceService
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
from support.vault import fake_vault

from core.config.settings import settings

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN = principal(superuser=True)
REASON = "Просьба человека удалить его данные"


def _passport(number: str, *, variant: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {
        "number": number,
        "expire_date": "2031-02-03",
        "issued_authority": "ОВД Тверского района",
        "is_foreign": False,
    }
    if variant:
        body["name_variant"] = {"surname": "Ivanova", "name": "Anna"}
    return body


async def _owner(
    api: httpx.AsyncClient, as_person: AsPerson, *numbers: str
) -> tuple[UUID, dict[str, str]]:
    created = await api.post(
        f"{V1}/persons", json={"surname": "Ivanov", "name": "Ivan"}, headers=ADMIN
    )
    person_id = UUID(created.json()["id"])
    await api.post(f"{V1}/profiles", json={"id": str(person_id)}, headers=ADMIN)
    headers = await as_person(person_id)
    for n, number in enumerate(numbers):
        response = await api.post(
            f"{V1}/passports/my",
            json=_passport(number, variant=n == 0),
            headers=headers,
        )
        assert response.status_code == 200, response.text
    return person_id, headers


async def _numbers(api: httpx.AsyncClient, headers: dict[str, str]) -> list[str]:
    response = await api.get(f"{V1}/passports/my", headers=headers)
    assert response.status_code == 200, response.text
    return sorted(item["number"] for item in response.json()["items"])


async def _sql(engine: AsyncEngine, sql: str, **params: Any) -> list[Any]:
    async with engine.begin() as conn:
        result = await conn.execute(text(sql), params)
        return list(result.all()) if result.returns_rows else []


async def _keys(engine: AsyncEngine, *persons: UUID) -> dict[UUID, Any]:
    rows = await _sql(
        engine,
        "SELECT person_id, key_ref, dek_version, wrapped_dek, rotated_at, "
        "destroyed_at FROM person_key WHERE person_id = ANY(:p)",
        p=list(persons),
    )
    return {row.person_id: row for row in rows}


@pytest.fixture
def kek_dir(tmp_path: Path) -> Iterator[Path]:
    """A copy of the test key file, so a new version can be added beside it."""
    assert settings.LOCAL_KEK_DIR is not None
    folder = tmp_path / "kek"
    folder.mkdir()
    shutil.copy(Path(settings.LOCAL_KEK_DIR) / "kek.v1", folder / "kek.v1")
    try:
        yield folder
    finally:
        install_keyring(None)
        dek_cache().clear()


def _service(
    maker: async_sessionmaker[AsyncSession], ring: KeyRing | None = None
) -> KeyMaintenanceService:
    return KeyMaintenanceService(PersonalDataUOW(maker), ring=ring)


async def test_rewrap_moves_every_key_to_a_new_version_of_the_local_key(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    kek_dir: Path,
) -> None:
    owners = [
        await _owner(api, as_person, f"4510 00000{n}", f"72 000000{n}")
        for n in range(3)
    ]
    persons = [person for person, _ in owners]
    before = await _keys(profile_engine, *persons)
    create(kek_dir, 2, None)
    ring = KeyRing(LocalKeyProvider(kek_dir, 2))
    seen: list[tuple[int, int]] = []

    dry = await _service(profile_sessionmaker, ring).rewrap(dry_run=True)
    unchanged = await _keys(profile_engine, *persons)
    report = await _service(profile_sessionmaker, ring).rewrap(
        batch_size=2,
        pause_ms=0,
        progress=lambda done, total: seen.append((done, total)),
    )
    again = await _service(profile_sessionmaker, ring).rewrap(pause_ms=0)
    after = await _keys(profile_engine, *persons)
    (kek_dir / "kek.v1").chmod(0o600)
    (kek_dir / "kek.v1").unlink()
    install_keyring(KeyRing(LocalKeyProvider(kek_dir, 2)))
    dek_cache().clear()

    assert (dry.found, dry.rewrapped, dry.dry_run) == (3, 0, True)
    assert unchanged == before
    assert (report.target, report.found, report.rewrapped) == ("local:kek:2", 3, 3)
    assert seen[-1] == (3, 3)
    assert (again.found, again.rewrapped) == (0, 0)
    for person in persons:
        assert before[person].key_ref == "local:kek:1"
        assert after[person].key_ref == "local:kek:2"
        assert after[person].wrapped_dek != before[person].wrapped_dek
        assert after[person].dek_version == before[person].dek_version
    for n, (_, headers) in enumerate(owners):
        assert await _numbers(api, headers) == [f"4510 00000{n}", f"72 000000{n}"]


async def test_an_interrupted_rewrap_resumes_where_it_stopped(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    kek_dir: Path,
) -> None:
    persons = [(await _owner(api, as_person, f"4510 11111{n}"))[0] for n in range(3)]
    create(kek_dir, 2, None)
    ring = KeyRing(LocalKeyProvider(kek_dir, 2))

    def stop(done: int, total: int) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        await _service(profile_sessionmaker, ring).rewrap(
            batch_size=1, pause_ms=0, progress=stop
        )
    halfway = await _keys(profile_engine, *persons)
    resumed = await _service(profile_sessionmaker, ring).rewrap(pause_ms=0)

    assert sorted(row.key_ref for row in halfway.values()) == [
        "local:kek:1",
        "local:kek:1",
        "local:kek:2",
    ]
    assert (resumed.found, resumed.rewrapped) == (2, 2)


async def test_rewrap_moves_keys_from_local_to_vault_and_follows_its_rotation(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    kek_dir: Path,
    tmp_path: Path,
) -> None:
    owners = [await _owner(api, as_person, f"4510 22222{n}") for n in range(2)]
    persons = [person for person, _ in owners]
    async with fake_vault(tmp_path) as vault:
        provider = VaultTransitProvider(
            vault.url,
            auth=AppRoleAuth("approle", vault.role_id_file, vault.secret_id_file),
        )
        local = LocalKeyProvider(kek_dir, 1)
        moved = await _service(
            profile_sessionmaker, KeyRing(provider, [local])
        ).rewrap(pause_ms=0)
        on_vault = await _keys(profile_engine, *persons)
        install_keyring(KeyRing(provider))
        dek_cache().clear()
        read_without_local = [await _numbers(api, headers) for _, headers in owners]
        vault.rotate()
        rotated = await _service(profile_sessionmaker, KeyRing(provider)).rewrap(
            pause_ms=0
        )
        on_new_version = await _keys(profile_engine, *persons)
        dek_cache().clear()
        read_after_rotation = [await _numbers(api, headers) for _, headers in owners]
        install_keyring(None)
        await provider.close()

    assert (moved.found, moved.rewrapped) == (2, 2)
    assert {row.key_ref for row in on_vault.values()} == {"vault:profile-kek:1"}
    assert read_without_local == [["4510 222220"], ["4510 222221"]]
    assert (rotated.target, rotated.rewrapped) == ("vault:profile-kek:2", 2)
    assert {row.key_ref for row in on_new_version.values()} == {"vault:profile-kek:2"}
    assert read_after_rotation == read_without_local


async def test_status_tells_whether_a_retired_key_still_wraps_anything(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    kek_dir: Path,
) -> None:
    await _owner(api, as_person, "4510 333333")
    create(kek_dir, 2, None)
    ring = KeyRing(LocalKeyProvider(kek_dir, 2))
    retired = parser().parse_args(["status", "--retired", "local:kek:1"])
    rewrap = parser().parse_args(["rewrap", "--to", "local", "--sleep-ms", "0"])

    before = await run(retired, profile_sessionmaker)
    moved = await run(rewrap, profile_sessionmaker, ring)
    after = await run(retired, profile_sessionmaker)
    status = await _service(profile_sessionmaker).status()

    assert (before, moved, after) == (1, 0, 0)
    assert "local:kek:1" not in status.by_key_ref
    assert status.by_key_ref.get("local:kek:2", 0) >= 1


async def test_rotating_a_data_key_seals_the_values_again(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    rotated, headers = await _owner(api, as_person, "4510 444444", "72 4444444")
    other, _ = await _owner(api, as_person, "4510 555555")
    blobs = await _sql(
        profile_engine,
        "SELECT id, number, expire_date FROM passport WHERE profile_id = :p",
        p=rotated,
    )
    untouched = await _keys(profile_engine, other)

    report = await _service(profile_sessionmaker).rotate([rotated], pause_ms=0)
    again = await _sql(
        profile_engine,
        "SELECT id, number, expire_date FROM passport WHERE profile_id = :p",
        p=rotated,
    )
    keys = await _keys(profile_engine, rotated, other)

    assert (report.found, report.rotated) == (1, 1)
    assert keys[rotated].dek_version == 2
    assert keys[rotated].rotated_at is not None
    assert keys[other] == untouched[other]
    old = {row.id: row for row in blobs}
    for row in again:
        assert row.number != old[row.id].number
        assert cipher.dek_version_of(row.number) == 2
        assert cipher.dek_version_of(row.expire_date) == 2
    assert await _numbers(api, headers) == ["4510 444444", "72 4444444"]


async def test_only_keys_older_than_asked_are_rotated(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    old, _ = await _owner(api, as_person, "4510 666666")
    fresh, _ = await _owner(api, as_person, "4510 777777")
    await _sql(
        profile_engine,
        "UPDATE person_key SET created_at = now() - interval '400 days' "
        "WHERE person_id = :p",
        p=old,
    )
    dry = await _service(profile_sessionmaker).rotate(
        older_than=timedelta(days=365), dry_run=True
    )
    report = await _service(profile_sessionmaker).rotate(
        older_than=timedelta(days=365), pause_ms=0
    )
    keys = await _keys(profile_engine, old, fresh)

    assert (dry.found, dry.rotated) == (1, 0)
    assert (report.found, report.rotated) == (1, 1)
    assert (keys[old].dek_version, keys[fresh].dek_version) == (2, 1)


async def test_a_superuser_destroys_a_key_and_the_data_it_encrypts(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
) -> None:
    person, headers = await _owner(api, as_person, "4510 888888", "72 8888888")
    url = f"{V2}/persons/{person}/destroy-key"
    body = {"confirm_person_id": str(person), "reason": REASON}

    response = await api.post(url, json=body, headers=ADMIN)
    numbers = await _numbers(api, headers)
    key = (await _keys(profile_engine, person))[person]
    variants = await _sql(
        profile_engine,
        "SELECT count(*) AS n FROM name_variant nv JOIN passport p ON p.id = nv.id "
        "WHERE p.profile_id = :p",
        p=person,
    )
    journal = await _sql(
        profile_engine,
        "SELECT via, fields, outcome FROM sensitive_access_log "
        "WHERE subject_person_id = :p AND action = 'key_destroyed'",
        p=person,
    )
    [(title, notice)] = await _sql(
        profile_engine,
        "SELECT title, body FROM notification_outbox WHERE person_id = :p "
        "AND data->>'kind' = 'key_destroyed'",
        p=person,
    )
    again = await api.post(url, json=body, headers=ADMIN)
    created = await api.post(
        f"{V1}/passports/my", json=_passport("4510 999999"), headers=headers
    )
    renewed = (await _keys(profile_engine, person))[person]

    assert response.status_code == 200, response.text
    assert response.json()["rows_deleted"] == 2
    assert [field["key"] for field in response.json()["fields"]] == [
        "passport.number",
        "passport.issued_authority",
        "passport.issued_date",
        "passport.expire_date",
    ]
    assert numbers == []
    assert variants[0].n == 0
    assert key.wrapped_dek is None and key.key_ref is None
    assert key.destroyed_at is not None
    assert [(row.via, row.outcome) for row in journal] == [("superuser", "ok")]
    assert "passport.number" in journal[0].fields
    assert title == "Ваши данные уничтожены"
    assert REASON in notice and "Номер паспорта" in notice and "888888" not in notice
    assert again.status_code == 409
    assert again.json()["detail"] == "PERSON_KEY_ABSENT"
    assert created.status_code == 200, created.text
    assert renewed.dek_version == 2 and renewed.wrapped_dek is not None
    assert await _numbers(api, headers) == ["4510 999999"]


@pytest.mark.parametrize(
    ("who", "body", "status", "code"),
    [
        ("owner", "ok", 403, None),
        ("admin", "other", 422, "DESTROY_NOT_CONFIRMED"),
        ("admin", "short", 422, None),
        ("unknown", "ok", 404, "PERSON_NOT_FOUND"),
    ],
)
async def test_a_key_is_not_destroyed_without_rights_or_confirmation(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    who: str,
    body: str,
    status: int,
    code: str | None,
) -> None:
    person, headers = await _owner(api, as_person, "4510 121212")
    target = uuid4() if who == "unknown" else person
    payload = {
        "confirm_person_id": str(uuid4() if body == "other" else target),
        "reason": "мало" if body == "short" else REASON,
    }

    response = await api.post(
        f"{V2}/persons/{target}/destroy-key",
        json=payload,
        headers=headers if who == "owner" else ADMIN,
    )

    assert response.status_code == status, response.text
    if code is not None:
        assert response.json()["detail"] == code
    assert (await _keys(profile_engine, person))[person].wrapped_dek is not None
    assert await _numbers(api, headers) == ["4510 121212"]


async def test_the_cli_destroys_only_with_yes(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    person, headers = await _owner(api, as_person, "4510 131313")
    command = ["destroy", "--person", str(person), "--reason", REASON]

    refused = await run(parser().parse_args(command), profile_sessionmaker)
    kept = await _numbers(api, headers)
    done = await run(parser().parse_args([*command, "--yes"]), profile_sessionmaker)
    journal = await _sql(
        profile_engine,
        "SELECT actor_user_id, via FROM sensitive_access_log "
        "WHERE subject_person_id = :p AND action = 'key_destroyed'",
        p=person,
    )

    assert (refused, done) == (1, 0)
    assert kept == ["4510 131313"]
    assert await _numbers(api, headers) == []
    assert [(row.actor_user_id, row.via) for row in journal] == [(None, "none")]


async def test_a_field_registered_in_a_fixture_is_rotated_and_destroyed(
    api: httpx.AsyncClient,
    as_person: AsPerson,
    profile_engine: AsyncEngine,
    profile_sessionmaker: async_sessionmaker[AsyncSession],
    secret_note: PersonalField,
) -> None:
    person, _ = await _owner(api, as_person)
    row_id = uuid4()
    plain = {"body": "ключ под ковриком", "due": date(2030, 5, 6), "flag": True}
    async with PersonalDataUOW(profile_sessionmaker) as uow:
        sealed = await PersonalDataService(uow)._seal(  # pyright: ignore[reportPrivateUsage]
            "secret_note", person, row_id, plain
        )
        await uow.commit()
    await _sql(
        profile_engine,
        "INSERT INTO secret_note VALUES (:id, :person, :body, :due, :flag)",
        id=row_id,
        person=person,
        body=sealed["body"],
        due=sealed["due"],
        flag=sealed["flag"],
    )

    rotated = await _service(profile_sessionmaker).rotate([person], pause_ms=0)
    [after] = await _sql(
        profile_engine,
        "SELECT body, due, flag FROM secret_note WHERE id = :id",
        id=row_id,
    )
    async with PersonalDataUOW(profile_sessionmaker) as uow:
        records = await PersonalDataService(uow)._read_fields(  # pyright: ignore[reportPrivateUsage]
            [person], [secret_note.key]
        )
    async with PersonalDataUOW(profile_sessionmaker) as uow:
        await KeyMaintenanceService(uow).destroy(
            person,
            DestroyKeyDTO(person, REASON),
            None,
        )
    [cleared] = await _sql(
        profile_engine,
        "SELECT body, due, flag FROM secret_note WHERE id = :id",
        id=row_id,
    )

    assert rotated.rotated == 1
    assert cipher.dek_version_of(after.body) == 2
    assert records[person] == [
        {secret_note.key: {"body": plain["body"], "due": plain["due"], "flag": True}}
    ]
    assert tuple(cleared) == (None, None, None)


def test_an_encrypted_value_that_is_the_person_itself_must_be_optional() -> None:
    metadata = MetaData()
    Table(
        "dossier",
        metadata,
        SAColumn("id", Uuid, primary_key=True),
        SAColumn("code", LargeBinary, nullable=False),
    )
    field = PersonalField(
        key="dossier.code",
        label="Код",
        columns=(Column("dossier", "code"),),
        audience_default=Audience.PRIVATE,
        audience_min=Audience.PRIVATE,
        audience_max=Audience.PRIVATE,
        encrypted=True,
    )

    found = problems([field], metadata, [Source("dossier", person="id")])

    assert found == ["`dossier.code`: a destroyed key would have to delete the person"]
