from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload, joinedload, with_loader_criteria
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from profile.models.contact import ContactORM
from profile.models.passport import PassportORM
from profile.models.person import PersonORM
from profile.models.profile import ProfileORM as Model


class ProfileRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    with_passports = selectinload(Model.passports).load_only(PassportORM.id)
    with_diet = joinedload(Model.diet)
    with_person = selectinload(Model.person).selectinload(PersonORM.contacts)
    with_main_contacts = with_loader_criteria(ContactORM, ContactORM.is_main)

    all_options = (with_passports, with_diet, with_person, with_main_contacts)

    async def update_one(
        self,
        id: UUID,
        data: dict[str, Any],
        flush: bool = False,
        options=all_options,
    ) -> Model | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
            .options(*options)
        )
        return (await self.execute(stmt, flush)).unique().scalar_one_or_none()

    async def get_by_id(self, id, options=all_options):
        return await super().get_by_id(id, options)

    async def add_n_return(self, data, options=all_options):
        return await super().add_n_return(data, options)

    async def upsert(self, data, options=all_options):
        return await super().upsert(data, options)

    async def get_many_cron(
        self,
        offset: int,
        limit: int,
    ):
        stmt = (
            select(Model)
            .order_by(Model.edited_at)
            .order_by(Model.created_at)
            .limit(limit)
            .offset(offset)
            .options(*self.all_options)
        )
        return (
            (await self.execute(stmt)).unique().scalars().all(),
            await self.count(),
        )
