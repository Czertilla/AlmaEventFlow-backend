from fastapi_filter.contrib.sqlalchemy import Filter
from org.models.faculty import FacultyORM


class FacultyFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = FacultyORM
        search_model_fields = ["name", "acronym"]
