from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.schema.collective import MyCollectiveRead
from event.uow.collective import CollectiveUOW


class CollectiveService(BaseService[CollectiveUOW]):
    @required_transaction
    async def _get_my_collectives(
        self, person_id: UUID
    ) -> list[MyCollectiveRead]:
        collectives = await self.uow.collectives.get_by_principal_id(person_id)
        return [MyCollectiveRead.model_validate(c) for c in collectives]

    async def get_my_collectives(
        self, person_id: UUID
    ) -> list[MyCollectiveRead]:
        async with self.uow:
            return await self._get_my_collectives(person_id)
