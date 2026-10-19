from uuid import UUID

from core.filter.identity import IdentityFilterMixin
from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.participation import ParticipationFilterDTO
from event.enum.priority import EventPriorityEnumV1
from event.models.collective import CollectiveORM
from event.models.event import EventORM
from event.models.participation import ParticipationORM


class ParticipationFilter(
    RelatedSearchFilter,
    TimestampFilterMixin,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = ParticipationFilterDTO

    order_by: list[str] | None = ["collective_id"]
    search: str | None = None
    collective_id: None | UUID = None
    collective_id__in: None | list[UUID] = None
    event_id: None | UUID = None
    event_id__in: None | list[UUID] = None
    priority_degree: None | EventPriorityEnumV1 = None
    priority_degree__in: None | list[EventPriorityEnumV1] = None
    priority_degree__isnull: None | bool = None

    class Constants(RelatedSearchFilter.Constants):
        model = ParticipationORM
        search_paths = (
            ((ParticipationORM.collective,), (CollectiveORM.name,)),
            ((ParticipationORM.event,), (EventORM.name,)),
        )
        order_fields = ("collective_id", "priority_degree", "created_at", "edited_at")
