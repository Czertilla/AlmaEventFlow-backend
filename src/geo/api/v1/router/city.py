from logging import getLogger

from fastapi import APIRouter, Depends

from core.dependencies.auth import UserJWTDep
from core.filter.depends import FilterDepends
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from geo.api.v1.schema.city import CityRead
from geo.dependency.city import CityUOWDep
from geo.filter.city import CityFilter
from geo.service.city import CityService

router = APIRouter(prefix="/cities", tags=["city"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_cities(
    uow: CityUOWDep,
    user: UserJWTDep,
    filter: CityFilter = FilterDepends(CityFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[CityRead]:
    """List/search-only -- cities are seeded (bootstrap or hand-entered
    alongside an address's city), not admin-CRUD-managed in their own
    right. This exists so a city picker never has to fall back to typing
    a raw id."""
    return PageV1[CityRead].from_dto(
        await CityService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.get(
    "/{city_id}",
    responses={**auth_responses(), **entity_not_found_responses("city")},
)
async def get_city(city_id: int, user: UserJWTDep, uow: CityUOWDep) -> CityRead:
    return CityRead.from_dto(await CityService(uow).read(city_id))
