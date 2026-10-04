from logging import getLogger
from profile.api.v1.schema.diet import (
    DietCreate,
    DietPatch,
    DietPatchData,
    DietPut,
    DietPutData,
    DietRead,
)
from profile.dependency.diet import DietUOWDep
from profile.filter.diet import DietFilter
from profile.service.diet import DietService

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1

router = APIRouter(prefix="/diets", tags=["diet"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_many(
    uow: DietUOWDep,
    user: UserJWTDep,
    filter: DietFilter = FilterDepends(DietFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[DietRead]:
    return PageV1[DietRead].from_dto(
        await DietService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("diet")}
)
async def get_diet(id: int, user: UserJWTDep, uow: DietUOWDep) -> DietRead:
    return DietRead.from_dto(await DietService(uow).read(id))


@router.post("", responses={**auth_responses()})
async def create_diet(
    diet: DietCreate, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return DietRead.from_dto(await DietService(uow).create(diet.to_dto()))


@router.put(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("diet")}
)
async def put_diet(
    id: int, diet: DietPutData, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return DietRead.from_dto(
        await DietService(uow).put(
            DietPut.model_validate({"id": id, **diet.model_dump()}).to_dto()
        )
    )


@router.patch(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("diet")}
)
async def patch_diet(
    id: int, diet: DietPatchData, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return DietRead.from_dto(
        await DietService(uow).patch(
            DietPatch.model_validate({"id": id, **diet.model_dump()}).to_dto()
        )
    )


@router.delete(
    "/{id}", responses={**auth_responses(), **entity_not_found_responses("diet")}
)
async def delete_diet(id: int, user: SuperUserJWTDep, uow: DietUOWDep) -> None:
    await DietService(uow).delete(id)
