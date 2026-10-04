from logging import getLogger
from profile.dto.diet import (
    DietCreateDTO,
    DietDTO,
    DietFilterDTO,
    DietPatchDTO,
    DietPutDTO,
)
from profile.exc.diet import DietNotExistsException
from profile.filter.diet import DietFilter
from profile.models.diet import DietORM
from profile.uow.diet import DietUOW
from typing import Any

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


class DietService(BaseService[DietUOW]):
    @staticmethod
    def _to_dto(diet: DietORM) -> DietDTO:
        return dto_from_orm(diet, DietDTO)

    @required_transaction
    async def _create(self, diet_create: DietCreateDTO) -> DietORM:
        return await self.uow.diets.add_n_return(data=dto_dict(diet_create))

    @required_transaction
    async def _read(self, diet_id: int) -> DietORM:
        diet = await self.uow.diets.get_by_id(diet_id)
        if diet is None:
            raise DietNotExistsException()
        return diet

    @required_transaction
    async def _update(
        self,
        diet_id: int,
        diet_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> DietORM:
        diet = await self.uow.diets.update_one(diet_id, diet_data, flush)
        if diet is None:
            raise DietNotExistsException()
        return diet

    @required_transaction
    async def _upsert(self, diet_put: DietPutDTO) -> DietORM:
        diet = await self.uow.diets.upsert(dto_dict(diet_put))
        if diet is None:
            raise DietNotExistsException()
        return diet

    @required_transaction
    async def _delete(self, diet_id: int) -> None:
        await self.uow.diets.delete_one(diet_id)

    async def search(
        self,
        filter: DietFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[DietDTO]:
        async with self.uow as uow:
            diets, total = await uow.diets.search(
                DietFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(diet) for diet in diets],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def create(self, diet_create: DietCreateDTO) -> DietDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(diet_create))
            await uow.commit()
        return result

    async def read(self, diet_id: int) -> DietDTO:
        async with self.uow:
            return self._to_dto(await self._read(diet_id))

    async def patch(self, diet_patch: DietPatchDTO) -> DietDTO:
        async with self.uow as uow:
            diet_data = dto_dict(diet_patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(diet_patch.id, diet_data))
            await uow.commit()
        return result

    async def put(self, diet_put: DietPutDTO) -> DietDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(diet_put))
            await uow.commit()
        return result

    async def delete(self, diet_id: int) -> None:
        async with self.uow as uow:
            await self._delete(diet_id)
            await uow.commit()
