from fastapi_filter.contrib.sqlalchemy import Filter
from org.models.university import UniversityORM


class UniversityFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: str | None = None

    class Constants(Filter.Constants):
        model = UniversityORM
        search_model_fields = ["name", "acronym"]
