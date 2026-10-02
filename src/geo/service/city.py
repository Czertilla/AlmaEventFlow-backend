from logging import getLogger

from core.dto.base import dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from geo.dto.city import CityDTO, CityFilterDTO
from geo.exc.city import CityNotExistsException
from geo.filter.city import CityFilter
from geo.models.city import CityORM
from geo.uow.city import CityUOW

logger = getLogger(__name__)


class CityService(BaseService[CityUOW]):
    @staticmethod
    def _to_dto(city: CityORM) -> CityDTO:
        return dto_from_orm(city, CityDTO)

    @required_transaction
    async def _read(self, city_id: int) -> CityORM:
        city = await self.uow.cities.get_by_id(city_id)
        if city is None:
            raise CityNotExistsException()
        return city

    async def read(self, city_id: int) -> CityDTO:
        async with self.uow:
            return self._to_dto(await self._read(city_id))

    async def search(
        self,
        filter: CityFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[CityDTO]:
        async with self.uow as uow:
            items, total = await uow.cities.search(
                CityFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
