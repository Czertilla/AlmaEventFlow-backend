from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from user.dto.user import UserFilterDTO
from user.models.user import UserORM


class UserFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = UserFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = UserORM
        search_model_fields = ["username", "email"]
