from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from profile.dependency.diet import DietUOWDep
from profile.filter.diet import DietFilter
from profile.schema.diet import (
    DietCreate,
    DietPatch,
    DietPut,
    DietRead,
)
from profile.service.diet import DietService

router = APIRouter(prefix="/diets", tags=["diet"])

logger = getLogger(__name__)


@router.get("")
async def get_many(
    uow: DietUOWDep,
    user: UserJWTDep,
    filter: DietFilter = FilterDepends(DietFilter),
    page_param=Depends(SPageParam),
) -> SPage[DietRead]:
    return await DietService(uow).search(filter, page_param)


@router.get("/{id}")
async def get_diet(
    id: UUID, user: UserJWTDep, uow: DietUOWDep
) -> DietRead:
    return await DietService(uow).read(id)


@router.post("")
async def create_diet(
    diet: DietCreate, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return await DietService(uow).create(diet)


@router.put("/{id}")
async def put_diet(
    id: UUID, diet: DietPut, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return await DietService(uow).put(diet)


@router.patch("/{id}")
async def patch_diet(
    id: UUID, diet: DietPatch, user: SuperUserJWTDep, uow: DietUOWDep
) -> DietRead:
    return await DietService(uow).patch(diet)


@router.delete("/{id}")
async def delete_diet(
    id: UUID, user: SuperUserJWTDep, uow: DietUOWDep
) -> None:
    await DietService(uow).delete(id)
