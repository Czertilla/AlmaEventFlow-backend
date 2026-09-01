from fastapi_filter.contrib.sqlalchemy import Filter

from geo.models.city import CityORM


class CityFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    region_id: int | None = None

    class Constants(Filter.Constants):
        model = CityORM
        search_model_fields = ["name"]
