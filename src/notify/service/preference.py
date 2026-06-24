from logging import getLogger
from uuid import UUID

from core.enum.notify import TransportTypeEnum
from core.service.base import BaseService

from notify.schema.preference import (
    PreferenceItem,
    PreferencesRead,
    PreferencesUpdate,
)
from notify.transport import registry
from notify.uow.preference import PreferenceUOW

logger = getLogger(__name__)


class PreferenceService(BaseService[PreferenceUOW]):
    @staticmethod
    def _default(transport: TransportTypeEnum) -> bool:
        return transport in registry.DEFAULT_ENABLED

    def _resolve(self, stored: dict[TransportTypeEnum, bool]) -> list[PreferenceItem]:
        """Merges stored preferences with defaults across all known transports."""
        items: list[PreferenceItem] = []
        for transport in registry.all_transports():
            ttype = transport.type
            enabled = stored.get(ttype, self._default(ttype))
            if ttype == registry.GUARANTEED:
                enabled = True
            items.append(PreferenceItem(transport=ttype, is_enabled=enabled))
        return items

    async def get_my(self, user_id: UUID) -> PreferencesRead:
        async with self.uow as uow:
            rows = await uow.preferences.get_by_user(user_id)
            stored = {row.transport: row.is_enabled for row in rows}
        return PreferencesRead(preferences=self._resolve(stored))

    async def set_my(
        self, user_id: UUID, update: PreferencesUpdate
    ) -> PreferencesRead:
        desired: dict[TransportTypeEnum, bool] = {
            item.transport: item.is_enabled
            for item in update.preferences
            if registry.get(item.transport) is not None
        }
        desired[registry.GUARANTEED] = True
        async with self.uow as uow:
            await uow.preferences.delete_by_user(user_id)
            for transport, is_enabled in desired.items():
                await uow.preferences.add_one(
                    {
                        "user_id": user_id,
                        "transport": transport,
                        "is_enabled": is_enabled,
                    }
                )
            await uow.commit()
        return PreferencesRead(preferences=self._resolve(desired))
