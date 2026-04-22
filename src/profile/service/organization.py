from logging import getLogger

from core.schema.message.org import OrganizationData
from core.service.base import required_transaction
from core.service.event.organization import (
    OrganizationEventService as BaseService,
)

from profile.uow.organization import OrganizationUOW

logger = getLogger(__name__)


class OrganizationService(BaseService[OrganizationUOW]):
    @staticmethod
    def _validate_data(organization: OrganizationData):
        return {"id": organization.id, "type": organization.type}

    @required_transaction
    async def _create(self, organization: OrganizationData):
        await self.uow.organizations.add_n_return(
            data=self._validate_data(organization)
        )

    @required_transaction
    async def _upsert(self, organization: OrganizationData):
        await self.uow.organizations.upsert(
            data=self._validate_data(organization)
        )
