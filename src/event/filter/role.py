from uuid import UUID
from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.role import RoleORM


class RoleFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    collective_id: UUID | None = None

    class Constants(Filter.Constants):
        model = RoleORM
        search_model_fields = ["name"]
