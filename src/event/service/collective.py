from uuid import UUID

from core.dto.base import dto_from_orm
from core.service.base import BaseService, required_transaction
from event.dto.collective import CollectiveSummaryDTO
from event.uow.collective import CollectiveUOW


class CollectiveService(BaseService[CollectiveUOW]):
    @required_transaction
    async def _get_my_collectives(
        self, person_id: UUID
    ) -> list[CollectiveSummaryDTO]:
        collectives = await self.uow.collectives.get_by_principal_id(person_id)
        return [dto_from_orm(c, CollectiveSummaryDTO) for c in collectives]

    async def get_my_collectives(
        self, person_id: UUID
    ) -> list[CollectiveSummaryDTO]:
        async with self.uow:
            return await self._get_my_collectives(person_id)
