from profile.models.diet import DietORM

from fastapi_filter.contrib.sqlalchemy import Filter


class DietFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = DietORM
        search_model_fields = ["name", "description"]
