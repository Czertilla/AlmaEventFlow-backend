from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.link import LinkFilterDTO
from event.enum.link import EventLinkTypeEnumV1
from event.models.link import EventLinkORM


class LinkFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = LinkFilterDTO

    order_by: list[str] | None = ["type", "description"]
    search: None | str = None
    event_id: UUID | None = None
    event_id__in: list[UUID] | None = None
    type: EventLinkTypeEnumV1 | None = None
    type__in: list[EventLinkTypeEnumV1] | None = None

    class Constants(OrderedFilter.Constants):
        model = EventLinkORM
        search_model_fields = ["description", "url"]
        order_fields = ("type", "description", "url", "created_at", "edited_at")
