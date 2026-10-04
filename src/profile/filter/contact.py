from profile.dto.contact import ContactFilterDTO
from profile.models.contact import ContactORM
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class ContactFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = ContactFilterDTO

    order_by: list[str] | None = ["type", "value"]
    search: None | str = None
    person_id: UUID | None = None

    class Constants(Filter.Constants):
        model = ContactORM
        search_model_fields = ["value"]
