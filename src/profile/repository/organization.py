from collections.abc import Collection
from profile.models.organization import OrganizationORM as Model
from uuid import UUID

from sqlalchemy import select

from core.repository.organization import OrganizationBaseRepo


class OrganizationRepo(
    OrganizationBaseRepo[Model]
):
    model = Model

    async def principals(
        self, types: Collection[str], among: Collection[UUID] | None
    ) -> set[UUID]:
        stmt = select(Model.principal_id).where(
            Model.type.in_(list(types)), Model.principal_id.is_not(None)
        )
        if among is not None:
            stmt = stmt.where(Model.principal_id.in_(list(among)))
        return {i for i in (await self.execute(stmt)).scalars() if i is not None}
