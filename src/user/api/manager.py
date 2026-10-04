from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from fastapi import Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions, schemas
from fastapi_users.password import PasswordHelperProtocol

from user.api.v1.schema.user import UserCreate, UserUpdate
from user.dto.user import OAuthLoginDTO, UserDTO
from user.exceptions.account import (
    AccountAlreadyExistsError,
    AccountAlreadyVerifiedError,
    AccountInactiveError,
    AccountNotExistsError,
    InvalidResetTokenError,
    InvalidVerificationTokenError,
)
from user.service.user import UserService
from user.utils.auth_response import start_session


@contextmanager
def _translated() -> Generator[None]:
    try:
        yield
    except AccountNotExistsError:
        raise exceptions.UserNotExists() from None
    except AccountAlreadyExistsError:
        raise exceptions.UserAlreadyExists() from None
    except AccountInactiveError:
        raise exceptions.UserInactive() from None
    except AccountAlreadyVerifiedError:
        raise exceptions.UserAlreadyVerified() from None
    except InvalidVerificationTokenError:
        raise exceptions.InvalidVerifyToken() from None
    except InvalidResetTokenError:
        raise exceptions.InvalidResetPasswordToken() from None


class UserManager(UUIDIDMixin, BaseUserManager[Any, UUID]):
    def __init__(
        self,
        service: UserService,
        password_helper: PasswordHelperProtocol | None = None,
    ) -> None:
        self.service = service
        self.password_helper = password_helper or service.password_helper

    async def get(self, id: UUID) -> UserDTO:
        with _translated():
            return await self.service.get(id)

    async def get_by_email(self, user_email: str) -> UserDTO:
        with _translated():
            return await self.service.get_by_email(user_email)

    async def get_by_oauth_account(self, oauth: str, account_id: str) -> UserDTO:
        with _translated():
            return await self.service.get_by_oauth_account(oauth, account_id)

    async def create(
        self,
        user_create: schemas.BaseUserCreate,
        safe: bool = False,
        request: Request | None = None,
    ) -> UserDTO:
        schema = UserCreate.model_validate(user_create, from_attributes=True)
        with _translated():
            return await self.service.create(schema.to_dto(), safe=safe)

    async def update(
        self,
        user_update: schemas.BaseUserUpdate,
        user: Any,
        safe: bool = False,
        request: Request | None = None,
    ) -> UserDTO:
        schema = UserUpdate.model_validate(user_update, from_attributes=True)
        with _translated():
            return await self.service.update(user.id, schema.to_dto(), safe=safe)

    async def delete(self, user: Any, request: Request | None = None) -> None:
        with _translated():
            await self.service.delete(user.id)

    async def authenticate(
        self, credentials: OAuth2PasswordRequestForm
    ) -> UserDTO | None:
        return await self.service.authenticate(
            credentials.username, credentials.password
        )

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: Any,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> Any:
        email, username = account_email
        login = OAuthLoginDTO(
            oauth_name=oauth_name,
            access_token=access_token,
            account_id=account_id,
            account_email=email,
            account_username=username,
            expires_at=expires_at,
            refresh_token=refresh_token,
        )
        with _translated():
            return await self.service.oauth_callback(
                login,
                associate_by_email=associate_by_email,
                is_verified_by_default=is_verified_by_default,
            )

    async def oauth_associate_callback(
        self,
        user: Any,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: Any,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
    ) -> Any:
        email, username = account_email
        login = OAuthLoginDTO(
            oauth_name=oauth_name,
            access_token=access_token,
            account_id=account_id,
            account_email=email,
            account_username=username,
            expires_at=expires_at,
            refresh_token=refresh_token,
        )
        with _translated():
            return await self.service.oauth_associate_callback(user.id, login)

    async def request_verify(self, user: Any, request: Request | None = None) -> None:
        with _translated():
            await self.service.request_verify(user.id)

    async def verify(self, token: str, request: Request | None = None) -> UserDTO:
        with _translated():
            return await self.service.verify(token)

    async def forgot_password(self, user: Any, request: Request | None = None) -> None:
        with _translated():
            await self.service.forgot_password(user.id)

    async def reset_password(
        self, token: str, password: str, request: Request | None = None
    ) -> UserDTO:
        with _translated():
            return await self.service.reset_password(token, password)

    async def on_after_login(
        self,
        user: Any,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        if request is None or response is None:
            return
        await start_session(request, response, user.id, self.service)
