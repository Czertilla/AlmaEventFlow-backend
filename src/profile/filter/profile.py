from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.profile import ProfileORM


class ProfileFilter(Filter):
    order_by: list[str] | None = ["created_at"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = ProfileORM
        search_model_fields = ["birthdate"]
