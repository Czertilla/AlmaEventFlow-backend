from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.link import LinkFilterDTO
from event.models.link import EventLinkORM


class LinkFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = LinkFilterDTO

    order_by: list[str] | None = ["type", "name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = EventLinkORM
        search_model_fields = ["name", "value"]
