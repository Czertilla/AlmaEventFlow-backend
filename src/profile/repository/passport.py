from uuid import UUID
from sqlalchemy import delete
from sqlalchemy.orm import joinedload
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from profile.models.passport import PassportORM as Model, NameVariantORM


class PassportRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    with_name_variant = joinedload(Model.name_variant)

    async def get_many_by_profile(
        self, profile_id: UUID, limit: int, offset: int
    ) -> tuple[Model, int]:
        criteria = Model.profile_id == profile_id
        return (
            await self.get_many(
                criteria,
                limit_=limit,
                offset_=offset,
                options_=(self.with_name_variant,),
            ),
            await self.count(criteria),
        )

    async def add_n_return(self, data, options=(with_name_variant,)):
        return await super().add_n_return(data, options)

    async def get_by_id(self, id, options=(with_name_variant,)):
        return await super().get_by_id(id, options)

    async def clear_by_profile(self, profile_id: UUID):
        await self.execute(delete(Model).where(Model.profile_id == profile_id))


class NameVariantRepo(
    SQLAlchemyRepository[NameVariantORM],
    IDRepositoryMixin[NameVariantORM, UUID],
    UpsertRepositoryMixin[NameVariantORM, UUID],
):
    model = NameVariantORM
