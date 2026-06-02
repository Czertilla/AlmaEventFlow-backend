from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.link import EventLinkORM


class LinkFilter(Filter):
    order_by: list[str] | None = ["type", "name"]
    search: None | str = None
    class Constants(Filter.Constants):
        model = EventLinkORM
        search_model_fields = ["name", "value"]
