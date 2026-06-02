from logging import getLogger
from uuid import UUID

from core.schema.message.org import OrganizationData
from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction
from org.exc.collective import CollectiveNotExistsException
from org.filter.collective import CollectiveFilter
from org.models.collective import CollectiveORM
from org.models.organization import OrganizationORM
from org.schema.collective import (
    CollectiveCreate,
    CollectivePatch,
    CollectivePut,
    CollectiveRead,
)
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.uow.collective import CollectiveUOW

logger = getLogger(__name__)


class CollectiveService(BaseService[CollectiveUOW]):
    @required_transaction
    async def _create(
        self, collective_create: CollectiveCreate
    ) -> CollectiveORM:
        collective = CollectiveORM(**collective_create.model_dump())
        self.uow.session.add(collective)
        await self.uow.session.flush()
        return collective

    @required_transaction
    async def _read(self, collective_id: UUID) -> CollectiveORM | None:
        collective = await self.uow.collectives.get_by_id(collective_id)
        if collective is None:
            raise CollectiveNotExistsException()
        return collective

    @required_transaction
    async def _update(
        self,
        collective_id: UUID,
        collective_data: dict,
        *,
        flush: bool = False,
    ) -> CollectiveORM:
        organization = await self.uow.session.get(
            OrganizationORM, collective_id
        )
        if organization is None:
            raise CollectiveNotExistsException()
        collective = CollectiveORM(**collective_data, id=collective_id)

        return await self.uow.session.merge(collective)

    async def create(
        self, collective_create: CollectiveCreate
    ) -> CollectiveRead:
        async with self.uow as uow:
            result = CollectiveRead.model_validate(
                await self._create(collective_create)
            )
            await uow.commit()
        await on_organization_created(
            OrganizationData(**result.model_dump(exclude={"type"}), type="collective")
        )
        return result

    async def read(self, collective_id: UUID) -> CollectiveRead:
        async with self.uow:
            return CollectiveRead.model_validate(
                await self._read(collective_id)
            )

    async def patch(self, collective_patch: CollectivePatch) -> CollectiveRead:
        async with self.uow as uow:
            collective_data = collective_patch.model_dump()
            result = CollectiveRead.model_validate(
                await self._update(collective_data.pop("id"), collective_data)
            )
            await uow.commit()
        await on_organization_updated(
            OrganizationData(**result.model_dump(exclude={"type"}), type="collective")
        )
        return result

    async def put(self, collective_put: CollectivePut) -> CollectiveRead:
        async with self.uow as uow:
            result = CollectiveRead.model_validate(
                await self.uow.collectives.upsert(collective_put.model_dump())
            )
            await uow.commit()
        await on_organization_updated(
            OrganizationData(**result.model_dump())
        )
        return result

    async def search(
        self, filter: CollectiveFilter, pagination: SPageParam
    ) -> SPage[CollectiveRead]:
        async with self.uow:
            items, total = await self.uow.collectives.search(
                filter, pagination
            )
            return SPage(
                items=[CollectiveRead.model_validate(item) for item in items],
                pagination=SPagination.sql_validate(
                    page=pagination.page,
                    limit=pagination.limit,
                    total=total,
                ),
            )

    async def delete(self, collective_id: UUID) -> None:
        async with self.uow as uow:
            await self.uow.collectives.delete_one(collective_id)
            await uow.commit()
        await on_organization_deleted(collective_id)
