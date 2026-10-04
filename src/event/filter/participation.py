from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.participation import ParticipationFilterDTO
from event.enum.priority import EventPriorityEnumV1
from event.models.participation import ParticipationORM


class ParticipationFilter(
    OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = ParticipationFilterDTO

    order_by: list[str] | None = ["collective_id"]
    collective_id: None | UUID = None
    collective_id__in: None | list[UUID] = None
    event_id: None | UUID = None
    event_id__in: None | list[UUID] = None
    priority_degree: None | EventPriorityEnumV1 = None
    priority_degree__in: None | list[EventPriorityEnumV1] = None
    priority_degree__isnull: None | bool = None

    class Constants(OrderedFilter.Constants):
        model = ParticipationORM
        order_fields = ("collective_id", "priority_degree", "created_at", "edited_at")
