from fastapi_filter.contrib.sqlalchemy import Filter
from org.models.collective import CollectiveORM


class CollectiveFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = CollectiveORM
        search_model_fields = ["name", "acronym"]
