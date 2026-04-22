from uuid import UUID
from fastapi import APIRouter, Depends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from profile.dependency.profile import ProfilePassportUOWDep
from profile.exc.user import NonPersonalUserException
from profile.dependency.passport import PassportUOWDep
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


@router.post("/my")
async def get_my_passports(
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
    page_params=Depends(SPageParam),
) -> SPage[PassportItemRead]:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).read_many_by_profile(
        user.person_id, page_params
    )


@router.post("/my/new")
async def create_my_passport(
    passport_data: PassportCreate, user: UserJWTDep, uow: ProfilePassportUOWDep
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).create(passport_data)


@router.put("/my/{passport_id}")
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


@router.patch("/my/{passport_id}")
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


@router.delete("/my/{passport_id}")
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


@router.post("/{passport_id}")
async def get_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> PassportRead:
    await ProfileService(uow).ensure_existance(user.person_id)
    return await PassportService(uow).read(passport_id)


@router.put("/{passport_id}")
async def put_passport(
    passport_id: UUID,
    passport: PassportPutData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return await PassportService(uow).put(
        PassportPut(id=passport_id, **passport.model_dump())
    )


@router.patch("/{passport_id}")
async def patch_passport(
    passport_id: UUID,
    passport: PassportPatchData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return await PassportService(uow).patch(
        PassportPatch(id=passport_id, **passport.model_dump())
    )


@router.delete("/{passport_id}")
async def delete_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).delete(passport_id)


@router.post("/{passport_id}/name-variant")
async def get_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> NameVariantRead | None:
    await PassportService(uow).ensure_existance(passport_id)
    return await NameVariantService(uow).read(passport_id)


@router.put("/{passport_id}/name-variant")
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


@router.patch("/{passport_id}/name-variant")
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


@router.delete("/{passport_id}/name-variant")
async def delete_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).ensure_existance(passport_id)
    await NameVariantService(uow).delete(passport_id)
