from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from fastapi_users.db import BaseUserDatabase
from pydantic import EmailStr
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
)
from core.dto.pagination import PageParams
from user.models.user import OAuthAccountORM as OauthModel
from user.models.user import UserORM as Model


class UserRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
    BaseUserDatabase[Model, UUID],  # pyright: ignore[reportInvalidTypeArguments]
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

    async def exists_person(self, person_id: UUID) -> bool:
        return await self.exists(Model.person_id == person_id)

    async def get_by_person_id(self, person_id: UUID) -> Model | None:
        return await self.get_one(Model.person_id == person_id)

    async def get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> Model | None:
        table = self.oauth_account_table
        oauth_name = cast("InstrumentedAttribute[str]", table.oauth_name)
        account_column = cast("InstrumentedAttribute[str]", table.account_id)
        stmt = (
            select(self.model)
            .join(table)
            .where(oauth_name == oauth, account_column == account_id)
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def create(self, create_dict: dict[str, Any]) -> Model:
        return await self.add_n_return(create_dict)

    async def update(self, user: Model, update_dict: dict[str, Any]) -> Model:
        return cast("Model", await self.update_one(user.id, update_dict))

    async def delete(self, user: Model) -> None:
        await self.delete_one(user.id)

    async def add_oauth_account(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, user: Model, create_dict: dict[str, Any]
    ) -> Model:
        await self.session.refresh(user)
        oauth_account = self.oauth_account_table(**create_dict)
        self.session.add(oauth_account)
        user.oauth_accounts.append(oauth_account)
        self.session.add(user)
        return user

    async def update_oauth_account(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        user: Model,
        oauth_account: OauthModel,
        update_dict: dict[str, Any],
    ) -> Model:
        for key, value in update_dict.items():
            setattr(oauth_account, key, value)
        self.session.add(oauth_account)
        return user

    async def remove_oauth_account(
        self, user: Model, oauth_account: OauthModel
    ) -> Model:
        user.oauth_accounts.remove(oauth_account)
        await self.session.delete(oauth_account)
        return user

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
    ):
        return await super().search(
            filter, pagination, options=options, scope=scope
        )
