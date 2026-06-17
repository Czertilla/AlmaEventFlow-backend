from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from profile.models.passport import PassportORM


class PassportFilter(Filter):
    order_by: list[str] | None = ["expire_date"]
    search: None | str = None
    profile_id: UUID | None = None

    class Constants(Filter.Constants):
        model = PassportORM
        search_model_fields = ["number", "issued_authority"]
