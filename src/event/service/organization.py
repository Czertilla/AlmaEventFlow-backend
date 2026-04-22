from logging import getLogger

from core.schema.message.org import OrganizationData
from core.service.base import required_transaction
from core.service.event.organization import OrganizationEventService
from event.models.collective import CollectiveORM
from event.uow.organization import OrganizationUOW

logger = getLogger(__name__)


class OrganizationService(OrganizationEventService[OrganizationUOW]):
    @required_transaction
    async def _create(self, organization: OrganizationData):
        data = organization.model_dump()
        if organization.type == "collective":
            collective = CollectiveORM(**data)
            self.uow.session.add(collective)
            await self.uow.session.flush([collective])
        else:
            await self.uow.organizations.add_n_return(data)

    @required_transaction
    async def _upsert(self, organization: OrganizationData):
        data = organization.model_dump()
        if organization.type == "collective":
            await self.uow.session.merge(CollectiveORM(**data))
        else:
            await self.uow.organizations.upsert(data=data)
