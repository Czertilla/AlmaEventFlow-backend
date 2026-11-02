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
    all_fields,
    encrypted_columns,
    get_field,
    sensitive_fields_of,
)
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


def _entry(
    viewer: ViewerDTO,
    subject: UUID,
    action: AccessAction,
    keys: Collection[str],
    outcome: str,
    *,
    notified: bool = False,
) -> dict[str, Any]:
    return {
        "actor_user_id": viewer.user_id,
        "actor_person_id": viewer.person_id,
        "subject_person_id": subject,
        "action": action.value,
        "via": (
            Via.NONE.value if action == AccessAction.DENIED else _via(viewer, subject)
        ),
        "fields": _ordered(keys),
        "outcome": outcome,
        "notified": notified,
        "request_id_http": viewer.http_request_id,
    }


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
                _entry(
                    viewer,
                    subject,
                    AccessAction.READ,
                    keys,
                    OUTCOME_OK,
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
        ordered = _ordered(keys)
        labels = ", ".join(get_field(key).label for key in ordered)
        local = localize(now)
        await self.uow.notification_outbox.enqueue(
            person_id=subject,
            category=NotificationCategory.system.value,
            title="Просмотр ваших данных",
            body=(
                f"Открыты ваши данные: {labels}. "
                f"Кто: {who}. Когда: {local:%d.%m.%Y %H:%M} {local.tzname()}."
            ),
            data={
                "kind": "sensitive_access",
                "fields": ",".join(ordered),
                "via": _via(viewer, subject),
                "actor_person_id": str(viewer.person_id or ""),
            },
            now=now,
        )

    async def deny(
        self, viewer: ViewerDTO, subject_id: UUID, tables: Collection[str], reason: str
    ) -> None:
        """Journals a refused read in a transaction of its own: the refused request
        rolls its own one back."""
        keys = {field.key for table in tables for field in sensitive_fields_of(table)}
        if not keys:
            return
        async with self.uow() as uow:
            await uow.access_log.record_many(
                [_entry(viewer, subject_id, AccessAction.DENIED, keys, reason)]
            )
            await uow.commit()

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
        stored = await self.uow.person_keys.of_persons([person_id])
        if person_id not in stored:
            dek = bytearray(os.urandom(cipher.DEK_SIZE))
            try:
                wrapped = await self.ring.wrap(
                    bytes(dek), dek_context(person_id, FIRST_DEK_VERSION)
                )
            except KeyProviderError as exc:
                wipe(dek)
                logger.error("A data key cannot be wrapped: %s", exc.code)
                raise PersonalDataUnavailable() from None
            if await self.uow.person_keys.insert_if_absent(
                person_id, wrapped.to_bytes(), wrapped.ref, FIRST_DEK_VERSION
            ):
                self.cache.put((person_id, FIRST_DEK_VERSION), dek)
                return dek, FIRST_DEK_VERSION
            wipe(dek)
        return (await self._read_keys([person_id]))[person_id]

    @required_transaction
    async def _read_keys(
        self, person_ids: Collection[UUID]
    ) -> dict[UUID, tuple[bytearray, int]]:
        if not person_ids:
            return {}
        stored = await self.uow.person_keys.of_persons(person_ids)
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
