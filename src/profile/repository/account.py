from profile.models.account import PersonAccountORM as Model
from uuid import UUID

from sqlalchemy import delete, select

from core.database.sqlalchemy.core import SQLAlchemyRepository


class PersonAccountRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def get_by_user(self, user_id: UUID) -> Model | None:
        stmt = select(self.model).where(self.model.user_id == user_id)
        return (await self.execute(stmt)).scalar_one_or_none()

    async def get_by_person(self, person_id: UUID) -> Model | None:
        stmt = select(self.model).where(self.model.person_id == person_id)
        return (await self.execute(stmt)).scalar_one_or_none()

    async def delete_by_person(self, person_id: UUID) -> None:
        await self.execute(
            delete(self.model).where(self.model.person_id == person_id), flush=True
        )
