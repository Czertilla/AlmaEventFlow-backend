from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from event.filter.stage import StageFilter
from event.models.stage import EventStageORM
from event.schema.stage import (
    StageCreate,
    StagePatch,
    StagePut,
    StageRead,
)
from event.uow.stage import StageUOW

logger = getLogger(__name__)


class StageService(BaseService[StageUOW]):
    @required_transaction
    async def _create(self, stage_create: StageCreate) -> EventStageORM:
        stage_data = stage_create.model_dump()
        stage = await self.uow.stages.add_n_return(data=stage_data)
        await self.uow.session.flush(objects=[stage])
        return stage

    @required_transaction
    async def _read(self, stage_id: UUID) -> EventStageORM | None:
        stage = await self.uow.stages.get_by_id(stage_id)
        return stage

    @required_transaction
    async def _update(
        self, stage_id: UUID, stage_data: dict, *, flush: bool = False
    ) -> EventStageORM:
        stage = await self.uow.stages.update_one(stage_id, stage_data, flush)
        return stage

    @required_transaction
    async def _delete(self, stage_id: UUID) -> None:
        await self.uow.stages.delete_one(stage_id)

    async def create(self, stage_create: StageCreate) -> StageRead:
        async with self.uow as uow:
            stage = await self._create(stage_create)
            result = StageRead.model_validate(stage)
            await uow.commit()
        return result

    async def read(self, stage_id: UUID) -> StageRead:
        async with self.uow:
            stage = await self._read(stage_id)
            return StageRead.model_validate(stage)

    async def patch(self, stage_patch: StagePatch) -> StageRead:
        async with self.uow as uow:
            stage_data = stage_patch.model_dump()
            stage = await self._update(stage_patch.id, stage_data)
            result = StageRead.model_validate(stage)
            await uow.commit()
        return result

    async def put(self, stage_put: StagePut) -> StageRead:
        async with self.uow as uow:
            stage_data = stage_put.model_dump()
            stage_id = stage_data.pop("id")
            stage = await self._update(stage_id, stage_data)
            result = StageRead.model_validate(stage)
            await uow.commit()
        return result

    async def delete(self, stage_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(stage_id)
            await uow.commit()

    async def search(
        self, filter: StageFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[StageRead]:
        async with self.uow as uow:
            items, total = await uow.stages.search(filter, page_params)
            return SPage(
                items=[StageRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
