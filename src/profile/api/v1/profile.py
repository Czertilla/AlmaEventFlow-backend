from uuid import UUID
from fastapi import APIRouter, Depends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from profile.exc.user import NonPersonalUserException
from profile.dependency.profile import ProfileUOWDep
from profile.schema.profile import (
    ProfileCreate,
    ProfilePatch,
    ProfilePut,
    ProfileRead,
)
from profile.service.profile import ProfileService

router = APIRouter(prefix="/profiles", tags=["profile"])

logger = getLogger(__name__)


@router.get("")
async def get_many(
    uow: ProfileUOWDep,
    user: UserJWTDep,
    page_param=Depends(SPageParam),
) -> SPage[ProfileRead]:
    return await ProfileService(uow).read_many(page_param)


@router.get("/my")
async def get_my_profile(
    user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await ProfileService(uow).read(user.person_id)


@router.post("/new")
async def create_profile(
    profile: ProfileCreate, user: SuperUserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    return await ProfileService(uow).create(profile)


@router.put("/my")
async def put_my_profile(
    profile: ProfilePut, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await ProfileService(uow).put(profile)


@router.patch("/my")
async def patch_my_profile(
    profile: ProfilePatch, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return await ProfileService(uow).patch(profile)


@router.get("/{profile_id}")
async def get_profile(
    profile_id: UUID, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    return await ProfileService(uow).read(profile_id)


@router.put("/{profile_id}")
async def put_profile(
    profile: ProfilePut,
    user: SuperUserJWTDep,
    uow: ProfileUOWDep,
) -> ProfileRead:
    return await ProfileService(uow).put(profile)


@router.patch("/{profile_id}")
async def patch_profile(
    profile: ProfilePatch, user: SuperUserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    return await ProfileService(uow).patch(profile)


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: UUID, user: SuperUserJWTDep, uow: ProfileUOWDep
) -> None:
    await ProfileService(uow).delete(profile_id)
