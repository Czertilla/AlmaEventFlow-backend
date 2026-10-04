from profile.dto.person import PersonFilterDTO
from profile.models.person import PersonORM

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class PersonFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PersonFilterDTO

    order_by: list[str] | None = ["surname", "name", "patronymic"]
    search: None | str = None

    class Constants(OrderedFilter.Constants):
        model = PersonORM
        search_model_fields = ["surname", "name", "patronymic"]
        order_fields = (
            "surname",
            "name",
            "patronymic",
            "created_at",
            "edited_at",
        )
