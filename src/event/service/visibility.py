from collections.abc import Collection
from uuid import UUID

from core.service.base import BaseService
from event.dto.scope import CollectiveScopeDTO
from event.uow.member import MemberUOW


class VisibilityService(BaseService[MemberUOW]):
    async def collective_scope(
        self, person_id: UUID | None, is_superuser: bool
    ) -> CollectiveScopeDTO:
        if is_superuser:
            return CollectiveScopeDTO()
        if person_id is None:
            return CollectiveScopeDTO(frozenset())
        async with self.uow:
            return CollectiveScopeDTO(
                frozenset(await self.uow.members.collective_ids_of(person_id))
            )

    async def shared_subjects(
        self, viewer_person_id: UUID, subjects: Collection[UUID] | None = None
    ) -> set[UUID]:
        """The subjects who lead or actively belong to a collective the viewer
        leads or actively belongs to."""
        async with self.uow:
            collective_ids = await self.uow.members.collective_ids_of(viewer_person_id)
            return await self.uow.members.active_person_ids_in(collective_ids, subjects)
