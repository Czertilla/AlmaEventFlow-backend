from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.role import RoleFilterDTO
from event.models.role import RoleORM


class RoleFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = RoleFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    collective_id: UUID | None = None

    class Constants(Filter.Constants):
        model = RoleORM
        search_model_fields = ["name"]
