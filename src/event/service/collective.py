from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.collective import (
    CollectiveDTO,
    CollectiveFilterDTO,
    CollectivePatchDTO,
    CollectiveSummaryDTO,
)
from event.exc.event import CollectiveNotExistsException
from event.filter.collective import CollectiveFilter
from event.models.collective import CollectiveORM
from event.uow.collective import CollectiveUOW


class CollectiveService(BaseService[CollectiveUOW]):
    @required_transaction
    async def _get_my_collectives(
        self, person_id: UUID | None
    ) -> list[CollectiveSummaryDTO]:
        collectives = await self.uow.collectives.get_by_principal_id(person_id)
        return [dto_from_orm(c, CollectiveSummaryDTO) for c in collectives]

    async def get_my_collectives(
        self, person_id: UUID | None
    ) -> list[CollectiveSummaryDTO]:
        if person_id is None:
            return []
        async with self.uow:
            return await self._get_my_collectives(person_id)

    @required_transaction
    async def _get_my_memberships(
        self, person_id: UUID
    ) -> list[CollectiveSummaryDTO]:
        collectives = await self.uow.collectives.get_by_member_person_id(
            person_id
        )
        return [dto_from_orm(c, CollectiveSummaryDTO) for c in collectives]

    async def get_my_memberships(
        self, person_id: UUID
    ) -> list[CollectiveSummaryDTO]:
        async with self.uow:
            return await self._get_my_memberships(person_id)

    @required_transaction
    async def _read(self, collective_id: UUID) -> CollectiveORM:
        collective = await self.uow.collectives.get_by_id(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        return collective

    @required_transaction
    async def _update(
        self, collective_id: UUID, data: dict[str, bool | None]
    ) -> CollectiveORM:
        collective = await self._read(collective_id)
        for key, value in data.items():
            setattr(collective, key, value)
        return await self.uow.collectives.add_entity(collective)

    async def read(self, collective_id: UUID) -> CollectiveDTO:
        async with self.uow:
            return dto_from_orm(await self._read(collective_id), CollectiveDTO)

    async def patch(self, patch: CollectivePatchDTO) -> CollectiveDTO:
        async with self.uow as uow:
            data = dto_dict(patch, only_set=True, exclude={"id"})
            result = dto_from_orm(await self._update(patch.id, data), CollectiveDTO)
            await uow.commit()
        return result

    async def search(
        self, filter: CollectiveFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[CollectiveDTO]:
        async with self.uow as uow:
            items, total = await uow.collectives.search(
                CollectiveFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[dto_from_orm(item, CollectiveDTO) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
