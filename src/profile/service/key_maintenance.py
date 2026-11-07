import asyncio
import os
from collections.abc import Callable, Collection, Mapping
from datetime import UTC, datetime, timedelta
from logging import getLogger
from profile.crypto import DecryptionError, WrappedKey, cipher
from profile.crypto.cache import wipe
from profile.dto.access import AccessFieldDTO, ViewerDTO
from profile.dto.key_maintenance import (
    DestroyedKeyDTO,
    DestroyKeyDTO,
    KeyStatusDTO,
    RewrapReportDTO,
    RotationReportDTO,
)
from profile.enum.access import AccessAction
from profile.exc.person import PersonNotExistsException
from profile.exc.personal_data import DestroyNotConfirmed, PersonKeyAbsent
from profile.models import PersonORM
from profile.models.person_key import PersonKeyORM
from profile.registry import (
    Column,
    all_fields,
    encrypted_columns,
    encrypted_tables,
    source_of,
)
from profile.service.personal_data import (
    PersonalDataService,
    access_entry,
    dek_context,
    labels_of,
)
from uuid import UUID

from core.config.settings import settings
from core.service.base import required_transaction
from core.utils.tz import localize

logger = getLogger(__name__)

Progress = Callable[[int, int], None]


def _required(table: str, columns: Mapping[str, Column]) -> bool:
    """Whether the encrypted value is what the row is for: a NOT NULL column."""
    stored = PersonORM.metadata.tables.get(table)
    return stored is not None and any(
        name in stored.columns and not stored.columns[name].nullable
        for name in columns
    )


class KeyMaintenanceService(PersonalDataService):
    """Jobs over the data keys: moving them under another key encryption key or
    another provider (rewrap), giving a person a new data key (rotation) and
    destroying one together with what it encrypts (crypto-shredding)."""

    async def status(self) -> KeyStatusDTO:
        async with self.uow:
            return KeyStatusDTO(
                by_key_ref=await self.uow.person_keys.by_key_ref(),
                by_dek_version=await self.uow.person_keys.by_dek_version(),
                destroyed=await self.uow.person_keys.destroyed(),
            )

    async def rewrap(
        self,
        *,
        batch_size: int | None = None,
        pause_ms: int | None = None,
        dry_run: bool = False,
        progress: Progress | None = None,
    ) -> RewrapReportDTO:
        """Unwraps every live data key not wrapped by the current key of the
        ring's active provider and wraps it again with it. The data stays as it
        is; a run that stops is resumed by running it again."""
        target = self.ring.active
        current = await target.current_key_ref()
        target_ref = f"{target.provider_id}:{current.name}:{current.version}"
        async with self.uow:
            found = await self.uow.person_keys.count_not_on(target_ref)
        if dry_run or not found:
            return RewrapReportDTO(target_ref, found, 0, dry_run)
        await self.ring.self_test()
        done = 0
        while True:
            async with self.uow:
                rows = await self.uow.person_keys.lock_not_on(
                    target_ref, batch_size or settings.MIGRATION_BATCH_SIZE
                )
                if not rows:
                    break
                for row in rows:
                    target_ref = await self._rewrap_one(row)
                await self.uow.commit()
            done += len(rows)
            if progress is not None:
                progress(done, found)
            await self._pause(pause_ms)
        return RewrapReportDTO(target_ref, found, done, False)

    async def rotate(
        self,
        person_ids: Collection[UUID] | None = None,
        older_than: timedelta | None = None,
        *,
        batch_size: int | None = None,
        pause_ms: int | None = None,
        dry_run: bool = False,
        progress: Progress | None = None,
    ) -> RotationReportDTO:
        """Gives each person a new data key and seals their values again with it,
        one person per transaction."""
        before = datetime.now(UTC) - older_than if older_than is not None else None
        async with self.uow:
            candidates = await self.uow.person_keys.rotation_candidates(
                person_ids, before
            )
        if dry_run or not candidates:
            return RotationReportDTO(len(candidates), 0, dry_run)
        size = max(batch_size or settings.MIGRATION_BATCH_SIZE, 1)
        rotated = 0
        for start in range(0, len(candidates), size):
            for person_id in candidates[start : start + size]:
                async with self.uow:
                    if await self._rotate_one(person_id, before):
                        rotated += 1
                    await self.uow.commit()
            if progress is not None:
                progress(min(start + size, len(candidates)), len(candidates))
            await self._pause(pause_ms)
        return RotationReportDTO(len(candidates), rotated, False)

    async def destroy(
        self, person_id: UUID, data: DestroyKeyDTO, actor: ViewerDTO | None
    ) -> DestroyedKeyDTO:
        """Destroys the person's data key and, in the same transaction, the rows
        it encrypted: a row whose encrypted value is required goes, an optional
        value becomes NULL. Journaled and told to the person."""
        if data.confirm_person_id != person_id:
            raise DestroyNotConfirmed()
        now = datetime.now(UTC)
        async with self.uow:
            if await self.uow.persons.get_by_id(person_id) is None:
                raise PersonNotExistsException()
            row = (
                await self.uow.person_keys.of_persons([person_id], lock="update")
            ).get(person_id)
            if row is None or row.wrapped_dek is None:
                raise PersonKeyAbsent()
            deleted, cleared = await self._shred_rows(person_id)
            await self.uow.person_keys.destroy(person_id, now)
            keys = [field.key for field in all_fields() if field.encrypted]
            await self._record(
                [
                    access_entry(
                        actor,
                        person_id,
                        AccessAction.KEY_DESTROYED,
                        keys,
                        notified=True,
                    )
                ]
            )
            who = (
                await self._actor_name(actor)
                if actor is not None
                else "оператор системы"
            )
            local = localize(now)
            await self._tell(
                person_id,
                "Ваши данные уничтожены",
                f"Удалены без возможности восстановления: {labels_of(keys)}. "
                f"Кто: {who}. Причина: «{data.reason.strip()}». "
                f"Когда: {local:%d.%m.%Y %H:%M} {local.tzname()}.",
                {"kind": "key_destroyed"},
                now,
            )
            destroyed = DestroyedKeyDTO(
                person_id=person_id,
                destroyed_at=now,
                fields=[
                    AccessFieldDTO(key=field.key, label=field.label)
                    for field in all_fields()
                    if field.encrypted
                ],
                rows_deleted=deleted,
                rows_cleared=cleared,
            )
            await self.uow.commit()
        self.cache.drop(person_id)
        logger.info("The data key of a person was destroyed: %s", person_id)
        return destroyed

    @required_transaction
    async def _rewrap_one(self, row: PersonKeyORM) -> str:
        assert row.wrapped_dek is not None
        context = dek_context(row.person_id, row.dek_version)
        dek = bytearray(
            await self.ring.unwrap(WrappedKey.from_bytes(row.wrapped_dek), context)
        )
        try:
            wrapped = await self.ring.wrap(bytes(dek), context)
        finally:
            wipe(dek)
        await self.uow.person_keys.rewrap(
            row.person_id, wrapped.to_bytes(), wrapped.ref
        )
        return wrapped.ref

    @required_transaction
    async def _rotate_one(self, person_id: UUID, before: datetime | None) -> bool:
        row = (await self.uow.person_keys.of_persons([person_id], lock="update")).get(
            person_id
        )
        if row is None or row.wrapped_dek is None:
            return False
        if before is not None and (row.rotated_at or row.created_at) >= before:
            return False
        old_version = row.dek_version
        new_version = old_version + 1
        if new_version > cipher.MAX_DEK_VERSION:
            raise DecryptionError("dek_version_exhausted")
        old = bytearray(
            await self.ring.unwrap(
                WrappedKey.from_bytes(row.wrapped_dek),
                dek_context(person_id, old_version),
            )
        )
        new = bytearray(os.urandom(cipher.DEK_SIZE))
        try:
            for table in encrypted_tables():
                columns = encrypted_columns(table)
                source = source_of(table)
                parent = source_of(source.parent) if source.parent else None
                for _, row_id, values in await self.uow.registry_rows.rows(
                    source, parent, columns, [person_id]
                ):
                    sealed: dict[str, bytes] = {}
                    for name, blob in values.items():
                        if blob is None:
                            continue
                        if cipher.dek_version_of(blob) != old_version:
                            raise DecryptionError("dek_version")
                        plain = cipher.open_sealed(
                            old, blob, table, name, person_id, row_id
                        )
                        sealed[name] = cipher.seal(
                            new, new_version, plain, table, name, person_id, row_id
                        )
                    if sealed:
                        await self.uow.registry_rows.update_row(source, row_id, sealed)
            wrapped = await self.ring.wrap(
                bytes(new), dek_context(person_id, new_version)
            )
            await self.uow.person_keys.replace(
                person_id,
                wrapped.to_bytes(),
                wrapped.ref,
                new_version,
                datetime.now(UTC),
            )
        finally:
            wipe(old)
            wipe(new)
        self.cache.drop(person_id)
        return True

    @required_transaction
    async def _shred_rows(self, person_id: UUID) -> tuple[int, int]:
        deleted = cleared = 0
        for table in encrypted_tables():
            columns = encrypted_columns(table)
            source = source_of(table)
            parent = source_of(source.parent) if source.parent else None
            rows = await self.uow.registry_rows.rows(
                source, parent, columns, [person_id]
            )
            if not rows:
                continue
            if _required(table, columns):
                await self.uow.registry_rows.delete_rows(
                    source, [row_id for _, row_id, _ in rows]
                )
                deleted += len(rows)
                continue
            for _, row_id, values in rows:
                if any(value is not None for value in values.values()):
                    await self.uow.registry_rows.update_row(
                        source, row_id, dict.fromkeys(columns)
                    )
                    cleared += 1
        return deleted, cleared

    @staticmethod
    async def _pause(pause_ms: int | None) -> None:
        pause = settings.MIGRATION_SLEEP_MS if pause_ms is None else pause_ms
        if pause > 0:
            await asyncio.sleep(pause / 1000)
