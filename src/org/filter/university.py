from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.university import UniversityFilterDTO
from org.models.university import UniversityORM


class UniversityFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = UniversityFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = UniversityORM
        search_model_fields = ["name", "acronym"]
