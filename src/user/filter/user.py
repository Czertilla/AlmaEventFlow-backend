from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from user.dto.user import UserFilterDTO
from user.models.user import UserORM


class UserFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = UserFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None
    is_active: bool | None = None
    is_verified: bool | None = None
    is_superuser: bool | None = None
    person_id: UUID | None = None
    person_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = UserORM
        search_model_fields = ["username", "email"]
        order_fields = (
            "username",
            "email",
            "is_active",
            "is_verified",
            "is_superuser",
            "created_at",
            "edited_at",
        )
