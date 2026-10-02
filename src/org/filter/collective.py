from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.collective import CollectiveFilterDTO
from org.models.collective import CollectiveORM


class CollectiveFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = CollectiveFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None
    university_id: UUID | None = None

    class Constants(Filter.Constants):
        model = CollectiveORM
        search_model_fields = ["name", "acronym"]
