from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from event.filter.link import LinkFilter
from event.models.link import EventLinkORM
from event.schema.link import (
    LinkCreate,
    LinkPatch,
    LinkPut,
    LinkRead,
)
from event.uow.link import LinkUOW

logger = getLogger(__name__)


class LinkService(BaseService[LinkUOW]):
    @required_transaction
    async def _create(self, link_create: LinkCreate) -> EventLinkORM:
        link_data = link_create.model_dump()
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

    async def create(self, link_create: LinkCreate) -> LinkRead:
        async with self.uow as uow:
            link = await self._create(link_create)
            result = LinkRead.model_validate(link)
            await uow.commit()
        return result

    async def read(self, link_id: UUID) -> LinkRead:
        async with self.uow:
            link = await self._read(link_id)
            return LinkRead.model_validate(link)

    async def patch(self, link_patch: LinkPatch) -> LinkRead:
        async with self.uow as uow:
            link_data = link_patch.model_dump()
            link = await self._update(link_patch.id, link_data)
            result = LinkRead.model_validate(link)
            await uow.commit()
        return result

    async def put(self, link_put: LinkPut) -> LinkRead:
        async with self.uow as uow:
            link_data = link_put.model_dump()
            link_id = link_data.pop("id")
            link = await self._update(link_id, link_data)
            result = LinkRead.model_validate(link)
            await uow.commit()
        return result

    async def delete(self, link_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(link_id)
            await uow.commit()

    async def search(
        self, filter: LinkFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[LinkRead]:
        async with self.uow as uow:
            items, total = await uow.links.search(filter, page_params)
            return SPage(
                items=[LinkRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
