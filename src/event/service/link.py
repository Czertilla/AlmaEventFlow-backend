from logging import getLogger
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.link import (
    LinkCreateDTO,
    LinkDTO,
    LinkFilterDTO,
    LinkPatchDTO,
    LinkPutDTO,
)
from event.filter.link import LinkFilter
from event.models.link import EventLinkORM
from event.uow.link import LinkUOW

logger = getLogger(__name__)


class LinkService(BaseService[LinkUOW]):
    @staticmethod
    def _to_dto(link: EventLinkORM) -> LinkDTO:
        return dto_from_orm(link, LinkDTO)

    @required_transaction
    async def _create(self, link_create: LinkCreateDTO) -> EventLinkORM:
        link_data = dto_dict(link_create)
        link = await self.uow.links.add_n_return(data=link_data)
        await self.uow.session.flush(objects=[link])
        return link

    @required_transaction
    async def _read(self, link_id: UUID) -> EventLinkORM | None:
        link = await self.uow.links.get_by_id(link_id)
        return link

    @required_transaction
    async def _update(
        self, link_id: UUID, link_data: dict, *, flush: bool = False
    ) -> EventLinkORM:
        link = await self.uow.links.update_one(link_id, link_data, flush)
        return link

    @required_transaction
    async def _delete(self, link_id: UUID) -> None:
        await self.uow.links.delete_one(link_id)

    async def create(self, link_create: LinkCreateDTO) -> LinkDTO:
        async with self.uow as uow:
            link = await self._create(link_create)
            result = self._to_dto(link)
            await uow.commit()
        return result

    async def read(self, link_id: UUID) -> LinkDTO:
        async with self.uow:
            link = await self._read(link_id)
            return self._to_dto(link)

    async def patch(self, link_patch: LinkPatchDTO) -> LinkDTO:
        async with self.uow as uow:
            link_data = dto_dict(link_patch, only_set=True)
            link = await self._update(link_patch.id, link_data)
            result = self._to_dto(link)
            await uow.commit()
        return result

    async def put(self, link_put: LinkPutDTO) -> LinkDTO:
        async with self.uow as uow:
            link_data = dto_dict(link_put, exclude={"id"})
            link = await self._update(link_put.id, link_data)
            result = self._to_dto(link)
            await uow.commit()
        return result

    async def delete(self, link_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(link_id)
            await uow.commit()

    async def search(
        self, filter: LinkFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[LinkDTO]:
        async with self.uow as uow:
            orm_filter = LinkFilter.from_dto(filter)
            items, total = await uow.links.search(orm_filter, page_params)
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
