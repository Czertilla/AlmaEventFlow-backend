from fastapi_filter.contrib.sqlalchemy import Filter
from geo.models.address import AddressORM


class AddressFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    city_id: int | None = None
    class Constants(Filter.Constants):
        model = AddressORM
        search_model_fields = ["name"]
