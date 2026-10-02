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
from org.dto.organization import (
    OrganizationCreateDTO,
    OrganizationDTO,
    OrganizationFilterDTO,
    OrganizationPatchDTO,
    OrganizationPutDTO,
)
from org.exc.organization import OrganizationNotExistsException
from org.filter.organization import OrganizationFilter
from org.models.organization import OrganizationORM
from org.uow.organization import OrganizationUOW

logger = getLogger(__name__)


class OrganizationService(BaseService[OrganizationUOW]):
    @staticmethod
    def _to_dto(organization: OrganizationORM) -> OrganizationDTO:
        return dto_from_orm(organization, OrganizationDTO)

    @staticmethod
    def _event(organization: OrganizationDTO) -> OrganizationData:
        return OrganizationData(**dto_dict(organization))

    @required_transaction
    async def _create(
        self, organization_create: OrganizationCreateDTO
    ) -> OrganizationORM:
        return await self.uow.organizations.add_n_return(
            data=dto_dict(organization_create)
        )

    @required_transaction
    async def _read(self, organization_id: UUID) -> OrganizationORM:
        organization = await self.uow.organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotExistsException()
        return organization

    @required_transaction
    async def _update(
        self,
        organization_id: UUID,
        organization_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> OrganizationORM:
        organization = await self.uow.organizations.update_one(
            organization_id, organization_data, flush
        )
        if organization is None:
            raise OrganizationNotExistsException()
        return organization

    @required_transaction
    async def _upsert(self, organization_put: OrganizationPutDTO) -> OrganizationORM:
        return await self.uow.organizations.upsert(dto_dict(organization_put))

    @required_transaction
    async def _delete(self, organization_id: UUID) -> None:
        await self.uow.organizations.delete_one(organization_id)

    async def create(
        self, organization_create: OrganizationCreateDTO
    ) -> OrganizationDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(organization_create))
            await uow.commit()
        await on_organization_created([self._event(result)])
        return result

    async def read(self, organization_id: UUID) -> OrganizationDTO:
        async with self.uow:
            return self._to_dto(await self._read(organization_id))

    async def patch(self, organization_patch: OrganizationPatchDTO) -> OrganizationDTO:
        async with self.uow as uow:
            organization_data = dto_dict(
                organization_patch, only_set=True, exclude={"id"}
            )
            result = self._to_dto(
                await self._update(organization_patch.id, organization_data)
            )
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def put(self, organization_put: OrganizationPutDTO) -> OrganizationDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(organization_put))
            await uow.commit()
        await on_organization_updated([self._event(result)])
        return result

    async def search(
        self, filter: OrganizationFilterDTO, pagination: PageParamDTO
    ) -> PageDTO[OrganizationDTO]:
        async with self.uow:
            items, total = await self.uow.organizations.search(
                OrganizationFilter.from_dto(filter), pagination
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=pagination.page,
                    limit=pagination.limit,
                    total=total,
                ),
            )

    async def delete(self, organization_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(organization_id)
            await uow.commit()
        await on_organization_deleted([organization_id])
