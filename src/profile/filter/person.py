from profile.dto.person import PersonFilterDTO
from profile.models.person import PersonORM

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class PersonFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PersonFilterDTO

    order_by: list[str] | None = ["surname", "name", "patronymic"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = PersonORM
        search_model_fields = ["surname", "name", "patronymic"]
