from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.models.member import MemberORM as Model
from event.models.member import MemberRoleAssociation
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

    async def get_by_collective_with_person(self, collective_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .options(selectinload(self.model.person))
            .where(self.model.collective_id == collective_id)
        )
        return list((await self.execute(stmt)).unique().scalars().all())

    async def get_with_details(self, member_id: UUID) -> Model | None:
        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.roles), selectinload(self.model.person)
            )
            .where(self.model.id == member_id)
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def with_roles(self, member_id: UUID) -> Model | None:
        return await self.get_by_id(
            member_id, options=(selectinload(self.model.roles),)
        )

    async def _assign_roles(
        self, member_id: UUID, collective_id: UUID, role_ids: list[UUID]
    ) -> None:
        stmt = select(RoleORM).where(RoleORM.id.in_(role_ids))
        roles = (await self.execute(stmt)).unique().scalars().all()
        self.session.add_all(
            [
                MemberRoleAssociation(role_id=role.id, member_id=member_id)
                for role in roles
                if role.collective_id == collective_id
            ]
        )
        await self.session.flush()

    async def replace_roles(
        self, member_id: UUID, collective_id: UUID, role_ids: list[UUID]
    ) -> None:
        await self.execute(
            delete(MemberRoleAssociation).where(
                MemberRoleAssociation.member_id == member_id
            )
        )
        if role_ids:
            await self._assign_roles(member_id, collective_id, role_ids)
        else:
            await self.session.flush()

    async def create_member_with_roles(
        self, member_data: dict, role_ids: list[UUID]
    ) -> Model:
        member = Model(**member_data)
        self.session.add(member)
        await self.session.flush()

        if role_ids:
            await self._assign_roles(member.id, member.collective_id, role_ids)

        await self.session.refresh(member, ["roles"])
        return member
