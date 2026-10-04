from logging import getLogger
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.dto.base import dto_dict
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction
from event.dto.attendance import AttendanceCreateDTO
from event.dto.me import MeParticipationCreateDTO
from event.dto.participation import (
    ParticipationCreateDTO,
    ParticipationDTO,
    ParticipationFilterDTO,
    ParticipationPatchDTO,
    ParticipationPutDTO,
)
from event.exc.event import ParticipationNotExistsException
from event.filter.participation import ParticipationFilter
from event.models.member import MemberORM
from event.models.participation import ParticipationORM
from event.service.attendance import AttendanceService
from event.service.notification import notify_event_targets
from event.uow.participation import ParticipationUOW

logger = getLogger(__name__)


class ParticipationService(BaseService[ParticipationUOW]):
    @staticmethod
    def _to_dto(participation: ParticipationORM) -> ParticipationDTO:
        collective = getattr(participation, "collective", None)
        return ParticipationDTO(
            id=participation.id,
            event_id=participation.event_id,
            collective_id=participation.collective_id,
            priority_degree=participation.priority_degree,
            created_at=participation.created_at,
            edited_at=participation.edited_at,
            collective_name=collective.name if collective is not None else None,
        )

    @required_transaction
    async def _create(
        self, participation_create: ParticipationCreateDTO
    ) -> ParticipationORM:
        participation_data = dto_dict(participation_create)
        participation = await self.uow.participations.add_n_return(
            data=participation_data
        )
        await self.uow.session.flush(objects=[participation])
        return participation

    @required_transaction
    async def _read(self, participation_id: UUID) -> ParticipationORM | None:
        participation = await self.uow.participations.get_by_id(
            participation_id,
            options=(selectinload(ParticipationORM.collective),),
        )
        return participation

    @required_transaction
    async def _reload(self, participation_id: UUID) -> ParticipationORM:
        participation = await self._read(participation_id)
        if participation is None:
            raise ParticipationNotExistsException()
        return participation

    @required_transaction
    async def _update(
        self,
        participation_id: UUID,
        participation_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> ParticipationORM:
        participation = await self.uow.participations.update_one(
            participation_id, participation_data, flush
        )
        if participation is None:
            raise ParticipationNotExistsException()
        return participation

    @required_transaction
    async def _delete(self, participation_id: UUID) -> None:
        await self.uow.participations.delete_one(participation_id)

    async def create(
        self, participation_create: ParticipationCreateDTO
    ) -> ParticipationDTO:
        async with self.uow as uow:
            created = await self._create(participation_create)
            result = self._to_dto(await self._reload(created.id))
            await uow.commit()
        return result

    async def read(self, participation_id: UUID) -> ParticipationDTO:
        async with self.uow:
            participation = await self._read(participation_id)
            if participation is None:
                raise ParticipationNotExistsException()
            return self._to_dto(participation)

    async def patch(
        self, participation_patch: ParticipationPatchDTO
    ) -> ParticipationDTO:
        async with self.uow as uow:
            participation_data = dto_dict(participation_patch, only_set=True)
            await self._update(participation_patch.id, participation_data)
            result = self._to_dto(await self._reload(participation_patch.id))
            await uow.commit()
        return result

    async def put(
        self, participation_put: ParticipationPutDTO
    ) -> ParticipationDTO:
        async with self.uow as uow:
            participation_data = dto_dict(participation_put, exclude={"id"})
            await self._update(participation_put.id, participation_data)
            result = self._to_dto(await self._reload(participation_put.id))
            await uow.commit()
        return result

    async def delete(self, participation_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(participation_id)
            await uow.commit()

    async def create_with_attendance(
        self, collective_id: UUID, participation_data: MeParticipationCreateDTO
    ) -> ParticipationDTO:
        async with self.uow as uow:
            participation_orm = await self._create(
                ParticipationCreateDTO(
                    collective_id=collective_id,
                    event_id=participation_data.event_id,
                    priority_degree=participation_data.priority_degree,
                )
            )

            member_ids = participation_data.member_ids
            if member_ids is None:
                rows = (
                    (
                        await uow.session.execute(
                            select(MemberORM).where(
                                MemberORM.collective_id == collective_id,
                                MemberORM.is_active,
                            )
                        )
                    )
                    .unique()
                    .scalars()
                    .all()
                )
                member_ids = [m.id for m in rows]
            elif len(member_ids) == 0:
                member_ids = []

            if member_ids:
                attendance_service = AttendanceService(self.uow)
                for member_id in member_ids:
                    await attendance_service._create(
                        AttendanceCreateDTO(
                            member_id=member_id,
                            participation_id=participation_orm.id,
                        )
                    )

            result = self._to_dto(await self._reload(participation_orm.id))
            await uow.commit()
            await notify_event_targets(
                uow, participation_ids=[participation_orm.id]
            )
            return result

    async def search(
        self,
        filter: ParticipationFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[ParticipationDTO]:
        async with self.uow as uow:
            orm_filter = ParticipationFilter.from_dto(filter)
            items, total = await uow.participations.search(
                orm_filter, page_params
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
