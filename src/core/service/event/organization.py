from typing import Generic, TypeVar
from uuid import UUID
from core.service.base import BaseService, required_transaction
from core.uow.event.organization import OrganizationAUOW
from core.schema.message.org import OrganizationData, OrganizationDelete

UOW = TypeVar("UOW", bound=OrganizationAUOW)


class OrganizationEventService(BaseService[UOW], Generic[UOW]):
    @required_transaction
    async def _create(self, organization: OrganizationData):
        await self.uow.organizations.add_n_return(
            data=organization.model_dump()
        )

    @required_transaction
    async def _upsert(self, organization: OrganizationData):
        await self.uow.organizations.upsert(data=organization.model_dump())

    @required_transaction
    async def _delete(self, organization_id: UUID):
        await self.uow.organizations.delete_one(organization_id)

    async def create(self, organizations: list[OrganizationData]) -> None:
        async with self.uow as uow:
            for organization in organizations:
                await self._create(organization)
            await uow.commit()

    async def update(self, organizations: list[OrganizationData]) -> None:
        async with self.uow as uow:
            for organization in organizations:
                await self._upsert(organization)
            await uow.commit()

    async def delete(self, organizations: list[OrganizationDelete]) -> None:
        async with self.uow as uow:
            for organization in organizations:
                await self._delete(organization.id)
            await uow.commit()
