from typing import Any
from uuid import UUID
from pydantic import EmailStr
from fastapi_users_db_sqlalchemy import BaseUserDatabase
from fastapi_users.models import UP, UOAP
from sqlalchemy import select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from user.models.user import UserORM as Model, OAuthAccountORM as OauthModel


class UserRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    BaseUserDatabase[Model, UUID],
):
    model = Model
    oauth_account_table = OauthModel

    async def get(self, id: UUID) -> Model | None:
        return await self.get_by_id(id)

    async def get_by_email(self, email: EmailStr) -> Model | None:
        return await self.get_one(Model.email == email)

    async def exists_email(self, email: EmailStr) -> bool:
        return await self.exists(Model.email == email)

    async def get_by_username(self, username: str) -> Model | None:
        return await self.get_one(Model.username == username)

    async def exists_username(self, username: str) -> bool:
        return await self.exists(Model.username == username)

    async def get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> Model | None:
        if self.oauth_account_table is None:
            raise NotImplementedError()

        stmt = (
            select(self.model)
            .join(self.oauth_account_table)
            .where(
                self.oauth_account_table.oauth_name == oauth,
                self.oauth_account_table.account_id == account_id,
            )
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def create(self, create_dict: dict[str, Any]) -> Model:
        return await self.add_n_return(create_dict)

    async def update(self, user: UP, update_dict: dict[str, Any]) -> Model:
        return await self.update_one(user.id, update_dict)

    async def delete(self, user: UP) -> None:
        await self.delete_one(user.id)

    async def add_oauth_account(
        self, user: UOAP, create_dict: dict[str, Any]
    ) -> Model:
        await self.session.refresh(user)
        oauth_account = self.oauth_account_table(**create_dict)
        self.session.add(oauth_account)
        user.oauth_accounts.append(oauth_account)
        self.session.add(user)
        return user

    async def update_oauth_account(
        self,
        user: UP,
        oauth_account: OauthModel,
        update_dict: dict[str, Any],
    ) -> Model:
        for key, value in update_dict.items():
            setattr(oauth_account, key, value)
        self.session.add(oauth_account)
        return user

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
        )
        return (
            (await self.execute(stmt)).unique().scalars().all(),
            await self.count(),
        )
