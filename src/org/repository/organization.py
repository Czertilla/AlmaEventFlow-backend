from sqlalchemy import func, select

from core.database.sqlalchemy.mixins.repositories import SearchRepositoryMixin
from core.repository.organization import OrganizationBaseRepo
from org.models.organization import OrganizationORM as Model


class OrganizationRepo(
    OrganizationBaseRepo[Model], SearchRepositoryMixin[Model]
):
    model = Model

    async def find_workplace(self, name: str) -> Model | None:
        stmt = select(self.model).where(
            func.lower(self.model.name) == name.lower(),
            self.model.type.in_(("organization", "university")),
        )
        return (await self.execute(stmt)).scalars().first()
