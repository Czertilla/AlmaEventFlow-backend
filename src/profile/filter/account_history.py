from datetime import datetime
from profile.dto.account_history import AccountLinkChangeFilterDTO
from profile.enum.account import PersonLinkAction
from profile.models.account import PersonAccountHistoryORM
from typing import Any
from uuid import UUID

from sqlalchemy import or_

from core.enum.profile import PersonLinkSource
from core.filter.ordered import OrderedFilter
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class AccountLinkChangeFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = AccountLinkChangeFilterDTO

    order_by: list[str] | None = ["-created_at"]
    search: str | None = None
    user_id: UUID | None = None
    person_id: UUID | None = None
    actor_id: UUID | None = None
    action: PersonLinkAction | None = None
    source: PersonLinkSource | None = None
    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None

    class Constants(OrderedFilter.Constants):
        model = PersonAccountHistoryORM
        order_fields = ("created_at", "action", "source")

    def filter(self, query: Any) -> Any:
        person_id = self.person_id
        if person_id is not None:
            query = query.where(
                or_(
                    PersonAccountHistoryORM.old_person_id == person_id,
                    PersonAccountHistoryORM.new_person_id == person_id,
                )
            )
        self.person_id = None
        try:
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            self.person_id = person_id
