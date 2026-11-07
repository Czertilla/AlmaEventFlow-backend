from uuid import UUID

from core.service.base import BaseService
from event.dto.collective_access import CollectivePrincipalDTO
from event.uow.collective_access import CollectiveAccessUOW


class CollectiveAccessService(BaseService[CollectiveAccessUOW]):
    """What profile asks before it hands out data by a grant: whether a person
    leads a collective now, and who its active members are now."""

    async def principal_check(
        self, person_id: UUID, collective_id: UUID
    ) -> CollectivePrincipalDTO:
        async with self.uow:
            collective = await self.uow.collectives.get_by_id(collective_id)
            if collective is None or collective.principal_id != person_id:
                return CollectivePrincipalDTO(is_principal=False)
            return CollectivePrincipalDTO(
                is_principal=True,
                name=collective.name,
                is_verified=collective.is_verified,
            )

    async def active_members(self, collective_id: UUID) -> set[UUID]:
        async with self.uow:
            return await self.uow.members.active_person_ids_of(collective_id)
