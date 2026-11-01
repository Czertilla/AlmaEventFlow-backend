import asyncio
import os
from collections.abc import Collection, Mapping, Sequence
from logging import getLogger
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
from profile.exc.personal_data import PersonalDataUnavailable
from profile.models.person_key import PersonKeyORM
from profile.registry import Column, encrypted_columns
from profile.uow.person_key import PersonalDataUOW
from typing import Any
from uuid import UUID

from core.config.settings import settings
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)

FIRST_DEK_VERSION = 1

SealedRow = tuple[UUID, UUID, Mapping[str, Any]]


def dek_context(person_id: UUID, dek_version: int) -> bytes:
    return f"person_key|{person_id}|{dek_version}".encode()


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
        self, table: str, rows: Sequence[SealedRow]
    ) -> list[dict[str, Any]]:
        columns = encrypted_columns(table)
        needed = {
            person_id
            for person_id, _, values in rows
            if any(values.get(name) is not None for name in columns)
        }
        keys = await self._read_keys(needed)
        try:
            return [
                self._open_row(table, columns, keys, person_id, row_id, values)
                for person_id, row_id, values in rows
            ]
        except DecryptionError as exc:
            logger.error("Personal data in %s cannot be decrypted: %s", table, exc.code)
            raise PersonalDataUnavailable() from None
        finally:
            for dek, _ in keys.values():
                wipe(dek)

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
