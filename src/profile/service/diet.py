from logging import getLogger

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from profile.exc.diet import DietNotExistsException
from profile.filter.diet import DietFilter
from profile.models.diet import DietORM
from profile.schema.diet import (
    DietCreate,
    DietPatch,
    DietPut,
    DietRead,
)
from profile.uow.diet import DietUOW


logger = getLogger(__name__)


class DietService(BaseService[DietUOW]):
    @required_transaction
    async def _create(self, diet_create: DietCreate) -> DietORM:
        return await self.uow.diets.add_n_return(data=diet_create.model_dump())

    @required_transaction
    async def _read(self, diet_id: int) -> DietORM | None:
        diet = await self.uow.diets.get_by_id(diet_id)
        if diet is None:
            raise DietNotExistsException()
        return diet

    @required_transaction
    async def _update(
        self, diet_id: int, diet_data: dict, *, flush: bool = False
    ) -> DietORM:
        diet = await self.uow.diets.update_one(diet_id, diet_data, flush)
        if diet is None:
            raise DietNotExistsException()
        return diet

    async def search(
        self, filter: DietFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[DietRead]:
        async with self.uow as uow:
            diets, total = await uow.diets.search(filter, page_params)
            return SPage(
                items=[DietRead.model_validate(diet) for diet in diets],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def create(self, diet_create: DietCreate) -> DietRead:
        async with self.uow as uow:
            result = DietRead.model_validate(await self._create(diet_create))
            await uow.commit()
        return result

    async def read(self, diet_id: int) -> DietRead:
        async with self.uow:
            return DietRead.model_validate(await self._read(diet_id))

    async def patch(self, diet_patch: DietPatch) -> DietRead:
        async with self.uow as uow:
            diet_data = diet_patch.model_dump()
            result = DietRead.model_validate(
                await self._update(diet_data.pop("id"), diet_data)
            )
            await uow.commit()
        return result

    async def put(self, diet_put: DietPut) -> DietRead:
        async with self.uow as uow:
            result = DietRead.model_validate(
                await uow.diets.upsert(diet_put.model_dump())
            )
            await uow.commit()
        return result

    async def delete(self, diet_id: int) -> None:
        async with self.uow as uow:
            await self.uow.diets.delete_one(diet_id)
            await uow.commit()
