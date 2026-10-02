from logging import getLogger
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.stage import (
    StageCreateDTO,
    StageDTO,
    StageFilterDTO,
    StagePatchDTO,
    StagePutDTO,
)
from event.exc.event import StageNotExistsException
from event.filter.stage import StageFilter
from event.models.stage import EventStageORM
from event.uow.stage import StageUOW

logger = getLogger(__name__)


class StageService(BaseService[StageUOW]):
    @staticmethod
    def _to_dto(stage: EventStageORM) -> StageDTO:
        return dto_from_orm(stage, StageDTO)

    @required_transaction
    async def _create(self, stage_create: StageCreateDTO) -> EventStageORM:
        stage_data = dto_dict(stage_create)
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

    async def create(self, stage_create: StageCreateDTO) -> StageDTO:
        async with self.uow as uow:
            stage = await self._create(stage_create)
            result = self._to_dto(stage)
            await uow.commit()
        return result

    async def read(self, stage_id: UUID) -> StageDTO:
        async with self.uow:
            stage = await self._read(stage_id)
            if stage is None:
                raise StageNotExistsException()
            return self._to_dto(stage)

    async def patch(self, stage_patch: StagePatchDTO) -> StageDTO:
        async with self.uow as uow:
            stage_data = dto_dict(stage_patch, only_set=True)
            stage = await self._update(stage_patch.id, stage_data)
            result = self._to_dto(stage)
            await uow.commit()
        return result

    async def put(self, stage_put: StagePutDTO) -> StageDTO:
        async with self.uow as uow:
            stage_data = dto_dict(stage_put, exclude={"id"})
            stage = await self._update(stage_put.id, stage_data)
            result = self._to_dto(stage)
            await uow.commit()
        return result

    async def delete(self, stage_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(stage_id)
            await uow.commit()

    async def search(
        self, filter: StageFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[StageDTO]:
        async with self.uow as uow:
            orm_filter = StageFilter.from_dto(filter)
            items, total = await uow.stages.search(orm_filter, page_params)
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
