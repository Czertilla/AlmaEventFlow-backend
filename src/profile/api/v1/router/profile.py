from logging import getLogger
from profile.api.v1.schema.profile import (
    ProfileCreate,
    ProfilePatch,
    ProfilePatchData,
    ProfilePut,
    ProfilePutData,
    ProfileRead,
)
from profile.dependency.profile import ProfileUOWDep
from profile.exc.user import NonPersonalUserException
from profile.filter.profile import ProfileFilter
from profile.service.profile import ProfileService
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
)
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/profiles", tags=["profile"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_many(
    uow: ProfileUOWDep,
    user: UserJWTDep,
    filter: ProfileFilter = FilterDepends(ProfileFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[ProfileRead]:
    return PageV1[ProfileRead].from_dto(
        await ProfileService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def get_my_profile(user: UserJWTDep, uow: ProfileUOWDep) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return ProfileRead.from_dto(await ProfileService(uow).read(user.person_id))


@router.post("", responses={**auth_responses()})
async def create_profile(
    profile: ProfileCreate, user: SuperUserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    return ProfileRead.from_dto(await ProfileService(uow).create(profile.to_dto()))


@router.put(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def put_my_profile(
    profile: ProfilePut, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return ProfileRead.from_dto(await ProfileService(uow).put(profile.to_dto()))


@router.patch(
    "/my",
    responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)},
)
async def patch_my_profile(
    profile: ProfilePatch, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    return ProfileRead.from_dto(await ProfileService(uow).patch(profile.to_dto()))


@router.get(
    "/{profile_id}",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def get_profile(
    profile_id: UUID, user: UserJWTDep, uow: ProfileUOWDep
) -> ProfileRead:
    return ProfileRead.from_dto(await ProfileService(uow).read(profile_id))


@router.put(
    "/{profile_id}",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def put_profile(
    profile_id: UUID,
    profile: ProfilePutData,
    user: SuperUserJWTDep,
    uow: ProfileUOWDep,
) -> ProfileRead:
    return ProfileRead.from_dto(
        await ProfileService(uow).put(
            ProfilePut(id=profile_id, **profile.model_dump()).to_dto()
        )
    )


@router.patch(
    "/{profile_id}",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def patch_profile(
    profile_id: UUID,
    profile: ProfilePatchData,
    user: SuperUserJWTDep,
    uow: ProfileUOWDep,
) -> ProfileRead:
    return ProfileRead.from_dto(
        await ProfileService(uow).patch(
            ProfilePatch(id=profile_id, **profile.model_dump()).to_dto()
        )
    )


@router.delete(
    "/{profile_id}",
    responses={**auth_responses(), **entity_not_found_responses("profile")},
)
async def delete_profile(
    profile_id: UUID, user: SuperUserJWTDep, uow: ProfileUOWDep
) -> None:
    await ProfileService(uow).delete(profile_id)
