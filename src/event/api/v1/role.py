from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from event.dependency.role import RoleUOWDep
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


@router.post("")
async def create_role(
    role: RoleCreate, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).create(role)


@router.get("/{role_id}")
async def get_role(
    role_id: UUID, user: UserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).read(role_id)


@router.put("/{role_id}")
async def put_role(
    role_id: UUID, role: RolePutData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).put(RolePut(id=role_id, **role.model_dump()))


@router.patch("/{role_id}")
async def patch_role(
    role_id: UUID, role: RolePatchData, user: SuperUserJWTDep, uow: RoleUOWDep
) -> RoleRead:
    return await RoleService(uow).patch(
        RolePatch(id=role_id, **role.model_dump())
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID, user: SuperUserJWTDep, uow: RoleUOWDep
) -> None:
    await RoleService(uow).delete(role_id)
