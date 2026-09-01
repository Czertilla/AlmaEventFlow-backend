from logging import getLogger

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction
from geo.exc.city import CityNotExistsException
from geo.filter.city import CityFilter
from geo.models.city import CityORM
from geo.schema.city import CityRead
from geo.uow.city import CityUOW

logger = getLogger(__name__)


class CityService(BaseService[CityUOW]):
    @required_transaction
    async def _read(self, city_id: int) -> CityORM | None:
        city = await self.uow.cities.get_by_id(city_id)
        if city is None:
            raise CityNotExistsException()
        return city

    async def read(self, city_id: int) -> CityRead:
        async with self.uow:
            return CityRead.model_validate(await self._read(city_id))

    async def search(
        self, filter: CityFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[CityRead]:
        async with self.uow as uow:
            items, total = await uow.cities.search(filter, page_params)
            return SPage(
                items=[CityRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
