from fastapi_filter.contrib.sqlalchemy import Filter

from user.models.user import UserORM


class UserFilter(Filter):
    order_by: list[str] | None = ["created_at"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = UserORM
        search_model_fields = ["username", "email"]
