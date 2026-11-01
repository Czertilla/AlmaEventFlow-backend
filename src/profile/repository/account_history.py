from datetime import datetime
from profile.enum.account import PersonLinkAction
from profile.models.account import PersonAccountHistoryORM as Model
from uuid import UUID

from sqlalchemy import func, or_, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import SearchRepositoryMixin
from core.enum.profile import PersonLinkSource


class PersonAccountHistoryRepo(
    SQLAlchemyRepository[Model], SearchRepositoryMixin[Model]
):
    model = Model

    async def last_change_of_person(self, person_id: UUID) -> datetime | None:
        stmt = select(func.max(Model.created_at)).where(
            or_(Model.old_person_id == person_id, Model.new_person_id == person_id)
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def record(
        self,
        user_id: UUID,
        *,
        old_person_id: UUID | None,
        new_person_id: UUID | None,
        source: PersonLinkSource,
        actor_id: UUID | None,
    ) -> None:
        await self.add_one(
            {
                "user_id": user_id,
                "old_person_id": old_person_id,
                "new_person_id": new_person_id,
                "action": PersonLinkAction.of(old_person_id, new_person_id),
                "source": source,
                "actor_id": actor_id,
            }
        )
