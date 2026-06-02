from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.contact import ContactORM


class ContactFilter(Filter):
    order_by: list[str] | None = ["type", "value"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = ContactORM
        search_model_fields = ["value"]
