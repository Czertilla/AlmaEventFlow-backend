from profile.models.profile import ProfileORM

from fastapi_filter.contrib.sqlalchemy import Filter


class ProfileFilter(Filter):
    order_by: list[str] | None = ["created_at"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = ProfileORM
        search_model_fields = ["birthdate"]
