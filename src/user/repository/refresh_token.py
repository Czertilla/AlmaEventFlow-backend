from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin
from user.models.refresh_token import RefreshTokenORM as Model


class RefreshTokenRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_token_hash(
        self, token_hash: str, *, for_update: bool = False
    ) -> Model | None:
        stmt = select(Model).where(Model.token_hash == token_hash)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def get_active_by_session(self, session_id: UUID) -> list[Model]:
        return await self.get_many(
            Model.session_id == session_id,
            ~Model.is_revoked,
            Model.expires_at > datetime.now(UTC),
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
        stmt = delete(Model).where(Model.expires_at < datetime.now(UTC))
        result = cast("CursorResult[Any]", await self.execute(stmt))
        return result.rowcount
