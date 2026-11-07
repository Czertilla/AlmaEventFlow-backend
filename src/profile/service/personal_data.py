import asyncio
import os
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from logging import getLogger
from profile.access.decision import Via
from profile.crypto import (
    DecryptionError,
    DekCache,
    KeyProviderError,
    KeyRing,
    WrappedKey,
    cipher,
    dek_cache,
    keyring,
)
from profile.crypto.cache import wipe
from profile.dto.access import ViewerDTO
from profile.enum.access import OUTCOME_OK, AccessAction
from profile.exc.personal_data import PersonalDataUnavailable
from profile.models.person_key import PersonKeyORM
from profile.registry import (
    Column,
    PersonalField,
    all_fields,
    encrypted_columns,
    get_field,
    sensitive_fields_of,
    source_of,
)
from profile.repository.registry_rows import StoredRow
from profile.uow.person_key import PersonalDataUOW
from typing import Any
from uuid import UUID

from core.config.settings import settings
from core.enum.notify import NotificationCategory
from core.service.base import BaseService, required_transaction
from core.utils.tz import localize

logger = getLogger(__name__)

FIRST_DEK_VERSION = 1
SUPERUSER_NOTICE_EVERY = timedelta(hours=1)

SealedRow = tuple[UUID, UUID, Mapping[str, Any]]


def dek_context(person_id: UUID, dek_version: int) -> bytes:
    return f"person_key|{person_id}|{dek_version}".encode()


def _ordered(keys: Collection[str]) -> list[str]:
    return [field.key for field in all_fields() if field.key in keys]


def _via(viewer: ViewerDTO, subject: UUID) -> str:
    if viewer.is_subject(subject):
        return Via.SELF.value
    if viewer.is_superuser:
        return Via.SUPERUSER.value
    return Via.NONE.value


def labels_of(keys: Collection[str]) -> str:
    return ", ".join(get_field(key).label for key in _ordered(keys))


def access_entry(
    viewer: ViewerDTO | None,
    subject: UUID | None,
    action: AccessAction,
    keys: Collection[str],
    outcome: str = OUTCOME_OK,
    *,
    via: Via | None = None,
    request_id: UUID | None = None,
    grant_id: UUID | None = None,
    notified: bool = False,
) -> dict[str, Any]:
    """One row of the journal; `subject` is none only for an operation over a
    whole access request, `viewer` only for an operator's job."""
    if via is None:
        via = (
            Via.NONE
            if action == AccessAction.DENIED or subject is None or viewer is None
            else Via(_via(viewer, subject))
        )
    return {
        "actor_user_id": viewer.user_id if viewer else None,
        "actor_person_id": viewer.person_id if viewer else None,
        "subject_person_id": subject,
        "request_id": request_id,
        "grant_id": grant_id,
        "action": action.value,
        "via": via.value,
        "fields": _ordered(keys),
        "outcome": outcome,
        "notified": notified,
        "request_id_http": viewer.http_request_id if viewer else None,
    }


def _shown(
    column: Column, value: Any, labels: Mapping[tuple[str, Any], Any]
) -> Any:
    if column.ref is None or value is None:
        return value
    return labels.get((column.ref.table, value))


def _matches(field: PersonalField, values: Mapping[str, Any]) -> bool:
    return all(
        str(values.get(column.where[0])) == column.where[1]
        for column in field.columns
        if column.where is not None
    )


def _disclosed(
    table: str,
    rows: Sequence[SealedRow],
    joined: Mapping[UUID, Collection[str]] | None,
) -> dict[UUID, set[str]]:
    own = {field.key for field in sensitive_fields_of(table)}
    disclosed: dict[UUID, set[str]] = {}
    for person_id, _, _ in rows:
        disclosed.setdefault(person_id, set()).update(own)
    for person_id, tables in (joined or {}).items():
        for other in tables:
            disclosed.setdefault(person_id, set()).update(
                field.key for field in sensitive_fields_of(other)
            )
    return {person_id: keys for person_id, keys in disclosed.items() if keys}


class PersonalDataService(BaseService[PersonalDataUOW]):
    """Every read and write of a registered personal field goes through here. The
    registry says which columns of a table are encrypted; each person has one data
    key (`person_key`), wrapped by the key ring. Callers pass rows as plain dicts
    and never see a key or a ciphertext."""

    def __init__(
        self,
        uow: PersonalDataUOW,
        ring: KeyRing | None = None,
        cache: DekCache | None = None,
    ) -> None:
        super().__init__(uow)
        self._ring = ring
        self._cache = cache

    @property
    def ring(self) -> KeyRing:
        return self._ring or keyring()

    @property
    def cache(self) -> DekCache:
        return self._cache or dek_cache()

    @required_transaction
    async def _seal(
        self, table: str, person_id: UUID, row_id: UUID, values: Mapping[str, Any]
    ) -> dict[str, Any]:
        columns = encrypted_columns(table)
        targets = [name for name in columns if values.get(name) is not None]
        sealed = dict(values)
        if not targets:
            return sealed
        dek, version = await self._write_key(person_id)
        try:
            for name in targets:
                sealed[name] = cipher.seal(
                    dek,
                    version,
                    cipher.encode(values[name], columns[name].kind),
                    table,
                    name,
                    person_id,
                    row_id,
                )
        finally:
            wipe(dek)
        return sealed

    @required_transaction
    async def _open(
        self,
        table: str,
        rows: Sequence[SealedRow],
        viewer: ViewerDTO,
        *,
        joined: Mapping[UUID, Collection[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """Decrypts the rows for `viewer` and journals, in this transaction, the
        sensitive fields they disclose: those of `table` and of the tables
        `joined` names per person. The caller commits before it answers."""
        columns = encrypted_columns(table)
        needed = {
            person_id
            for person_id, _, values in rows
            if any(values.get(name) is not None for name in columns)
        }
        keys = await self._read_keys(needed)
        try:
            opened = [
                self._open_row(table, columns, keys, person_id, row_id, values)
                for person_id, row_id, values in rows
            ]
        except DecryptionError as exc:
            logger.error("Personal data in %s cannot be decrypted: %s", table, exc.code)
            raise PersonalDataUnavailable() from None
        finally:
            for dek, _ in keys.values():
                wipe(dek)
        await self._record_reads(viewer, _disclosed(table, rows, joined))
        return opened

    @required_transaction
    async def _record_reads(
        self, viewer: ViewerDTO, disclosed: Mapping[UUID, set[str]]
    ) -> None:
        if not disclosed:
            return
        now = datetime.now(UTC)
        others = {subject for subject in disclosed if not viewer.is_subject(subject)}
        told: set[UUID] = set()
        if viewer.is_superuser:
            told = await self.uow.access_log.notified_since(
                viewer.user_id, others, now - SUPERUSER_NOTICE_EVERY
            )
        notify = others - told
        await self.uow.access_log.record_many(
            [
                access_entry(
                    viewer,
                    subject,
                    AccessAction.READ,
                    keys,
                    notified=subject in notify,
                )
                for subject, keys in disclosed.items()
            ]
        )
        if notify:
            who = await self._actor_name(viewer)
            for subject in notify:
                await self._tell_subject(viewer, who, subject, disclosed[subject], now)

    @required_transaction
    async def _actor_name(self, viewer: ViewerDTO) -> str:
        person = (
            await self.uow.persons.get_by_id(viewer.person_id)
            if viewer.person_id is not None
            else None
        )
        name = (
            " ".join(
                part
                for part in (person.surname, person.name, person.patronymic)
                if part
            )
            if person is not None
            else None
        )
        if viewer.is_superuser:
            return f"{name} (администратор)" if name else "администратор"
        return name or "пользователь без подробной информации"

    @required_transaction
    async def _tell_subject(
        self,
        viewer: ViewerDTO,
        who: str,
        subject: UUID,
        keys: Collection[str],
        now: datetime,
    ) -> None:
        local = localize(now)
        await self._tell(
            subject,
            "Просмотр ваших данных",
            f"Открыты ваши данные: {labels_of(keys)}. "
            f"Кто: {who}. Когда: {local:%d.%m.%Y %H:%M} {local.tzname()}.",
            {
                "kind": "sensitive_access",
                "fields": ",".join(_ordered(keys)),
                "via": _via(viewer, subject),
                "actor_person_id": str(viewer.person_id or ""),
            },
            now,
        )

    @required_transaction
    async def _tell(
        self, subject: UUID, title: str, body: str, data: dict[str, str], now: datetime
    ) -> None:
        await self._tell_many([(subject, title, body, data)], now)

    @required_transaction
    async def _tell_many(
        self, notices: Sequence[tuple[UUID, str, str, dict[str, str]]], now: datetime
    ) -> None:
        """Notices `(subject, title, body, data)` written in this transaction."""
        await self.uow.notification_outbox.enqueue_to_persons(
            notices, NotificationCategory.system.value, now
        )

    @required_transaction
    async def _record(self, entries: Sequence[dict[str, Any]]) -> None:
        await self.uow.access_log.record_many(entries)

    async def deny(
        self, viewer: ViewerDTO, subject_id: UUID, tables: Collection[str], reason: str
    ) -> None:
        """Journals a refused read in a transaction of its own: the refused request
        rolls its own one back."""
        keys = {field.key for table in tables for field in sensitive_fields_of(table)}
        if keys:
            await self.deny_many(
                [access_entry(viewer, subject_id, AccessAction.DENIED, keys, reason)]
            )

    async def deny_many(self, entries: Sequence[dict[str, Any]]) -> None:
        if not entries:
            return
        async with self.uow() as uow:
            await uow.access_log.record_many(entries)
            await uow.commit()

    @required_transaction
    async def _read_fields(
        self, person_ids: Collection[UUID], keys: Collection[str]
    ) -> dict[UUID, list[dict[str, Any]]]:
        """The values of the registry fields `keys` of each person: a record per
        stored row, and a row that extends another one joins its record. It
        journals nothing; the caller records what it hands out."""
        by_table: dict[str, list[PersonalField]] = {}
        for key in _ordered(keys):
            field = get_field(key)
            by_table.setdefault(field.columns[0].table, []).append(field)
        stored: list[tuple[str, StoredRow]] = []
        for table, fields in by_table.items():
            source = source_of(table)
            parent = source_of(source.parent) if source.parent else None
            names = {
                name
                for field in fields
                for column in field.columns
                for name in (column.column, *(column.where or ())[:1])
            }
            rows = await self.uow.registry_rows.rows(source, parent, names, person_ids)
            stored.extend((table, row) for row in rows)
        opened = await self._open_stored(stored)
        labels = await self._labels(by_table, opened)
        records: dict[UUID, dict[tuple[str, Any], dict[str, Any]]] = {
            person_id: {} for person_id in person_ids
        }
        for table, (person_id, row_id, values) in opened:
            root = source_of(table).parent or table
            for field in by_table[table]:
                if not _matches(field, values):
                    continue
                shown = {
                    column.column: _shown(column, values[column.column], labels)
                    for column in field.columns
                }
                records[person_id].setdefault((root, row_id), {})[field.key] = (
                    next(iter(shown.values())) if len(shown) == 1 else shown
                )
        return {person_id: list(rows.values()) for person_id, rows in records.items()}

    @required_transaction
    async def _open_stored(
        self, stored: Sequence[tuple[str, StoredRow]]
    ) -> list[tuple[str, StoredRow]]:
        needed = {
            person_id
            for table, (person_id, _, values) in stored
            if any(values.get(name) is not None for name in encrypted_columns(table))
        }
        keys = await self._read_keys(needed)
        try:
            return [
                (
                    table,
                    (
                        person_id,
                        row_id,
                        self._open_row(
                            table,
                            encrypted_columns(table),
                            keys,
                            person_id,
                            row_id,
                            values,
                        ),
                    ),
                )
                for table, (person_id, row_id, values) in stored
            ]
        except DecryptionError as exc:
            logger.error("Personal data cannot be decrypted: %s", exc.code)
            raise PersonalDataUnavailable() from None
        finally:
            for dek, _ in keys.values():
                wipe(dek)

    @required_transaction
    async def _labels(
        self,
        by_table: Mapping[str, Sequence[PersonalField]],
        opened: Sequence[tuple[str, StoredRow]],
    ) -> dict[tuple[str, Any], Any]:
        wanted: dict[str, tuple[Column, set[Any]]] = {}
        for table, (_, _, values) in opened:
            for field in by_table[table]:
                for column in field.columns:
                    value = values.get(column.column)
                    if column.ref is None or value is None:
                        continue
                    wanted.setdefault(column.ref.table, (column, set()))[1].add(value)
        labels: dict[tuple[str, Any], Any] = {}
        for ref_table, (column, keys) in wanted.items():
            assert column.ref is not None
            found = await self.uow.registry_rows.labels(column.ref, keys)
            labels.update(((ref_table, key), label) for key, label in found.items())
        return labels

    @staticmethod
    def _open_row(
        table: str,
        columns: Mapping[str, Column],
        keys: Mapping[UUID, tuple[bytearray, int]],
        person_id: UUID,
        row_id: UUID,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        opened = dict(values)
        for name, column in columns.items():
            blob = values.get(name)
            if blob is None:
                continue
            dek, version = keys[person_id]
            if cipher.dek_version_of(blob) != version:
                raise DecryptionError("dek_version")
            opened[name] = cipher.decode(
                cipher.open_sealed(dek, blob, table, name, person_id, row_id),
                column.kind,
            )
        return opened

    @required_transaction
    async def _write_key(self, person_id: UUID) -> tuple[bytearray, int]:
        """The data key to seal with; a person without one, or whose key was
        destroyed, gets a new one (the next version after a destroyed key)."""
        row = (
            await self.uow.person_keys.of_persons([person_id], lock="update")
        ).get(person_id)
        if row is not None and row.wrapped_dek is not None:
            return (await self._read_keys([person_id]))[person_id]
        version = FIRST_DEK_VERSION if row is None else row.dek_version + 1
        if version > cipher.MAX_DEK_VERSION:
            logger.error("A person ran out of data key versions")
            raise PersonalDataUnavailable()
        dek = bytearray(os.urandom(cipher.DEK_SIZE))
        try:
            wrapped = await self.ring.wrap(bytes(dek), dek_context(person_id, version))
        except KeyProviderError as exc:
            wipe(dek)
            logger.error("A data key cannot be wrapped: %s", exc.code)
            raise PersonalDataUnavailable() from None
        if row is not None:
            await self.uow.person_keys.replace(
                person_id, wrapped.to_bytes(), wrapped.ref, version, None
            )
        elif not await self.uow.person_keys.insert_if_absent(
            person_id, wrapped.to_bytes(), wrapped.ref, version
        ):
            wipe(dek)
            return (await self._read_keys([person_id]))[person_id]
        self.cache.put((person_id, version), dek)
        return dek, version

    @required_transaction
    async def _read_keys(
        self, person_ids: Collection[UUID]
    ) -> dict[UUID, tuple[bytearray, int]]:
        if not person_ids:
            return {}
        stored = await self.uow.person_keys.of_persons(person_ids, lock="share")
        keys: dict[UUID, tuple[bytearray, int]] = {}
        pending: list[PersonKeyORM] = []
        for person_id in person_ids:
            row = stored.get(person_id)
            if row is None or row.wrapped_dek is None:
                logger.error("Personal data has no data key")
                raise PersonalDataUnavailable()
            cached = self.cache.get((person_id, row.dek_version))
            if cached is None:
                pending.append(row)
            else:
                keys[person_id] = (cached, row.dek_version)
        limit = asyncio.Semaphore(max(settings.KMS_UNWRAP_CONCURRENCY, 1))

        async def unwrap(row: PersonKeyORM) -> tuple[UUID, bytearray, int]:
            assert row.wrapped_dek is not None
            async with limit:
                dek = bytearray(
                    await self.ring.unwrap(
                        WrappedKey.from_bytes(row.wrapped_dek),
                        dek_context(row.person_id, row.dek_version),
                    )
                )
            self.cache.put((row.person_id, row.dek_version), dek)
            return row.person_id, dek, row.dek_version

        try:
            for person_id, dek, version in await asyncio.gather(
                *(unwrap(row) for row in pending)
            ):
                keys[person_id] = (dek, version)
        except KeyProviderError as exc:
            for dek, _ in keys.values():
                wipe(dek)
            logger.error("A data key cannot be unwrapped: %s", exc.code)
            raise PersonalDataUnavailable() from None
        return keys
