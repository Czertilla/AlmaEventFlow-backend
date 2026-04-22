from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload, with_loader_criteria

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from profile.models.contact import ContactORM
from profile.models.person import PersonORM as Model


class PersonRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    with_contacts = selectinload(Model.contacts)
    with_main_contacts = with_loader_criteria(ContactORM, ContactORM.is_main)
    all_options = (with_contacts, with_main_contacts)

    async def get_with_contacts(self, id: UUID) -> Model | None:
        return await self.get_by_id(
            id, (self.with_contacts, self.with_main_contacts)
        )

    async def add_n_return(
        self, data, options=(with_contacts, with_main_contacts)
    ):
        return await super().add_n_return(data, options)
    
    async def update_one(self, id, data, flush = False):
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
            .options(*self.all_options)
        )
        return (await self.execute(stmt, flush)).unique().scalar_one_or_none()

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

    async def upsert(self, data, options = all_options):
        return await super().upsert(data, options)