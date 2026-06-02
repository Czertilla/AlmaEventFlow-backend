from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.diet import DietORM


class DietFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = DietORM
        search_model_fields = ["name", "description"]
