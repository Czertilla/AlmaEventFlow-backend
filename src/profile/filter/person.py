from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.person import PersonORM


class PersonFilter(Filter):
    order_by: list[str] | None = ["surname", "name", "patronymic"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = PersonORM
        search_model_fields = ["surname", "name", "patronymic"]
