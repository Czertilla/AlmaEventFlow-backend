from datetime import date
from profile.dto.profile import ProfileFilterDTO
from profile.models.person import PersonORM
from profile.models.profile import ProfileORM
from uuid import UUID

from core.filter.related_search import RelatedSearchFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class ProfileFilter(
    RelatedSearchFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = ProfileFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None
    birthdate__gte: date | None = None
    birthdate__lte: date | None = None
    birthdate__isnull: bool | None = None
    workplace_id: UUID | None = None
    workplace_id__isnull: bool | None = None
    diet_id: int | None = None
    diet_id__in: list[int] | None = None
    diet_id__isnull: bool | None = None

    class Constants(RelatedSearchFilter.Constants):
        model = ProfileORM
        search_relation = ProfileORM.person
        search_related = (PersonORM.surname, PersonORM.name, PersonORM.patronymic)
        order_fields = ("birthdate", "created_at", "edited_at")
