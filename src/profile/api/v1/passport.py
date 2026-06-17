from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import ErrorCode, auth_responses, detail_400, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from profile.dependency.profile import ProfilePassportUOWDep
from profile.exc.user import NonPersonalUserException
from profile.dependency.passport import PassportUOWDep
from profile.filter.passport import PassportFilter
from profile.schema.passport import (
    PassportCreate,
    PassportItemCreate,
    PassportItemRead,
    PassportPatch,
    PassportPatchData,
    PassportPut,
    PassportPutData,
    PassportRead,
    NameVariantPatch,
    NameVariantPatchData,
    NameVariantPut,
    NameVariantPutData,
    NameVariantRead,
)
from profile.service.passport import PassportService, NameVariantService
from profile.service.profile import ProfileService

router = APIRouter(prefix="/passports", tags=["passport"])

logger = getLogger(__name__)


@router.post("/my", responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)})
async def get_my_passports(
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
    filter: PassportFilter = FilterDepends(PassportFilter),
    page_params=Depends(SPageParam),
) -> SPage[PassportItemRead]:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).search_by_profile(
        user.person_id, filter, page_params
    )


@router.post("/my/new", responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)})
async def create_my_passport(
    passport_data: PassportCreate, user: UserJWTDep, uow: ProfilePassportUOWDep
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).create(passport_data)


@router.put("/my/{passport_id}", responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)})
async def put_my_passport(
    passport_id: UUID,
    passport_data: PassportItemCreate,
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := ProfileService(uow)).ensure_existance(user.person_id)
    return await service.put(
        PassportPut(
            id=passport_id,
            profile_id=user.person_id,
            **passport_data.model_dump(),
        )
    )


@router.patch("/my/{passport_id}", responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)})
async def patch_my_passport(
    passport_id: UUID,
    passport_data: PassportPatchData,
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    await (service := PassportService(uow)).check_ownership(
        passport_id, user.person_id
    )
    return await service.patch(
        PassportPatch(person_id=user.person_id, **passport_data.model_dump())
    )


@router.delete("/my/{passport_id}", responses={**auth_responses(), **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED)})
async def delete_my_passport(
    passport_id: UUID,
    passport_data: PassportPatchData,
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    await (service := PassportService(uow)).check_ownership(
        passport_id, user.person_id
    )
    return await service.patch(
        PassportPatch(person_id=user.person_id, **passport_data.model_dump())
    )


@router.get("", responses={**auth_responses()})
async def get_passports(
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
    filter: PassportFilter = FilterDepends(PassportFilter),
    page_params=Depends(SPageParam),
) -> SPage[PassportItemRead]:
    return await PassportService(uow).search(filter, page_params)


@router.post("/{passport_id}", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def get_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> PassportRead:
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).read(passport_id)


@router.put("/{passport_id}", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def put_passport(
    passport_id: UUID,
    passport: PassportPutData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return await PassportService(uow).put(
        PassportPut(id=passport_id, **passport.model_dump())
    )


@router.patch("/{passport_id}", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def patch_passport(
    passport_id: UUID,
    passport: PassportPatchData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return await PassportService(uow).patch(
        PassportPatch(id=passport_id, **passport.model_dump())
    )


@router.delete("/{passport_id}", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def delete_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).delete(passport_id)


@router.post("/{passport_id}/name-variant", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def get_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> NameVariantRead | None:
    await PassportService(uow).ensure_existance(passport_id)
    return await NameVariantService(uow).read(passport_id)


@router.put("/{passport_id}/name-variant", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def put_name_variant(
    passport_id: UUID,
    name_variant_data: NameVariantPutData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> NameVariantRead:
    await PassportService(uow).ensure_existance(passport_id)
    return await NameVariantService(uow).put(
        NameVariantPut(id=passport_id, **name_variant_data.model_dump())
    )


@router.patch("/{passport_id}/name-variant", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def patch_name_variant(
    passport_id: UUID,
    name_variant_data: NameVariantPatchData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> NameVariantRead:
    await PassportService(uow).ensure_existance(passport_id)
    return await NameVariantService(uow).patch(
        NameVariantPatch(id=passport_id, **name_variant_data.model_dump())
    )


@router.delete("/{passport_id}/name-variant", responses={**auth_responses(), **entity_not_found_responses("passport")})
async def delete_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).ensure_existance(passport_id)
    await NameVariantService(uow).delete(passport_id)
