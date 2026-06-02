from logging import getLogger
from uuid import UUID

from sqlalchemy import select

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from event.filter.participation import ParticipationFilter
from event.models.member import MemberORM
from event.models.participation import ParticipationORM
from event.schema.attendance import AttendanceCreate
from event.schema.me import MeParticipationCreate
from event.schema.participation import (
    ParticipationCreate,
    ParticipationPatch,
    ParticipationRead,
)
from event.service.attendance import AttendanceService
from event.uow.participation import ParticipationUOW

logger = getLogger(__name__)


class ParticipationService(BaseService[ParticipationUOW]):
    @required_transaction
    async def _create(
        self, participation_create: ParticipationCreate
    ) -> ParticipationORM:
        participation_data = participation_create.model_dump()
        participation = await self.uow.participations.add_n_return(
            data=participation_data
        )
        await self.uow.session.flush(objects=[participation])
        return participation

    @required_transaction
    async def _read(self, participation_id: UUID) -> ParticipationORM | None:
        participation = await self.uow.participations.get_by_id(
            participation_id
        )
        return participation

    @required_transaction
    async def _update(
        self,
        participation_id: UUID,
        participation_data: dict,
        *,
        flush: bool = False,
    ) -> ParticipationORM:
        participation = await self.uow.participations.update_one(
            participation_id, participation_data, flush
        )
        return participation

    @required_transaction
    async def _delete(self, participation_id: UUID) -> None:
        await self.uow.participations.delete_one(participation_id)

    async def create(
        self, participation_create: ParticipationCreate
    ) -> ParticipationRead:
        async with self.uow as uow:
            participation = await self._create(participation_create)
            result = ParticipationRead.model_validate(participation)
            await uow.commit()
        return result

    async def read(self, participation_id: UUID) -> ParticipationRead:
        async with self.uow:
            participation = await self._read(participation_id)
            return ParticipationRead.model_validate(participation)

    async def patch(
        self, participation_patch: ParticipationPatch
    ) -> ParticipationRead:
        async with self.uow as uow:
            participation_data = participation_patch.model_dump(
                exclude_unset=True
            )
            participation = await self._update(
                participation_patch.id,
                participation_data,
            )
            result = ParticipationRead.model_validate(participation)
            await uow.commit()
        return result

    async def delete(self, participation_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(participation_id)
            await uow.commit()

    async def create_with_attendance(
        self, collective_id: UUID, participation_data: MeParticipationCreate
    ) -> ParticipationRead:
        async with self.uow as uow:
            participation_orm = await self._create(
                ParticipationCreate(
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
                        AttendanceCreate(
                            member_id=member_id,
                            participation_id=participation_orm.id,
                        )
                    )

            await uow.commit()
            return ParticipationRead.model_validate(participation_orm)

    async def search(
        self,
        filter: ParticipationFilter,
        page_params: SPageParam = SPageParam(),
    ) -> SPage[ParticipationRead]:
        async with self.uow as uow:
            items, total = await uow.participations.search(filter, page_params)
            return SPage(
                items=[
                    ParticipationRead.model_validate(item) for item in items
                ],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
