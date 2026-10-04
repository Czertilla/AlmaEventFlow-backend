from profile.dto.diet import DietFilterDTO
from profile.models.diet import DietORM

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class DietFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = DietFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = DietORM
        search_model_fields = ["name", "description"]
