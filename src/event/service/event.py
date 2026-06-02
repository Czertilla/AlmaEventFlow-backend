from logging import getLogger
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from core.schema.user import UserJWT
from event.enum.status import EventStatus
from event.filter.event import EventFilter
from event.models.event import EventORM, EventStatusORM
from event.models.member import MemberORM
from event.schema.attendance import AttendanceCreate
from event.schema.event import (
    EventCreate,
    EventPatch,
    EventPut,
    EventRead,
)
from event.schema.me import MeEventCreate, MeEventRead
from event.schema.participation import ParticipationCreate
from event.schema.stage import StageCreate
from event.service.attendance import AttendanceService
from event.service.participation import ParticipationService
from event.service.stage import StageService
from event.uow.event import EventUOW
from core.utils.exc.http import VancedHTTPException
from event.exc.event import CollectiveNotExistsException
from event.models.participation import ParticipationORM

logger = getLogger(__name__)


class EventService(BaseService[EventUOW]):
    @staticmethod
    def _orm_to_read(event: EventORM) -> EventRead:
        return EventRead(
            id=event.id,
            name=event.name,
            date=event.date,
            description=event.description,
            location_id=event.location_id,
            organizer_id=event.organizer_id,
            status=EventStatus(event.status) if event.status else EventStatus.draft,
            created_at=event.created_at,
            edited_at=event.edited_at,
        )

    async def _resolve_status_id(self, status: EventStatus) -> int:
        stmt = select(EventStatusORM.id).where(EventStatusORM.name == status.value)
        result = await self.uow.session.execute(stmt)
        return result.scalar_one()

    @required_transaction
    async def _create(self, event_create: EventCreate) -> EventORM:
        event_data = event_create.model_dump(exclude={"status"})
        event_data["status_id"] = await self._resolve_status_id(event_create.status)
        event = await self.uow.events.add_n_return(data=event_data)
        await self.uow.session.flush(objects=[event])
        event = await self.uow.events.get_by_id(
            event.id, options=(selectinload(EventORM.status_rel),)
        )
        return event

    @required_transaction
    async def _read(self, event_id: UUID) -> EventORM | None:
        event = await self.uow.events.get_by_id(
            event_id, options=(selectinload(EventORM.status_rel),)
        )
        return event

    @required_transaction
    async def _update(
        self, event_id: UUID, event_data: dict, *, flush: bool = False
    ) -> EventORM:
        event = await self.uow.events.update_one(event_id, event_data, flush)
        if event:
            event = await self.uow.events.get_by_id(
                event.id, options=(selectinload(EventORM.status_rel),)
            )
        return event

    @required_transaction
    async def _delete(self, event_id: UUID) -> None:
        await self.uow.events.delete_one(event_id)

    async def create(self, event_create: EventCreate) -> EventRead:
        async with self.uow as uow:
            event = await self._create(event_create)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def read(self, event_id: UUID) -> EventRead:
        async with self.uow:
            event = await self._read(event_id)
            return self._orm_to_read(event)

    async def patch(self, event_patch: EventPatch) -> EventRead:
        async with self.uow as uow:
            event_data = event_patch.model_dump(exclude={"status"}, exclude_unset=True)
            if "status" in event_patch.model_fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def put(self, event_put: EventPut) -> EventRead:
        async with self.uow as uow:
            event_data = event_put.model_dump(exclude={"id", "status"})
            event_data["status_id"] = await self._resolve_status_id(event_put.status)
            event = await self._update(event_put.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def delete(self, event_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(event_id)
            await uow.commit()

    async def create_with_collective(
        self, event_data: MeEventCreate, user: UserJWT
    ) -> MeEventRead:
        async with self.uow as uow:
            collective = await uow.collectives.get_by_id(
                event_data.collective_id
            )
            if not collective:
                raise CollectiveNotExistsException()
            if not user.is_superuser:
                if user.person_id != collective.principal_id:
                    raise VancedHTTPException(
                        status_code=403, detail="NOT_COLLECTIVE_PRINCIPAL"
                    )
                if not collective.is_verified:
                    raise VancedHTTPException(
                        status_code=403, detail="COLLECTIVE_NOT_VERIFIED"
                    )

            event_create_data = event_data.model_dump(
                exclude={"collective_id", "member_ids", "stages"}
            )
            event_orm = await self._create(EventCreate(**event_create_data))

            if event_data.stages:
                stage_service = StageService(self.uow)
                for stage_data in event_data.stages:
                    await stage_service._create(
                        StageCreate(
                            event_id=event_orm.id, **stage_data.model_dump()
                        )
                    )

            participation_service = ParticipationService(self.uow)
            participation_orm = await participation_service._create(
                ParticipationCreate(
                    collective_id=event_data.collective_id,
                    event_id=event_orm.id,
                )
            )

            member_ids = event_data.member_ids
            if member_ids is None:
                rows = (
                    (
                        await uow.session.execute(
                            select(MemberORM).where(
                                MemberORM.collective_id
                                == event_data.collective_id,
                                MemberORM.is_active
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

            return MeEventRead(
                **self._orm_to_read(event_orm).model_dump(),
                participation_id=participation_orm.id,
            )

    async def put_for_collective(
        self, collective_id: UUID, event_put: EventPut
    ) -> EventRead:
        async with self.uow as uow:
            stmt = select(ParticipationORM).where(
                ParticipationORM.collective_id == collective_id,
                ParticipationORM.event_id == event_put.id,
            )
            participation = (
                await uow.session.execute(stmt)
            ).scalar_one_or_none()
            if not participation:
                raise VancedHTTPException(
                    status_code=403, detail="COLLECTIVE_NOT_PARTICIPATING"
                )

            event_data = event_put.model_dump(exclude={"id", "status"})
            event_data["status_id"] = await self._resolve_status_id(event_put.status)
            event = await self._update(event_put.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def patch_for_collective(
        self, collective_id: UUID, event_patch: EventPatch
    ) -> EventRead:
        async with self.uow as uow:
            stmt = select(ParticipationORM).where(
                ParticipationORM.collective_id == collective_id,
                ParticipationORM.event_id == event_patch.id,
            )
            participation = (
                await uow.session.execute(stmt)
            ).scalar_one_or_none()
            if not participation:
                raise VancedHTTPException(
                    status_code=403, detail="COLLECTIVE_NOT_PARTICIPATING"
                )

            event_data = event_patch.model_dump(exclude={"status"}, exclude_unset=True)
            if "status" in event_patch.model_fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def delete_for_collective(
        self, collective_id: UUID, event_id: UUID
    ) -> None:
        async with self.uow as uow:
            stmt = select(ParticipationORM).where(
                ParticipationORM.collective_id == collective_id,
                ParticipationORM.event_id == event_id,
            )
            participation = (
                await uow.session.execute(stmt)
            ).scalar_one_or_none()
            if not participation:
                raise VancedHTTPException(
                    status_code=403, detail="COLLECTIVE_NOT_PARTICIPATING"
                )

            await self._delete(event_id)
            await uow.commit()

    async def search(
        self, filter: EventFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[EventRead]:
        async with self.uow as uow:
            items, total = await uow.events.search(filter, page_params)
            return SPage(
                items=[self._orm_to_read(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
