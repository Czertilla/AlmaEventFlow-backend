from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from event.dependency.role import RoleUOWDep
from event.filter.role import RoleFilter
from ...schema.role import (
    RoleCreate,
    RolePatch,
    RolePatchData,
    RolePut,
    RolePutData,
    RoleRead,
)
from event.service.role import RoleService

router = APIRouter(prefix="/roles", tags=["role"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_roles(
    uow: RoleUOWDep,
    user: UserJWTDep,
    filter: RoleFilter = FilterDepends(RoleFilter),
    page_param=Depends(SPageParam),
) -> SPage[RoleRead]:
    return await RoleService(uow).search(filter, page_param)


@router.post("", responses={**auth_responses()})
async def create_role(
    role: RoleCreate, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).create(role)


@router.get("/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")})
async def get_role(
    role_id: UUID, user: UserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).read(role_id)


@router.put("/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")})
async def put_role(
    role_id: UUID, role: RolePutData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).put(RolePut(id=role_id, **role.model_dump()))


@router.patch("/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")})
async def patch_role(
    role_id: UUID, role: RolePatchData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).patch(
        RolePatch(id=role_id, **role.model_dump())
    )


@router.delete("/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")})
async def delete_role(
    role_id: UUID, user: SuperUserJWTDep, uow: RoleUOWDep
) -> None:
    await RoleService(uow).delete(role_id)
