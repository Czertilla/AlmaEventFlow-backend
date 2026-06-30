from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from user.models.refresh_token import RefreshTokenORM
from user.models.session import SessionORM as Model


class SessionRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_active_by_user(self, user_id: UUID) -> list[Model]:
        return await self.get_many(Model.user_id == user_id)

    async def list_active_for_user(self, user_id: UUID) -> list[Model]:
        """Sessions of ``user_id`` that still hold at least one non-revoked,
        non-expired refresh token, most recently used first."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Model)
            .join(RefreshTokenORM, RefreshTokenORM.session_id == Model.id)
            .where(
                Model.user_id == user_id,
                ~RefreshTokenORM.is_revoked,
                RefreshTokenORM.expires_at > now,
            )
            .distinct()
            .order_by(Model.last_used_at.desc())
        )
        return (await self.execute(stmt)).scalars().all()

    async def get_for_user(
        self, user_id: UUID, session_id: UUID
    ) -> Model | None:
        return await self.get_one(
            Model.id == session_id, Model.user_id == user_id
        )

    async def update_last_used(
        self,
        session_id: UUID,
        ip_address: str | None = None,
        device_info: str | None = None,
    ) -> None:
        values: dict = {"last_used_at": datetime.now(timezone.utc)}
        if ip_address is not None:
            values["ip_address"] = ip_address
        if device_info is not None:
            values["device_info"] = device_info
        stmt = update(Model).where(Model.id == session_id).values(**values)
        await self.execute(stmt, flush=True)
