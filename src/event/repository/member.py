from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
    SearchRepositoryMixin,
)

from event.models.member import MemberORM as Model, MemberRoleAssociation
from event.models.role import RoleORM


class MemberRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def search(self, filter, pagination, *, options=None):
        return await super().search(filter, pagination, options=options)

    async def get_by_person_id(self, person_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .options(selectinload(self.model.roles))
            .where(self.model.person_id == person_id)
        )
        return (await self.execute(stmt)).unique().scalars().all()

    async def create_member_with_roles(
        self, member_data: dict, role_ids: list[UUID]
    ) -> Model:
        member = Model(**member_data)
        self.session.add(member)
        await self.session.flush()

        if role_ids:
            roles: list[RoleORM] = (
                (
                    await self.execute(
                        select(RoleORM).where(RoleORM.id.in_(role_ids))
                    )
                )
                .unique()
                .scalars()
                .all()
            )
            self.session.add_all(
                [
                    MemberRoleAssociation(role_id=role.id, member_id=member.id)
                    for role in roles
                    if role.collective_id == member.collective_id
                ]
            )
            await self.session.flush()

        return await self.session.scalar(
            select(Model)
            .options(selectinload(Model.roles))
            .where(Model.id == member.id)
        )
