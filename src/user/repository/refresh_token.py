from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import delete, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from user.models.refresh_token import RefreshTokenORM as Model


class RefreshTokenRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_token_hash(self, token_hash: str) -> Model | None:
        return await self.get_one(Model.token_hash == token_hash)

    async def get_active_by_session(self, session_id: UUID) -> list[Model]:
        return await self.get_many(
            Model.session_id == session_id,
            ~Model.is_revoked,
            Model.expires_at > datetime.now(timezone.utc),
        )

    async def revoke(self, token_id: UUID) -> None:
        await self.update_one(token_id, {"is_revoked": True})

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            update(Model)
            .where(Model.user_id == user_id, ~Model.is_revoked)
            .values(is_revoked=True)
        )
        await self.execute(stmt, flush=True)

    async def revoke_all_by_session(self, session_id: UUID) -> None:
        stmt = (
            update(Model)
            .where(Model.session_id == session_id, ~Model.is_revoked)
            .values(is_revoked=True)
        )
        await self.execute(stmt, flush=True)

    async def delete_expired(self) -> int:
        stmt = delete(Model).where(Model.expires_at < datetime.now(timezone.utc))
        result = await self.execute(stmt)
        return result.rowcount
