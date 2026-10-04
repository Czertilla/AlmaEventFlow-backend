from profile.dto.profile import ProfileFilterDTO
from profile.models.profile import ProfileORM

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class ProfileFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = ProfileFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = ProfileORM
        search_model_fields = ["birthdate"]
