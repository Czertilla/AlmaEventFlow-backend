from typing import Any
from uuid import UUID

from core.filter.identity import IdentityFilterMixin
from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.attendance import AttendanceFilterDTO
from event.models.attendance import AttendanceORM
from event.models.collective import CollectiveORM
from event.models.event import EventORM
from event.models.member import MemberORM
from event.models.participation import ParticipationORM
from event.models.person import PersonORM

DERIVED_FILTERS = (
    "collective_id",
    "collective_id__in",
    "event_id",
    "event_id__in",
    "person_id",
    "person_id__in",
)


class AttendanceFilter(
    RelatedSearchFilter,
    TimestampFilterMixin,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = AttendanceFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None
    participation_id: None | UUID = None
    participation_id__in: None | list[UUID] = None
    collective_id: None | UUID = None
    collective_id__in: None | list[UUID] = None
    event_id: None | UUID = None
    event_id__in: None | list[UUID] = None
    member_id: None | UUID = None
    member_id__in: None | list[UUID] = None
    person_id: None | UUID = None
    person_id__in: None | list[UUID] = None
    is_attended: None | bool = None
    is_verified: None | bool = None

    class Constants(RelatedSearchFilter.Constants):
        model = AttendanceORM
        search_model_fields = ["comment"]
        search_paths = (
            (
                (AttendanceORM.member, MemberORM.person),
                (PersonORM.surname, PersonORM.name, PersonORM.patronymic),
            ),
            (
                (AttendanceORM.participation, ParticipationORM.collective),
                (CollectiveORM.name,),
            ),
            ((AttendanceORM.participation, ParticipationORM.event), (EventORM.name,)),
        )
        order_fields = ("is_attended", "is_verified", "created_at", "edited_at")

    def filter(self, query: Any) -> Any:
        given = {name: getattr(self, name) for name in DERIVED_FILTERS}
        participation: list[Any] = []
        if given["collective_id"] is not None:
            participation.append(
                ParticipationORM.collective_id == given["collective_id"]
            )
        if given["collective_id__in"]:
            participation.append(
                ParticipationORM.collective_id.in_(given["collective_id__in"])
            )
        if given["event_id"] is not None:
            participation.append(ParticipationORM.event_id == given["event_id"])
        if given["event_id__in"]:
            participation.append(ParticipationORM.event_id.in_(given["event_id__in"]))
        if participation:
            query = query.where(AttendanceORM.participation.has(*participation))
        if given["person_id"] is not None:
            query = query.where(
                AttendanceORM.member.has(MemberORM.person_id == given["person_id"])
            )
        if given["person_id__in"]:
            query = query.where(
                AttendanceORM.member.has(
                    MemberORM.person_id.in_(given["person_id__in"])
                )
            )
        for name in DERIVED_FILTERS:
            setattr(self, name, None)
        try:
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            for name, value in given.items():
                setattr(self, name, value)
