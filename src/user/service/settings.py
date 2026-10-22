import json
from typing import Any
from uuid import UUID

from core.service.base import BaseService, required_transaction
from user.dto.settings import UserSettingsDTO, UserSettingsPatchDTO
from user.exceptions.user import SettingsTooLarge
from user.models.settings import UserSettingsORM
from user.uow.user import UserUOW

MAX_SETTINGS_BYTES = 16 * 1024


def merge_settings(
    current: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    """JSON merge patch over the top-level keys: ``None`` removes a key."""
    merged = dict(current)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def _size(data: dict[str, Any]) -> int:
    return len(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode())


def _to_dto(row: UserSettingsORM | None) -> UserSettingsDTO:
    if row is None:
        return UserSettingsDTO(values={}, revision=0, edited_at=None)
    return UserSettingsDTO(
        values=dict(row.data), revision=row.revision, edited_at=row.edited_at
    )


class SettingsService(BaseService[UserUOW]):
    async def read(self, user_id: UUID) -> UserSettingsDTO:
        async with self.uow as uow:
            return _to_dto(await uow.user_settings.get_for_user(user_id))

    @required_transaction
    async def _patch(
        self, user_id: UUID, patch: UserSettingsPatchDTO
    ) -> UserSettingsORM:
        row = await self.uow.user_settings.lock_for_user(user_id)
        merged = merge_settings(row.data, patch.values)
        if merged == row.data:
            return row
        if _size(merged) > MAX_SETTINGS_BYTES:
            raise SettingsTooLarge()
        row.data = merged
        row.revision += 1
        await self.uow.user_settings.flush()
        return row

    async def patch(
        self, user_id: UUID, patch: UserSettingsPatchDTO
    ) -> UserSettingsDTO:
        async with self.uow as uow:
            row = await self._patch(user_id, patch)
            dto = _to_dto(row)
            await uow.commit()
        return dto
