from typing import Any
from uuid import UUID

from core.dto.base import dto_dict
from core.service.base import required_transaction
from org.dto.organization import OrganizationCreateDTO, OrganizationDTO
from org.enum.organization import OrganizationTypeEnum
from org.exc.organization import OrganizationNotExistsException
from org.filter.organization import OrganizationFilter
from org.models.organization import OrganizationORM
from org.service.base import OrgEntityService
from org.uow.organization import OrganizationUOW


class OrganizationService(OrgEntityService[OrganizationUOW]):
    model = OrganizationORM
    dto = OrganizationDTO
    filter_cls = OrganizationFilter
    not_found = OrganizationNotExistsException
    repo_name = "organizations"

    def _to_dto(self, entity: OrganizationORM) -> OrganizationDTO:
        return OrganizationDTO(
            id=entity.id,
            type=OrganizationTypeEnum(entity.type),
            name=entity.name,
            acronym=entity.acronym,
            principal_id=entity.principal_id,
            address_id=entity.address_id,
            created_at=entity.created_at,
            edited_at=entity.edited_at,
        )

    @required_transaction
    async def _create(self, create: OrganizationCreateDTO) -> OrganizationORM:
        return await self.uow.organizations.add_n_return(
            data={**dto_dict(create), "type": OrganizationTypeEnum.organization}
        )

    @required_transaction
    async def _update(
        self, entity_id: UUID, data: dict[str, Any]
    ) -> OrganizationORM:
        entity = await self.uow.organizations.update_one(entity_id, data)
        if entity is None:
            raise OrganizationNotExistsException()
        return entity
