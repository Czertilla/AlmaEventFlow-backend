from fastapi_filter.contrib.sqlalchemy import Filter
from geo.models.location import LocationORM


class LocationFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    class Constants(Filter.Constants):
        model = LocationORM
        search_model_fields = ["name"]
