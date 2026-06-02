from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from org.dependency.organization import OrganizationUOWDep
from org.filter.organization import OrganizationFilter
from org.schema.organization import (
    OrganizationCreate,
    OrganizationPatch,
    OrganizationPut,
    OrganizationRead,
)
from org.service.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organization"])

logger = getLogger(__name__)


@router.get("")
async def list_organizations(
    uow: OrganizationUOWDep,
    user: UserJWTDep,
    filter: OrganizationFilter = FilterDepends(OrganizationFilter),
    page_param=Depends(SPageParam),
) -> SPage[OrganizationRead]:
    return await OrganizationService(uow).search(filter, page_param)


@router.post("")
async def create_organization(
    organization: OrganizationCreate,
    user: SuperUserJWTDep,
    uow: OrganizationUOWDep,
) -> OrganizationRead:
    return await OrganizationService(uow).create(organization)


@router.get("/{organization_id}")
async def get_organization(
    organization_id: UUID, user: UserJWTDep, uow: OrganizationUOWDep
) -> OrganizationRead:
    return await OrganizationService(uow).read(organization_id)


@router.put("/{organization_id}")
async def put_organization(
    organization_id: UUID,
    organization: OrganizationPut,
    user: SuperUserJWTDep,
    uow: OrganizationUOWDep,
) -> OrganizationRead:
    return await OrganizationService(uow).put(organization)


@router.patch("/{organization_id}")
async def patch_organization(
    organization_id: UUID,
    organization: OrganizationPatch,
    user: SuperUserJWTDep,
    uow: OrganizationUOWDep,
) -> OrganizationRead:
    return await OrganizationService(uow).patch(organization)


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: UUID, user: SuperUserJWTDep, uow: OrganizationUOWDep
) -> None:
    await OrganizationService(uow).delete(organization_id)
