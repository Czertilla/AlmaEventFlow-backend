from uuid import UUID
from datetime import datetime
from sqlalchemy import select, delete

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from user.models.session import SessionORM as Model


class SessionRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_token_hash(self, token_hash: str) -> Model | None:
        return await self.get_one(Model.token_hash == token_hash)

    async def get_active_by_user(self, user_id: UUID) -> list[Model]:
        return await self.get_many(
            Model.user_id == user_id,
            ~Model.is_revoked,
            Model.expires_at > datetime.now(),
        )

    async def revoke(self, token_id: UUID) -> None:
        await self.update_one(token_id, {"is_revoked": True})

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = select(Model).where(Model.user_id == user_id, ~Model.is_revoked)
        tokens = (await self.execute(stmt)).scalars().all()
        for token in tokens:
            token.is_revoked = True
            self.session.add(token)

    async def delete_expired(self) -> int:
        stmt = delete(Model).where(Model.expires_at < datetime.now())
        result = await self.execute(stmt)
        return result.rowcount
