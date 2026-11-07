from collections.abc import Collection
from profile.enum.audience import Audience
from profile.registry import UNIT_HEAD_TYPES
from profile.uow.access import AccessUOW
from profile.utils.event import shared_collective_subjects
from uuid import UUID

from core.service.base import BaseService


class AccessDataService(BaseService[AccessUOW]):
    async def unit_heads(self, among: Collection[UUID] | None) -> set[UUID]:
        async with self.uow:
            return await self.uow.organizations.principals(UNIT_HEAD_TYPES, among)

    async def stored_audiences(
        self, field_key: str, among: Collection[UUID] | None
    ) -> dict[UUID, Audience]:
        async with self.uow:
            stored = await self.uow.visibility.stored(field_key, among)
        return {person_id: Audience(audience) for person_id, audience in stored.items()}

    async def shared_subjects(
        self, viewer_person_id: UUID, among: Collection[UUID] | None
    ) -> set[UUID]:
        return await shared_collective_subjects(viewer_person_id, among)
