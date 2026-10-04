import dataclasses
import datetime
from logging import getLogger
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.error import ErrorCode
from core.schema.user import UserJWT
from core.service.base import BaseService, required_transaction
from core.utils.exc.http import VancedHTTPException
from event.dto.attendance import AttendanceCreateDTO
from event.dto.event import (
    EventCreateDTO,
    EventDTO,
    EventFilterDTO,
    EventPatchDTO,
    EventPutDTO,
)
from event.dto.me import MeEventCreateDTO, MeEventDTO
from event.dto.participation import ParticipationCreateDTO
from event.dto.stage import StageCreateDataDTO, StageCreateDTO, StageDTO, StagePatchDTO
from event.enum.calendar import CalendarChangeTypeEnum
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.exc.event import (
    CollectiveNotExistsException,
    EventNotExistsException,
    EventTemplateNotExistsException,
    StageNotExistsException,
)
from event.filter.event import EventFilter
from event.models.calendar import CalendarChangeLogORM
from event.models.event import (
    EventLevelORM,
    EventORM,
    EventStatusORM,
    EventTypeORM,
)
from event.models.member import MemberORM
from event.models.participation import ParticipationORM
from event.service.attendance import AttendanceService
from event.service.notification import (
    is_trigger_status,
    notify_collective_chats,
    notify_event_targets,
)
from event.service.participation import ParticipationService
from event.service.stage import StageService
from event.uow.event import EventUOW

logger = getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class EventSnapshot:
    status: str | None
    name: str | None
    date: datetime.date | None

    @classmethod
    def of(cls, event: EventORM | None) -> "EventSnapshot | None":
        if event is None:
            return None
        return cls(status=event.status, name=event.name, date=event.date)


class EventService(BaseService[EventUOW]):
    @staticmethod
    def _orm_to_dto(event: EventORM) -> EventDTO:
        return EventDTO(
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

    async def _resolve_template(
        self, template_id: UUID, collective_id: UUID
    ) -> EventORM:
        """Scoped to the caller's own collective (via the same
        ``ParticipationORM`` join every collective-owned query uses) so a
        principal can't probe another collective's event ids through this
        endpoint -- not found, wrong collective, and "isn't a template" all
        collapse to the same 404."""
        stmt = (
            select(EventORM)
            .join(
                ParticipationORM, ParticipationORM.event_id == EventORM.id
            )
            .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
            .where(
                EventORM.id == template_id,
                ParticipationORM.collective_id == collective_id,
                EventStatusORM.name == EventStatusEnumV1.template.value,
            )
        )
        template = (
            (await self.uow.session.execute(stmt)).unique().scalar_one_or_none()
        )
        if template is None:
            raise EventTemplateNotExistsException()
        return template

    def _apply_template_defaults(
        self, event_data: MeEventCreateDTO, template: EventORM
    ) -> MeEventCreateDTO:
        """Only fills in fields the caller didn't explicitly set on this
        request -- a principal can start from a template and still
        override just the date, for instance. Never touches
        status/stages/member_ids; those are never copied from a template.
        Skips validation, same as ``_orm_to_dto`` does for the matching
        ORM attributes."""
        set_fields = event_data.fields_set
        candidates = {
            "name": template.name,
            "date": template.date,
            "description": template.description,
            "location_id": template.location_id,
            "organizer_id": template.organizer_id,
            "level": EventLevelEnumV1(template.level)
            if template.level
            else None,
            "type": EventTypeEnumV1(template.type) if template.type else None,
            "format": EventFormatEnumV1(template.format)
            if template.format
            else EventFormatEnumV1.offline,
        }
        overrides = {
            field: value
            for field, value in candidates.items()
            if field not in set_fields
        }
        return dataclasses.replace(event_data, **overrides)

    @required_transaction
    async def _create(self, event_create: EventCreateDTO) -> EventORM:
        self._ensure_active_has_date(event_create.status, event_create.date)
        event_data = dto_dict(event_create, exclude={"status", "level", "type"})
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
        if event is None:
            raise EventNotExistsException()
        self.uow.events.session.expire(
            event, ["status_rel", "level_rel", "type_rel"]
        )
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

    async def _publish_event_notice(self, event_id: UUID) -> None:
        """Publishes both the personal attendance ping and the collective
        chat announcement for the same event — two independent pipelines
        (see ``event/service/notification.py``), triggered together."""
        await notify_event_targets(self.uow, event_ids=[event_id])
        await notify_collective_chats(self.uow, event_ids=[event_id])

    async def _publish_activation(
        self, old: EventSnapshot | None, event: EventORM
    ) -> None:
        """Notifies attendees on a transition into a trigger status (the
        original 'mark your attendance' ping), and again on a later material
        edit (name/date) to an already-active event — so the Telegram bot
        (which decides edit-vs-send itself, keyed by event_id) can refresh a
        message it already sent instead of it going stale. A no-op edit, or
        one where nothing attendee-visible changed, publishes nothing."""
        old_status = old.status if old else None
        if not is_trigger_status(old_status) and is_trigger_status(
            event.status
        ):
            await self._publish_event_notice(event.id)
            return
        if (
            old is not None
            and is_trigger_status(old_status)
            and is_trigger_status(event.status)
            and (old.name != event.name or old.date != event.date)
        ):
            await self._publish_event_notice(event.id)

    async def create(self, event_create: EventCreateDTO) -> EventDTO:
        async with self.uow as uow:
            event = await self._create(event_create)
            result = self._orm_to_dto(event)
            await uow.commit()
        return result

    async def read(self, event_id: UUID) -> EventDTO:
        async with self.uow:
            event = await self._read(event_id)
            if event is None:
                raise EventNotExistsException()
            return self._orm_to_dto(event)

    async def get_templates_for_collective(
        self, collective_id: UUID
    ) -> list[EventDTO]:
        """The list a principal picks from when starting a new event
        ``from`` a template -- same collective-scoping join as everywhere
        else, filtered to ``status=template`` instead of the active/trigger
        statuses."""
        async with self.uow:
            stmt = (
                select(EventORM)
                .join(
                    ParticipationORM,
                    ParticipationORM.event_id == EventORM.id,
                )
                .join(
                    EventStatusORM, EventStatusORM.id == EventORM.status_id
                )
                .where(
                    ParticipationORM.collective_id == collective_id,
                    EventStatusORM.name == EventStatusEnumV1.template.value,
                )
            )
            events = (
                (await self.uow.session.execute(stmt)).unique().scalars()
            )
            return [self._orm_to_dto(event) for event in events]

    async def _validate_patch_active_date(
        self, event_patch: EventPatchDTO
    ) -> None:
        """Сверяем итоговое состояние (текущее + патч) с правилом active+date."""
        current = await self._read(event_patch.id)
        if current is None:
            raise EventNotExistsException()
        fields = event_patch.fields_set
        final_status = (
            event_patch.status if "status" in fields else current.status
        )
        final_date = event_patch.date if "date" in fields else current.date
        self._ensure_active_has_date(final_status, final_date)

    async def patch(self, event_patch: EventPatchDTO) -> EventDTO:
        async with self.uow as uow:
            await self._validate_patch_active_date(event_patch)
            old = EventSnapshot.of(await self._read(event_patch.id))
            event_data = dto_dict(
                event_patch, only_set=True, exclude={"status", "level", "type"}
            )
            if "status" in event_patch.fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            if "level" in event_patch.fields_set:
                if event_patch.level is not None:
                    event_data["level_id"] = await self._resolve_level_id(
                        event_patch.level
                    )
                else:
                    event_data["level_id"] = None
            if "type" in event_patch.fields_set:
                if event_patch.type is not None:
                    event_data["type_id"] = await self._resolve_type_id(
                        event_patch.type
                    )
                else:
                    event_data["type_id"] = None
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_dto(event)
            await uow.commit()
            await self._publish_activation(old, event)
        return result

    async def put(self, event_put: EventPutDTO) -> EventDTO:
        async with self.uow as uow:
            self._ensure_active_has_date(event_put.status, event_put.date)
            old = EventSnapshot.of(await self._read(event_put.id))
            event_data = dto_dict(
                event_put, exclude={"id", "status", "level", "type"}
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
            result = self._orm_to_dto(event)
            await uow.commit()
            await self._publish_activation(old, event)
        return result

    async def delete(self, event_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(event_id)
            await uow.commit()

    async def create_with_collective(
        self, event_data: MeEventCreateDTO, user: UserJWT
    ) -> MeEventDTO:
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

            if event_data.template_id is not None:
                template = await self._resolve_template(
                    event_data.template_id, event_data.collective_id
                )
                event_data = self._apply_template_defaults(
                    event_data, template
                )

            event_create_data = dto_dict(
                event_data,
                exclude={
                    "collective_id",
                    "member_ids",
                    "stages",
                    "template_id",
                },
            )
            event_orm = await self._create(EventCreateDTO(**event_create_data))

            if event_data.stages:
                stage_service = StageService(self.uow)
                for stage_data in event_data.stages:
                    await stage_service._create(
                        StageCreateDTO(
                            event_id=event_orm.id, **dto_dict(stage_data)
                        )
                    )

            participation_service = ParticipationService(self.uow)
            participation_orm = await participation_service._create(
                ParticipationCreateDTO(
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
                        AttendanceCreateDTO(
                            member_id=member_id,
                            participation_id=participation_orm.id,
                        )
                    )

            await uow.commit()
            await self._publish_event_notice(event_orm.id)

            return MeEventDTO(
                **dto_dict(
                    self._orm_to_dto(event_orm),
                    exclude={"created_at", "edited_at"},
                ),
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
        self, collective_id: UUID, event_put: EventPutDTO
    ) -> EventDTO:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_put.id
            )
            self._ensure_active_has_date(event_put.status, event_put.date)
            old = EventSnapshot.of(await self._read(event_put.id))

            event_data = dto_dict(
                event_put, exclude={"id", "status", "level", "type"}
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
            result = self._orm_to_dto(event)
            await uow.commit()
            await self._publish_activation(old, event)
        return result

    async def patch_for_collective(
        self, collective_id: UUID, event_patch: EventPatchDTO
    ) -> EventDTO:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_patch.id
            )
            await self._validate_patch_active_date(event_patch)
            old = EventSnapshot.of(await self._read(event_patch.id))

            event_data = dto_dict(
                event_patch, only_set=True, exclude={"status", "level", "type"}
            )
            if "status" in event_patch.fields_set:
                event_data["status_id"] = await self._resolve_status_id(
                    event_patch.status
                )
            if "level" in event_patch.fields_set:
                if event_patch.level is not None:
                    event_data["level_id"] = await self._resolve_level_id(
                        event_patch.level
                    )
                else:
                    event_data["level_id"] = None
            if "type" in event_patch.fields_set:
                if event_patch.type is not None:
                    event_data["type_id"] = await self._resolve_type_id(
                        event_patch.type
                    )
                else:
                    event_data["type_id"] = None
            event = await self._update(event_patch.id, event_data)
            result = self._orm_to_dto(event)
            await uow.commit()
            await self._publish_activation(old, event)
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

    async def cancel_participation_for_collective(
        self, collective_id: UUID, event_id: UUID
    ) -> None:
        """Руководитель отменяет участие своего коллектива в мероприятии.

        Удаляется только участие этого коллектива (отметки посещаемости
        каскадно удаляются по FK). Если коллектив был последним участником —
        удаляется само мероприятие и пишется лог отмены, как при
        :meth:`delete_for_collective`.
        """
        async with self.uow as uow:
            participation = await self._require_collective_participation(
                collective_id, event_id
            )
            await uow.participations.delete_one(participation.id)
            await uow.session.flush()

            remaining = (
                await uow.session.execute(
                    select(func.count())
                    .select_from(ParticipationORM)
                    .where(ParticipationORM.event_id == event_id)
                )
            ).scalar_one()

            if remaining == 0:
                event = await uow.events.get_by_id(event_id)
                if event is not None:
                    logger.debug(
                        "Last collective %s left event %s; deleting event",
                        collective_id,
                        event_id,
                    )
                    uow.session.add(
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
        self, collective_id: UUID, event_id: UUID, stage_data: StageCreateDataDTO
    ) -> StageDTO:
        async with self.uow as uow:
            await self._require_collective_participation(
                collective_id, event_id
            )
            stage = await StageService(self.uow)._create(
                StageCreateDTO(event_id=event_id, **dto_dict(stage_data))
            )
            result = dto_from_orm(stage, StageDTO)
            await uow.commit()
            await notify_collective_chats(uow, event_ids=[event_id])
        return result

    async def patch_stage_for_collective(
        self, collective_id: UUID, stage_patch: StagePatchDTO
    ) -> StageDTO:
        async with self.uow as uow:
            stage = await uow.stages.get_by_id(stage_patch.id)
            if stage is None:
                raise StageNotExistsException()
            await self._require_collective_participation(
                collective_id, stage.event_id
            )
            event_id = stage.event_id
            stage_data = dto_dict(stage_patch, only_set=True)
            stage = await StageService(self.uow)._update(
                stage_patch.id, stage_data
            )
            result = dto_from_orm(stage, StageDTO)
            await uow.commit()
            await notify_collective_chats(uow, event_ids=[event_id])
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
            event_id = stage.event_id
            await StageService(self.uow)._delete(stage_id)
            await uow.commit()
            await notify_collective_chats(uow, event_ids=[event_id])

    async def search(
        self, filter: EventFilterDTO, page_params: PageParamDTO = PageParamDTO()
    ) -> PageDTO[EventDTO]:
        async with self.uow as uow:
            orm_filter = EventFilter.from_dto(filter)
            items, total = await uow.events.search(orm_filter, page_params)
            return PageDTO(
                items=[self._orm_to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
