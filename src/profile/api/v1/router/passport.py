from logging import getLogger
from profile.api.v1.schema.passport import (
    NameVariantPatch,
    NameVariantPatchData,
    NameVariantPut,
    NameVariantPutData,
    NameVariantRead,
    PassportCreate,
    PassportItemCreate,
    PassportItemRead,
    PassportPatch,
    PassportPatchData,
    PassportPut,
    PassportPutData,
    PassportRead,
)
from profile.dependency.passport import PassportUOWDep
from profile.dependency.profile import ProfilePassportUOWDep
from profile.exc.user import NonPersonalUserException
from profile.filter.passport import PassportFilter
from profile.service.passport import NameVariantService, PassportService
from profile.service.profile import ProfileService
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_400,
    entity_not_found_responses,
    error_response,
)
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/passports", tags=["passport"])

logger = getLogger(__name__)

MY_RESPONSES: dict[int | str, dict[str, Any]] = {
    **auth_responses(),
    **detail_400(ErrorCode.ATTACHED_PERSON_REQUIRED),
}
MY_PASSPORT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **MY_RESPONSES,
    **entity_not_found_responses("passport"),
}
PASSPORT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **auth_responses(),
    **entity_not_found_responses("passport"),
}
NAME_VARIANT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **auth_responses(),
    **error_response(
        404,
        "Passport or its name variant does not exist",
        {
            ErrorCode.PASSPORT_NOT_FOUND: {},
            ErrorCode.NAME_VARIANT_NOT_FOUND: {},
        },
    ),
}


@router.get("/my", responses=MY_RESPONSES)
async def get_my_passports(
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
    filter: PassportFilter = FilterDepends(PassportFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[PassportItemRead]:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return PageV1[PassportItemRead].from_dto(
        await PassportService(uow).search_by_profile(
            user.person_id, filter.to_dto(), page_params.to_dto()
        )
    )


@router.post("/my", responses=MY_RESPONSES)
async def create_my_passport(
    passport_data: PassportItemCreate, user: UserJWTDep, uow: ProfilePassportUOWDep
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return PassportRead.from_dto(
        await PassportService(uow).create(
            PassportCreate(
                profile_id=user.person_id, **passport_data.model_dump()
            ).to_dto()
        )
    )


@router.get("/my/{passport_id}", responses=MY_PASSPORT_RESPONSES)
async def get_my_passport(
    passport_id: UUID, user: UserJWTDep, uow: ProfilePassportUOWDep
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := PassportService(uow)).check_ownership(passport_id, user.person_id)
    return PassportRead.from_dto(await service.read(passport_id))


@router.put("/my/{passport_id}", responses=MY_PASSPORT_RESPONSES)
async def put_my_passport(
    passport_id: UUID,
    passport_data: PassportItemCreate,
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await ProfileService(uow).ensure_existance(user.person_id)
    return PassportRead.from_dto(
        await PassportService(uow).put(
            PassportPut.model_validate(
                {
                    "id": passport_id,
                    "profile_id": user.person_id,
                    **passport_data.model_dump(),
                }
            ).to_dto()
        )
    )


@router.patch("/my/{passport_id}", responses=MY_PASSPORT_RESPONSES)
async def patch_my_passport(
    passport_id: UUID,
    passport_data: PassportPatchData,
    user: UserJWTDep,
    uow: ProfilePassportUOWDep,
) -> PassportRead:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := PassportService(uow)).check_ownership(passport_id, user.person_id)
    return PassportRead.from_dto(
        await service.patch(
            PassportPatch.model_validate(
                {"id": passport_id, **passport_data.model_dump()}
            ).to_dto()
        )
    )


@router.delete("/my/{passport_id}", responses=MY_PASSPORT_RESPONSES)
async def delete_my_passport(
    passport_id: UUID, user: UserJWTDep, uow: ProfilePassportUOWDep
) -> None:
    if user.person_id is None:
        raise NonPersonalUserException()
    await (service := PassportService(uow)).check_ownership(passport_id, user.person_id)
    await service.delete(passport_id)


@router.get("", responses={**auth_responses()})
async def get_passports(
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
    filter: PassportFilter = FilterDepends(PassportFilter),
    page_params: PageParamV1 = Depends(PageParamV1),
) -> PageV1[PassportItemRead]:
    return PageV1[PassportItemRead].from_dto(
        await PassportService(uow).search(filter.to_dto(), page_params.to_dto())
    )


@router.get("/{passport_id}", responses=PASSPORT_RESPONSES)
async def get_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> PassportRead:
    return PassportRead.from_dto(await PassportService(uow).read(passport_id))


@router.put("/{passport_id}", responses=PASSPORT_RESPONSES)
async def put_passport(
    passport_id: UUID,
    passport: PassportPutData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return PassportRead.from_dto(
        await PassportService(uow).put(
            PassportPut.model_validate(
                {"id": passport_id, **passport.model_dump()}
            ).to_dto()
        )
    )


@router.patch("/{passport_id}", responses=PASSPORT_RESPONSES)
async def patch_passport(
    passport_id: UUID,
    passport: PassportPatchData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> PassportRead:
    return PassportRead.from_dto(
        await PassportService(uow).patch(
            PassportPatch.model_validate(
                {"id": passport_id, **passport.model_dump()}
            ).to_dto()
        )
    )


@router.delete("/{passport_id}", responses=PASSPORT_RESPONSES)
async def delete_passport(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).delete(passport_id)


@router.get("/{passport_id}/name-variant", responses=NAME_VARIANT_RESPONSES)
async def get_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> NameVariantRead:
    await PassportService(uow).ensure_existance(passport_id)
    return NameVariantRead.from_dto(await NameVariantService(uow).read(passport_id))


@router.put("/{passport_id}/name-variant", responses=PASSPORT_RESPONSES)
async def put_name_variant(
    passport_id: UUID,
    name_variant_data: NameVariantPutData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> NameVariantRead:
    await PassportService(uow).ensure_existance(passport_id)
    return NameVariantRead.from_dto(
        await NameVariantService(uow).put(
            NameVariantPut.model_validate(
                {"id": passport_id, **name_variant_data.model_dump()}
            ).to_dto()
        )
    )


@router.patch("/{passport_id}/name-variant", responses=NAME_VARIANT_RESPONSES)
async def patch_name_variant(
    passport_id: UUID,
    name_variant_data: NameVariantPatchData,
    user: SuperUserJWTDep,
    uow: PassportUOWDep,
) -> NameVariantRead:
    await PassportService(uow).ensure_existance(passport_id)
    return NameVariantRead.from_dto(
        await NameVariantService(uow).patch(
            NameVariantPatch.model_validate(
                {"id": passport_id, **name_variant_data.model_dump()}
            ).to_dto()
        )
    )


@router.delete("/{passport_id}/name-variant", responses=PASSPORT_RESPONSES)
async def delete_name_variant(
    passport_id: UUID, user: SuperUserJWTDep, uow: PassportUOWDep
) -> None:
    await PassportService(uow).ensure_existance(passport_id)
    await NameVariantService(uow).delete(passport_id)
