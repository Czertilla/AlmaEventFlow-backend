from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.organization import OrganizationFilterDTO
from org.models.organization import OrganizationORM


class OrganizationFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = OrganizationFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None
    type: str | None = None
    type__in: list[str] | None = None

    class Constants(Filter.Constants):
        model = OrganizationORM
        search_model_fields = ["name", "acronym"]
