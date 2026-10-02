from logging import getLogger
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.message.org import OrganizationData
from core.service.base import BaseService, required_transaction
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.dto.collective import (
    CollectiveCreateDTO,
    CollectiveDTO,
    CollectiveFilterDTO,
    CollectivePatchDTO,
    CollectivePutDTO,
)
from org.exc.collective import CollectiveNotExistsException
from org.filter.collective import CollectiveFilter
from org.models.collective import CollectiveORM
from org.uow.collective import CollectiveUOW

logger = getLogger(__name__)


class CollectiveService(BaseService[CollectiveUOW]):
    @staticmethod
    def _to_dto(collective: CollectiveORM) -> CollectiveDTO:
        return dto_from_orm(collective, CollectiveDTO)

    @staticmethod
    def _event(collective: CollectiveDTO) -> OrganizationData:
        return OrganizationData(**dto_dict(collective))

    @required_transaction
    async def _create(self, collective_create: CollectiveCreateDTO) -> CollectiveORM:
        collective = CollectiveORM(**dto_dict(collective_create))
        self.uow.session.add(collective)
        await self.uow.session.flush()
        return collective

    @required_transaction
    async def _read(self, collective_id: UUID) -> CollectiveORM:
        collective = await self.uow.collectives.get_by_id(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        return collective

    @required_transaction
    async def _update(
        self,
        collective_id: UUID,
        collective_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> CollectiveORM:
        # merge() on a transient partial instance would null out unpatched columns
        collective = await self.uow.collectives.get_by_id(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        for key, value in collective_data.items():
            setattr(collective, key, value)
        if flush:
            await self.uow.session.flush()
        return collective

    @required_transaction
    async def _upsert(self, collective_put: CollectivePutDTO) -> CollectiveORM:
        collective = await self.uow.collectives.get_by_id(collective_put.id)
        collective_data = dto_dict(collective_put, exclude={"id"})
        if collective is None:
            collective = CollectiveORM(id=collective_put.id, **collective_data)
            self.uow.session.add(collective)
        else:
            for key, value in collective_data.items():
                setattr(collective, key, value)
        await self.uow.session.flush()
        return collective

    @required_transaction
    async def _delete(self, collective_id: UUID) -> None:
        await self.uow.collectives.delete_one(collective_id)

    async def create(self, collective_create: CollectiveCreateDTO) -> CollectiveDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(collective_create))
            await uow.commit()
        await on_organization_created([self._event(result)])
        return result

    async def read(self, collective_id: UUID) -> CollectiveDTO:
        async with self.uow:
            return self._to_dto(await self._read(collective_id))

    async def patch(self, collective_patch: CollectivePatchDTO) -> CollectiveDTO:
        async with self.uow as uow:
            collective_data = dto_dict(collective_patch, only_set=True, exclude={"id"})
            result = self._to_dto(
                await self._update(collective_patch.id, collective_data)
            )
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def put(self, collective_put: CollectivePutDTO) -> CollectiveDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(collective_put))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def search(
        self, filter: CollectiveFilterDTO, pagination: PageParamDTO
    ) -> PageDTO[CollectiveDTO]:
        async with self.uow:
            items, total = await self.uow.collectives.search(
                CollectiveFilter.from_dto(filter), pagination
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=pagination.page,
                    limit=pagination.limit,
                    total=total,
                ),
            )

    async def delete(self, collective_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(collective_id)
            await uow.commit()
        await on_organization_deleted([collective_id])
