from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction

from org.exc.organization import OrganizationNotExistsException
from org.models.organization import OrganizationORM
from org.schema.organization import (
    OrganizationCreate,
    OrganizationPatch,
    OrganizationPut,
    OrganizationRead,
)
from org.api.kafka.pub.organization import (
    on_organization_created,
    on_organization_deleted,
    on_organization_updated,
)
from org.uow.organization import OrganizationUOW

logger = getLogger(__name__)


class OrganizationService(BaseService[OrganizationUOW]):
    @required_transaction
    async def _create(
        self, organization_create: OrganizationCreate
    ) -> OrganizationORM:
        return await self.uow.organizations.add_n_return(
            data=organization_create.model_dump()
        )

    @required_transaction
    async def _read(self, organization_id: UUID) -> OrganizationORM | None:
        organization = await self.uow.organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotExistsException()
        return organization

    @required_transaction
    async def _update(
        self,
        organization_id: UUID,
        organization_data: dict,
        *,
        flush: bool = False,
    ) -> OrganizationORM:
        organization = await self.uow.organizations.update_one(
            organization_id, organization_data, flush
        )
        if organization is None:
            raise OrganizationNotExistsException()
        return organization

    async def create(
        self, organization_create: OrganizationCreate
    ) -> OrganizationRead:
        async with self.uow as uow:
            result = OrganizationRead.model_validate(
                await self._create(organization_create)
            )
            await uow.commit()
        await on_organization_created(result)
        return result

    async def read(self, organization_id: UUID) -> OrganizationRead:
        async with self.uow:
            return OrganizationRead.model_validate(
                await self._read(organization_id)
            )

    async def patch(
        self, organization_patch: OrganizationPatch
    ) -> OrganizationRead:
        async with self.uow as uow:
            organization_data = organization_patch.model_dump()
            result = OrganizationRead.model_validate(
                await self._update(
                    organization_data.pop("id"), organization_data
                )
            )
            await uow.commit()
        await on_organization_updated(result)
        return result

    async def put(self, organization_put: OrganizationPut) -> OrganizationRead:
        async with self.uow as uow:
            result = OrganizationRead.model_validate(
                await self.uow.organizations.upsert(
                    organization_put.model_dump()
                )
            )
            await uow.commit()
        await on_organization_updated(result)
        return result

    async def delete(self, organization_id: UUID) -> None:
        async with self.uow as uow:
            await self.uow.organizations.delete_one(organization_id)
            await uow.commit()
        await on_organization_deleted(organization_id)
