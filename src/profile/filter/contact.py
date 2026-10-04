from profile.dto.contact import ContactFilterDTO
from profile.enum.contact import ContactType
from profile.models.contact import ContactORM
from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class ContactFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = ContactFilterDTO

    order_by: list[str] | None = ["type", "value"]
    search: None | str = None
    person_id: UUID | None = None
    type: ContactType | None = None
    type__in: list[ContactType] | None = None
    is_main: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = ContactORM
        search_model_fields = ["value"]
        order_fields = ("type", "value", "is_main", "created_at", "edited_at")
