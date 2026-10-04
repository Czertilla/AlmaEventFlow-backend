from datetime import date
from profile.dto.passport import PassportFilterDTO
from profile.models.passport import PassportORM
from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class PassportFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PassportFilterDTO

    order_by: list[str] | None = ["expire_date"]
    search: None | str = None
    profile_id: UUID | None = None
    is_foreign: bool | None = None
    expire_date__gte: date | None = None
    expire_date__lte: date | None = None
    issued_date__gte: date | None = None
    issued_date__lte: date | None = None

    class Constants(OrderedFilter.Constants):
        model = PassportORM
        search_model_fields = ["number", "issued_authority"]
        order_fields = (
            "expire_date",
            "issued_date",
            "number",
            "is_foreign",
            "created_at",
            "edited_at",
        )
