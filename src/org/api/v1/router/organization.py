from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from org.api.v1.schema.organization import (
    OrganizationCreate,
    OrganizationPatch,
    OrganizationPatchData,
    OrganizationRead,
)
from org.dependency.organization import OrganizationUOWDep
from org.filter.organization import OrganizationFilter
from org.service.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organization"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def list_organizations(
    uow: OrganizationUOWDep,
    user: UserJWTDep,
    filter: OrganizationFilter = FilterDepends(OrganizationFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[OrganizationRead]:
    return PageV1[OrganizationRead].from_dto_with_page_count(
        await OrganizationService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{organization_id}",
    responses={**auth_responses(), **entity_not_found_responses("organization")},
)
async def get_organization(
    organization_id: UUID, user: UserJWTDep, uow: OrganizationUOWDep
) -> OrganizationRead:
    return OrganizationRead.from_dto(
        await OrganizationService(uow).read(organization_id)
    )


@router.post("", responses={**auth_responses()})
async def create_organization(
    organization: OrganizationCreate,
    user: SuperUserJWTDep,
    uow: OrganizationUOWDep,
) -> OrganizationRead:
    return OrganizationRead.from_dto(
        await OrganizationService(uow).create(organization.to_dto())
    )


@router.patch(
    "/{organization_id}",
    responses={**auth_responses(), **entity_not_found_responses("organization")},
)
async def patch_organization(
    organization_id: UUID,
    organization: OrganizationPatchData,
    user: SuperUserJWTDep,
    uow: OrganizationUOWDep,
) -> OrganizationRead:
    return OrganizationRead.from_dto(
        await OrganizationService(uow).patch(
            OrganizationPatch.model_validate(
                {"id": organization_id, **organization.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/{organization_id}",
    responses={**auth_responses(), **entity_not_found_responses("organization")},
)
async def delete_organization(
    organization_id: UUID, user: SuperUserJWTDep, uow: OrganizationUOWDep
) -> None:
    await OrganizationService(uow).delete(organization_id)
