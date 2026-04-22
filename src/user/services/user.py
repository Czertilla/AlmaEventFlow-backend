from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
from logging import getLogger
import uuid
import jwt
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi_users import (
    BaseUserManager,
    UUIDIDMixin,
    models,
    exceptions,
    schemas,
)
from fastapi_users.password import PasswordHelperProtocol, PasswordHelper
from fastapi_users.jwt import generate_jwt, decode_jwt
from pydantic import BaseModel

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, T, required_transaction, autocommit

from user.config.settings import settings
from user.exceptions.user import UsernameAlreadyExists
from user.models.user import UserORM
from user.schemas.user import OAuthAccountDict, UserOauthAccount, UserRead
from user.uow.user import UserUOW
from user.api.kafka.pub.mail import send_verify_message

SECRET = settings.PASS_SECRET

logger = getLogger(__name__)

Schema = TypeVar("Schema", bound=BaseModel)


class UserService(
    BaseService[UserUOW], UUIDIDMixin, BaseUserManager[UserORM, uuid.UUID]
):
    reset_password_token_secret = SECRET.get_secret_value()
    verification_token_secret = SECRET.get_secret_value()

    def __init__(
        self,
        uow: T,
        password_helper: PasswordHelperProtocol = None,
    ):
        super().__init__(uow)
        self.password_helper = password_helper or PasswordHelper()

    @staticmethod
    def user_existing(func):
        @wraps(func)
        async def wrapper(*args, **kwargs) -> UserORM:
            user = await func(*args, **kwargs)
            if user is None:
                raise exceptions.UserNotExists()
            return user

        return wrapper

    @staticmethod
    def user_transaction(schema_type: type[Schema]):
        def decorator(func) -> Callable[..., Schema]:
            @wraps(func)
            async def wrapper(self: "UserService", *args, **kwargs) -> UserRead:
                async with self.uow:
                    return schema_type.model_validate(
                        await func(self, *args, **kwargs)
                    )

            return wrapper

        return decorator

    @user_existing
    @required_transaction
    async def _get(self, id: uuid.UUID) -> UserORM:
        return await self.uow.users.get(id)

    @user_existing
    @required_transaction
    async def _get_by_email(self, user_email: str) -> UserORM:
        return await self.uow.users.get_by_email(user_email)

    @user_existing
    @required_transaction
    async def _get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> UserORM:
        return await self.uow.users.get_by_oauth_account(oauth, account_id)

    @user_transaction(UserRead)
    async def get(self, id: uuid.UUID) -> UserRead:
        return await self._get(id)

    @user_transaction(UserRead)
    async def get_by_email(self, user_email: str) -> models.UP:
        return await self._get_by_email(user_email)

    @user_transaction(UserRead)
    async def get_by_oauth_account(
        self, oauth: str, account_id: str
    ) -> UserRead:
        return await self._get_by_oauth_account(oauth, account_id)

    @user_transaction(UserRead)
    @autocommit
    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> UserRead:
        await self.validate_password(user_create.password, user_create)
        if await self.uow.users.exists_email(user_create.email):
            raise exceptions.UserAlreadyExists()
        if await self.uow.users.exists_username(user_create.username):
            raise UsernameAlreadyExists()
        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        created_user = await self.uow.users.create(user_dict)
        await self.on_after_register(created_user, request)
        return created_user

    @required_transaction
    async def _associate_account(
        self,
        oauth_account_dict: dict,
        account_email: str,
        account_username: str | None,
        associate_by_email: bool,
    ):
        user = await self._get_by_email(account_email)
        if not associate_by_email:
            raise exceptions.UserAlreadyExists()
        if (
            account_username is not None
            and user.username != account_username
            and await self.uow.users.exists_username(account_username)
        ):
            user.username = account_username
            await self.uow.session.flush()
        user = await self.uow.users.add_oauth_account(user, oauth_account_dict)

    @required_transaction
    async def _create_account(
        self,
        oauth_account_dict: OAuthAccountDict,
        account_email: str,
        account_username: str | None,
        is_verified_by_default: bool,
        request: Request,
    ):
        password = self.password_helper.generate()
        user_dict = {
            "email": account_email,
            "hashed_password": self.password_helper.hash(password),
            "is_verified": is_verified_by_default,
            "username": account_username
            if account_username is not None
            and not await self.uow.users.exists_username(account_username)
            else None,
        }
        user = await self.uow.users.create(user_dict)
        user = await self.uow.users.add_oauth_account(user, oauth_account_dict)
        await self.on_after_register(user, request)
        return user

    @required_transaction
    async def _update_oauth(
        self,
        oauth_account_dict: OAuthAccountDict,
        user: UserORM,
        account_id: str,
        oauth_name: str,
    ):
        for existing_oauth_account in list(
            filter(
                lambda account: account.account_id == account_id
                and account.oauth_name == oauth_name,
                user.oauth_accounts,
            )
        ):
            user = await self.uow.users.update_oauth_account(
                user, existing_oauth_account, oauth_account_dict
            )
        return user

    @user_transaction(UserOauthAccount)
    @autocommit
    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: tuple[str, str | None],
        expires_at: Optional[int] = None,
        refresh_token: Optional[str] = None,
        request: Optional[Request] = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> UserOauthAccount:
        account_email, account_username = account_email
        oauth_account_dict = OAuthAccountDict(
            oauth_name=oauth_name,
            access_token=access_token,
            account_id=account_id,
            account_email=account_email,
            expires_at=expires_at,
            refresh_token=refresh_token,
        )
        try:
            user = await self._get_by_oauth_account(oauth_name, account_id)
        except exceptions.UserNotExists:
            try:
                user = await self._associate_account(
                    oauth_account_dict,
                    account_email,
                    account_username,
                    associate_by_email,
                )
            except exceptions.UserNotExists:
                user = await self._create_account(
                    oauth_account_dict,
                    account_email,
                    account_username,
                    is_verified_by_default,
                    request,
                )
        else:
            user = await self._update_oauth(
                oauth_account_dict, user, account_id, oauth_name
            )
        return user

    @user_transaction(UserOauthAccount)
    @autocommit
    async def oauth_associate_callback(
        self,
        user: models.UOAP,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: tuple[str, str | None],
        expires_at: Optional[int] = None,
        refresh_token: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> UserOauthAccount:
        oauth_account_dict = OAuthAccountDict(
            oauth_name=oauth_name,
            access_token=access_token,
            account_id=account_id,
            account_email=account_email,
            expires_at=expires_at,
            refresh_token=refresh_token,
        )
        account_email, account_username = account_email
        user = await self._get(user.id)
        if (
            account_username is not None
            and user.username != account_username
            and await self.uow.users.exists_username(account_username)
        ):
            user.username = account_username
            await self.uow.session.flush()
        user = await self.uow.users.add_oauth_account(user, oauth_account_dict)
        await self.on_after_update(user, {}, request)
        return user

    async def request_verify(
        self, user: models.UP, request: Request | None = None
    ) -> JSONResponse:
        if not user.is_active:
            raise exceptions.UserInactive()
        if user.is_verified:
            raise exceptions.UserAlreadyVerified()

        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "aud": self.verification_token_audience,
        }
        token = generate_jwt(
            token_data,
            self.verification_token_secret,
            self.verification_token_lifetime_seconds,
        )
        return await self.on_after_request_verify(user, token, request)

    @user_transaction(UserRead)
    @autocommit
    async def verify(
        self, token: str, request: Optional[Request] = None
    ) -> UserRead:
        try:
            data = decode_jwt(
                token,
                self.verification_token_secret,
                [self.verification_token_audience],
            )
        except jwt.PyJWTError:
            raise exceptions.InvalidVerifyToken()
        try:
            user_id = data["sub"]
            email = data["email"]
        except KeyError:
            raise exceptions.InvalidVerifyToken()
        try:
            user = await self._get_by_email(email)
        except exceptions.UserNotExists:
            raise exceptions.InvalidVerifyToken()
        try:
            parsed_id = self.parse_id(user_id)
        except exceptions.InvalidID:
            raise exceptions.InvalidVerifyToken()
        if parsed_id != user.id:
            raise exceptions.InvalidVerifyToken()
        if user.is_verified:
            raise exceptions.UserAlreadyVerified()
        verified_user = await self._update(user, {"is_verified": True})
        await self.on_after_verify(verified_user, request)
        return verified_user

    async def get_many(
        self, page_params: SPageParam = SPageParam()
    ) -> SPage[UserRead]:
        async with self.uow as uow:
            users, total = await uow.users.get_many_cron(
                limit=page_params.limit,
                offset=page_params.offset,
            )
            return SPage(
                items=[UserRead.model_validate(user) for user in users],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def check_username(self, username: str) -> bool:
        async with self.uow as uow:
            return await uow.users.exists_username(username)

    async def forgot_password(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        if not user.is_active:
            raise exceptions.UserInactive()

        token_data = {
            "sub": str(user.id),
            "password_fgpt": self.password_helper.hash(user.hashed_password),
            "aud": self.reset_password_token_audience,
        }
        token = generate_jwt(
            token_data,
            self.reset_password_token_secret,
            self.reset_password_token_lifetime_seconds,
        )
        await self.on_after_forgot_password(user, token, request)

    @user_transaction(UserRead)
    @autocommit
    async def reset_password(
        self, token: str, password: str, request: Optional[Request] = None
    ) -> UserRead:
        try:
            data = decode_jwt(
                token,
                self.reset_password_token_secret,
                [self.reset_password_token_audience],
            )
        except jwt.PyJWTError:
            raise exceptions.InvalidResetPasswordToken()
        try:
            user_id = data["sub"]
            password_fingerprint = data["password_fgpt"]
        except KeyError:
            raise exceptions.InvalidResetPasswordToken()
        try:
            parsed_id = self.parse_id(user_id)
        except exceptions.InvalidID:
            raise exceptions.InvalidResetPasswordToken()
        user = await self._get(parsed_id)
        valid_password_fingerprint, _ = self.password_helper.verify_and_update(
            user.hashed_password, password_fingerprint
        )
        if not valid_password_fingerprint:
            raise exceptions.InvalidResetPasswordToken()
        if not user.is_active:
            raise exceptions.UserInactive()
        updated_user = await self._update(user, {"password": password})
        await self.on_after_reset_password(user, request)
        return updated_user

    @user_transaction(UserRead)
    @autocommit
    async def update(
        self,
        user_update: schemas.UU,
        user: models.UP,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> UserRead:
        if safe:
            updated_user_data = user_update.create_update_dict()
        else:
            updated_user_data = user_update.create_update_dict_superuser()
        updated_user = await self._update(user, updated_user_data)
        await self.on_after_update(updated_user, updated_user_data, request)
        return updated_user

    async def delete(
        self,
        user: models.UP,
        request: Optional[Request] = None,
    ) -> None:
        await self.on_before_delete(user, request)
        async with self.uow as uow:
            await uow.users.delete(user)
            await uow.commit()
        await self.on_after_delete(user, request)

    async def validate_password(
        self, password: str, user: Union[schemas.UC, models.UP]
    ) -> None:
        return  # pragma: no cover

    async def on_after_register(
        self, user: UserORM, request: Optional[Request] = None
    ):
        logger.info(f"User {user.id} has registered.")

    async def on_after_update(
        self,
        user: models.UP,
        update_dict: dict[str, Any],
        request: Optional[Request] = None,
    ) -> None:
        return  # pragma: no cover

    async def on_after_request_verify(
        self, user: UserORM, token: str, request: Optional[Request] = None
    ) -> JSONResponse:
        logger.warning(
            f"Verification requested for user {user.id}. Verification token: {token}"
        )
        return await send_verify_message(email=user.email, token=token)

    async def on_after_verify(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def on_after_forgot_password(
        self, user: UserORM, token: str, request: Optional[Request] = None
    ):
        logger.warning(
            f"User {user.id} has forgot their password. Reset token: {token}"
        )

    async def on_after_reset_password(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def on_after_login(
        self,
        user: models.UP,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ) -> None:
        return  # pragma: no cover

    async def on_before_delete(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def on_after_delete(
        self, user: models.UP, request: Optional[Request] = None
    ) -> None:
        return  # pragma: no cover

    async def authenticate(
        self, credentials: OAuth2PasswordRequestForm
    ) -> UserRead | None:
        async with self.uow as uow:
            try:
                user = await self._get_by_email(credentials.username)
            except exceptions.UserNotExists:
                # Run the hasher to mitigate timing attack
                # Inspired from Django: https://code.djangoproject.com/ticket/20760
                self.password_helper.hash(credentials.password)
                return None

            verified, updated_password_hash = (
                self.password_helper.verify_and_update(
                    credentials.password, user.hashed_password
                )
            )
            if not verified:
                return None
            # Update password hash to a more robust one if needed
            if updated_password_hash is not None:
                await uow.users.update(
                    user, {"hashed_password": updated_password_hash}
                )

            return UserRead.model_validate(user)

    @required_transaction
    async def _update(
        self, user: models.UP, update_dict: dict[str, Any]
    ) -> models.UP:
        validated_update_dict = {}
        for field, value in update_dict.items():
            if field == "email" and value != user.email:
                try:
                    await self._get_by_email(value)
                    raise exceptions.UserAlreadyExists()
                except exceptions.UserNotExists:
                    validated_update_dict["email"] = value
                    validated_update_dict["is_verified"] = False
            elif field == "password" and value is not None:
                await self.validate_password(value, user)
                validated_update_dict["hashed_password"] = (
                    self.password_helper.hash(value)
                )
            elif (
                field == "username"
                and value is not None
                and value != user.username
            ):
                if await self.uow.users.exists_username(value):
                    raise UsernameAlreadyExists()
                else:
                    validated_update_dict[field] = value
            else:
                validated_update_dict[field] = value
        return await self.uow.users.update(user, validated_update_dict)
