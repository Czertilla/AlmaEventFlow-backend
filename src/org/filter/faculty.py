from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.faculty import FacultyFilterDTO
from org.models.faculty import FacultyORM


class FacultyFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = FacultyFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = FacultyORM
        search_model_fields = ["name", "acronym"]
