from fastapi_filter.contrib.sqlalchemy import Filter
from org.models.organization import OrganizationORM


class OrganizationFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = OrganizationORM
        search_model_fields = ["name", "acronym"]
