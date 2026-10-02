from logging import getLogger

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from geo.dependency.city import CityUOWDep
from geo.filter.city import CityFilter
from geo.schema.city import CityRead
from geo.service.city import CityService

router = APIRouter(prefix="/cities", tags=["city"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_cities(
    uow: CityUOWDep,
    user: UserJWTDep,
    filter: CityFilter = FilterDepends(CityFilter),
    page_param=Depends(PageParamV1),
) -> PageV1[CityRead]:
    """List/search-only -- cities are seeded (bootstrap or hand-entered
    alongside an address's city), not admin-CRUD-managed in their own
    right. This exists so a city picker never has to fall back to typing
    a raw id."""
    return await CityService(uow).search(filter, page_param)


@router.get(
    "/{city_id}",
    responses={**auth_responses(), **entity_not_found_responses("city")},
)
async def get_city(
    city_id: int, user: UserJWTDep, uow: CityUOWDep
) -> CityRead:
    return await CityService(uow).read(city_id)
