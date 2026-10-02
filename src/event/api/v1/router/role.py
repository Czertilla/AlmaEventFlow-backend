from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.role import (
    RoleCreate,
    RolePatch,
    RolePatchData,
    RolePut,
    RolePutData,
    RoleRead,
)
from event.dependency.role import RoleUOWDep
from event.filter.role import RoleFilter
from event.service.role import RoleService

router = APIRouter(prefix="/roles", tags=["role"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_roles(
    uow: RoleUOWDep,
    user: UserJWTDep,
    filter: RoleFilter = FilterDepends(RoleFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[RoleRead]:
    return PageV1[RoleRead].from_dto(
        await RoleService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_role(
    role: RoleCreate, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return RoleRead.from_dto(await RoleService(uow).create(role.to_dto()))


@router.get(
    "/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")}
)
async def get_role(
    role_id: UUID, user: UserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return RoleRead.from_dto(await RoleService(uow).read(role_id))


@router.put(
    "/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")}
)
async def put_role(
    role_id: UUID, role: RolePutData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    result = await RoleService(uow).put(
        RolePut(id=role_id, **role.model_dump()).to_dto()
    )
    return RoleRead.from_dto(result)


@router.patch(
    "/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")}
)
async def patch_role(
    role_id: UUID, role: RolePatchData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    result = await RoleService(uow).patch(
        RolePatch(id=role_id, **role.model_dump()).to_dto()
    )
    return RoleRead.from_dto(result)


@router.delete(
    "/{role_id}", responses={**auth_responses(), **entity_not_found_responses("role")}
)
async def delete_role(
    role_id: UUID, user: SuperUserJWTDep, uow: RoleUOWDep
) -> None:
    await RoleService(uow).delete(role_id)
