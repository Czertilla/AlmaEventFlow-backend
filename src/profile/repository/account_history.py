from profile.enum.account import PersonLinkAction
from profile.models.account import PersonAccountHistoryORM as Model
from uuid import UUID

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import SearchRepositoryMixin
from core.enum.profile import PersonLinkSource


class PersonAccountHistoryRepo(
    SQLAlchemyRepository[Model], SearchRepositoryMixin[Model]
):
    model = Model

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
