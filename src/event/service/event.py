from logging import getLogger
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.service.base import BaseService, required_transaction
from core.schema.pagination import SPage, SPageParam, SPagination
from core.schema.user import UserJWT
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.filter.event import EventFilter
from event.models.event import (
    EventORM,
    EventLevelORM,
    EventStatusORM,
    EventTypeORM,
)
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
from event.schema.stage import (
    StageCreate,
    StageCreateData,
    StagePatch,
    StageRead,
)
from event.service.attendance import AttendanceService
from event.service.participation import ParticipationService
from event.service.stage import StageService
from event.uow.event import EventUOW
from core.schema.error import ErrorCode
from core.utils.exc.http import VancedHTTPException
from event.exc.event import (
    CollectiveNotExistsException,
    EventNotExistsException,
    StageNotExistsException,
)
from event.models.participation import ParticipationORM
from event.enum.calendar import CalendarChangeTypeEnum
from event.models.calendar import CalendarChangeLogORM

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
            status=EventStatusEnumV1(event.status)
            if event.status
            else EventStatusEnumV1.draft,
            level=EventLevelEnumV1(event.level) if event.level else None,
            type=EventTypeEnumV1(event.type) if event.type else None,
            format=EventFormatEnumV1(event.format)
            if event.format
            else EventFormatEnumV1.offline,
            created_at=event.created_at,
            edited_at=event.edited_at,
        )

    @staticmethod
    def _ensure_active_has_date(status, date) -> None:
        """Бизнес-правило: мероприятие не может быть active без даты."""
        status_value = (
            status.value
            if isinstance(status, EventStatusEnumV1)
            else status
        )
        if status_value == EventStatusEnumV1.active.value and date is None:
            raise VancedHTTPException(
                status_code=422,
                detail=ErrorCode.EVENT_ACTIVE_REQUIRES_DATE,
            )

    async def _resolve_status_id(self, status: EventStatusEnumV1) -> int:
        stmt = select(EventStatusORM.id).where(
            EventStatusORM.name == status.value
        )
        result = await self.uow.session.execute(stmt)
        return result.scalar_one()

    async def _resolve_level_id(self, level: EventLevelEnumV1) -> int:
        stmt = select(EventLevelORM.id).where(EventLevelORM.name == level.value)
        result = await self.uow.session.execute(stmt)
        return result.scalar_one()

    async def _resolve_type_id(self, type: EventTypeEnumV1) -> int:
        stmt = select(EventTypeORM.id).where(EventTypeORM.name == type.value)
        result = await self.uow.session.execute(stmt)
        return result.scalar_one()

    @required_transaction
    async def _create(self, event_create: EventCreate) -> EventORM:
        self._ensure_active_has_date(event_create.status, event_create.date)
        event_data = event_create.model_dump(
            exclude={"status", "level", "type"}
        )
        event_data["status_id"] = await self._resolve_status_id(
            event_create.status
        )
        if event_create.level:
            event_data["level_id"] = await self._resolve_level_id(
                event_create.level
            )
        if event_create.type:
            event_data["type_id"] = await self._resolve_type_id(
                event_create.type
            )
        event = await self.uow.events.add_n_return(data=event_data)
        await self.uow.session.flush(objects=[event])
        event = await self.uow.events.get_by_id(
            event.id,
            options=(
                selectinload(EventORM.status_rel),
                selectinload(EventORM.level_rel),
                selectinload(EventORM.type_rel),
            ),
        )
        return event

    @required_transaction
    async def _read(self, event_id: UUID) -> EventORM | None:
        event = await self.uow.events.get_by_id(
            event_id,
            options=(
                selectinload(EventORM.status_rel),
                selectinload(EventORM.level_rel),
                selectinload(EventORM.type_rel),
            ),
        )
        return event

    @required_transaction
    async def _update(
        self, event_id: UUID, event_data: dict, *, flush: bool = False
    ) -> EventORM:
        event = await self.uow.events.update_one(event_id, event_data, flush)
        if event:
            event = await self.uow.events.get_by_id(
                event.id,
                options=(
                    selectinload(EventORM.status_rel),
                    selectinload(EventORM.level_rel),
                    selectinload(EventORM.type_rel),
                ),
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

    async def _validate_patch_active_date(self, event_patch: EventPatch) -> None:
        """Сверяем итоговое состояние (текущее + патч) с правилом active+date."""
        current = await self._read(event_patch.id)
        if current is None:
            raise EventNotExistsException()
        fields = event_patch.model_fields_set
        final_status = (
            event_patch.status if "status" in fields else current.status
        )
        final_date = event_patch.date if "date" in fields else current.date
        self._ensure_active_has_date(final_status, final_date)

    async def patch(self, event_patch: EventPatch) -> EventRead:
        async with self.uow as uow:
            await self._validate_patch_active_date(event_patch)
            # PatchModel.model_dump already forces exclude_unset=True
            event_data = event_patch.model_dump(
                exclude={"status", "level", "type"}
            )
            if "status" in event_patch.model_fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            if "level" in event_patch.model_fields_set:
                if event_patch.level is not None:
                    event_data["level_id"] = await self._resolve_level_id(
                        event_patch.level
                    )
                else:
                    event_data["level_id"] = None
            if "type" in event_patch.model_fields_set:
                if event_patch.type is not None:
                    event_data["type_id"] = await self._resolve_type_id(
                        event_patch.type
                    )
                else:
                    event_data["type_id"] = None
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def put(self, event_put: EventPut) -> EventRead:
        async with self.uow as uow:
            self._ensure_active_has_date(event_put.status, event_put.date)
            event_data = event_put.model_dump(
                exclude={"id", "status", "level", "type"}
            )
            event_data["status_id"] = await self._resolve_status_id(
                event_put.status
            )
            if event_put.level:
                event_data["level_id"] = await self._resolve_level_id(
                    event_put.level
                )
            else:
                event_data["level_id"] = None
            if event_put.type:
                event_data["type_id"] = await self._resolve_type_id(
                    event_put.type
                )
            else:
                event_data["type_id"] = None
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
                        status_code=403,
                        detail=ErrorCode.NOT_COLLECTIVE_PRINCIPAL,
                    )
                if not collective.is_verified:
                    raise VancedHTTPException(
                        status_code=403,
                        detail=ErrorCode.COLLECTIVE_NOT_VERIFIED,
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

            return MeEventRead(
                **self._orm_to_read(event_orm).model_dump(),
                participation_id=participation_orm.id,
            )

    async def _require_collective_participation(
        self, collective_id: UUID, event_id: UUID
    ) -> ParticipationORM:
        """Руководитель действует от лица коллектива только если тот участвует."""
        stmt = select(ParticipationORM).where(
            ParticipationORM.collective_id == collective_id,
            ParticipationORM.event_id == event_id,
        )
        participation = (
            await self.uow.session.execute(stmt)
        ).scalar_one_or_none()
        if not participation:
            raise VancedHTTPException(
                status_code=403,
                detail=ErrorCode.COLLECTIVE_NOT_PARTICIPATING,
            )
        return participation

    async def put_for_collective(
        self, collective_id: UUID, event_put: EventPut
    ) -> EventRead:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_put.id
            )
            self._ensure_active_has_date(event_put.status, event_put.date)

            event_data = event_put.model_dump(
                exclude={"id", "status", "level", "type"}
            )
            event_data["status_id"] = await self._resolve_status_id(
                event_put.status
            )
            if event_put.level:
                event_data["level_id"] = await self._resolve_level_id(
                    event_put.level
                )
            else:
                event_data["level_id"] = None
            if event_put.type:
                event_data["type_id"] = await self._resolve_type_id(
                    event_put.type
                )
            else:
                event_data["type_id"] = None
            event = await self._update(event_put.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def patch_for_collective(
        self, collective_id: UUID, event_patch: EventPatch
    ) -> EventRead:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_patch.id
            )
            await self._validate_patch_active_date(event_patch)

            # PatchModel.model_dump already forces exclude_unset=True
            event_data = event_patch.model_dump(
                exclude={"status", "level", "type"}
            )
            if "status" in event_patch.model_fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            if "level" in event_patch.model_fields_set:
                if event_patch.level is not None:
                    event_data["level_id"] = await self._resolve_level_id(
                        event_patch.level
                    )
                else:
                    event_data["level_id"] = None
            if "type" in event_patch.model_fields_set:
                if event_patch.type is not None:
                    event_data["type_id"] = await self._resolve_type_id(
                        event_patch.type
                    )
                else:
                    event_data["type_id"] = None
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_read(event)
            await uow.commit()
        return result

    async def delete_for_collective(
        self, collective_id: UUID, event_id: UUID
    ) -> None:
        async with self.uow as uow:
            participation = await self._require_collective_participation(
                collective_id, event_id
            )
            event = await self.uow.events.get_by_id(event_id)
            if event is not None:
                logger.debug(
                    "Recording calendar removal log for event %s "
                    "(collective %s)",
                    event_id,
                    collective_id,
                )
                self.uow.session.add(
                    CalendarChangeLogORM(
                        change_type=CalendarChangeTypeEnum.removed.value,
                        event_id=event_id,
                        collective_id=collective_id,
                        participation_id=participation.id,
                        event_name=event.name,
                        event_date=event.date,
                    )
                )
            await self._delete(event_id)
            await uow.commit()

    # --- Этапы мероприятия от лица руководителя коллектива-участника ---

    async def create_stage_for_collective(
        self, collective_id: UUID, event_id: UUID, stage_data: StageCreateData
    ) -> StageRead:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_id
            )
            stage = await StageService(self.uow)._create(
                StageCreate(event_id=event_id, **stage_data.model_dump())
            )
            result = StageRead.model_validate(stage)
            await uow.commit()
        return result

    async def patch_stage_for_collective(
        self, collective_id: UUID, stage_patch: StagePatch
    ) -> StageRead:
        async with self.uow as uow:
            stage = await uow.stages.get_by_id(stage_patch.id)
            if stage is None:
                raise StageNotExistsException()
            await self._require_collective_participation(
                collective_id, stage.event_id
            )
            stage_data = stage_patch.model_dump(exclude={"id"})
            stage = await StageService(self.uow)._update(
                stage_patch.id, stage_data
            )
            result = StageRead.model_validate(stage)
            await uow.commit()
        return result

    async def delete_stage_for_collective(
        self, collective_id: UUID, stage_id: UUID
    ) -> None:
        async with self.uow as uow:
            stage = await uow.stages.get_by_id(stage_id)
            if stage is None:
                raise StageNotExistsException()
            await self._require_collective_participation(
                collective_id, stage.event_id
            )
            await StageService(self.uow)._delete(stage_id)
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
