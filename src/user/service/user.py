import hashlib
import secrets
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from logging import getLogger
from typing import Any
from uuid import UUID

import jwt

from core.config.settings import settings
from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest
from core.service.base import BaseService, required_transaction
from core.utils.notify import send_notification
from user.dto.invite import InviteTokenCreateDTO, InviteTokenDTO
from user.dto.session import SessionDTO, SessionTokenDTO
from user.dto.telegram import TelegramLinkTokenDTO
from user.dto.user import (
    OAuthAccountDTO,
    OAuthLoginDTO,
    UserCreateDTO,
    UserDTO,
    UserFilterDTO,
    UserUpdateDTO,
)
from user.exceptions.account import (
    AccountAlreadyExistsError,
    AccountAlreadyVerifiedError,
    AccountInactiveError,
    AccountNotExistsError,
    InvalidResetTokenError,
    InvalidVerificationTokenError,
)
from user.exceptions.profile import InvitePersonNotExistsException
from user.exceptions.user import (
    AccountAlreadyLinked,
    InvalidCurrentPassword,
    InviteTokenExpired,
    InviteTokenInvalid,
    PersonAlreadyHasAccount,
    TelegramBotNotConfigured,
    TelegramLinkPersonRequired,
    UsernameAlreadyExists,
    UserNotFound,
)
from user.filter.user import UserFilter
from user.models.user import UserORM
from user.uow.user import UserUOW
from user.utils.account import (
    publish_account_created,
    publish_account_deleted,
    publish_account_email_verified,
    publish_account_updated,
    publish_telegram_link_code_issued,
)
from user.utils.mail import send_reset_message, send_verify_message
from user.utils.password import PasswordHelper
from user.utils.token import generate_refresh_token

logger = getLogger(__name__)

TELEGRAM_LINK_TOKEN_LIFETIME = 600
VERIFICATION_TOKEN_AUDIENCE = "fastapi-users:verify"
RESET_PASSWORD_TOKEN_AUDIENCE = "fastapi-users:reset"
ACCOUNT_TOKEN_LIFETIME = 3600
TOKEN_ALGORITHM = "HS256"
INVITE_AUDIENCE = "invite"
UNSAFE_USER_FIELDS = frozenset({"is_superuser", "is_active", "is_verified"})
ANNOUNCED_FIELDS = frozenset({"email", "is_verified", "person_id"})


def _encode(data: dict[str, Any], secret: str, lifetime: int) -> str:
    payload = data | {"exp": datetime.now(UTC) + timedelta(seconds=lifetime)}
    return jwt.encode(payload, secret, algorithm=TOKEN_ALGORITHM)


def _decode(token: str, secret: str, audience: str) -> dict[str, Any]:
    return jwt.decode(token, secret, audience=[audience], algorithms=[TOKEN_ALGORITHM])


class UserService(BaseService[UserUOW]):
    def __init__(
        self, uow: UserUOW, password_helper: PasswordHelper | None = None
    ) -> None:
        super().__init__(uow)
        self.password_helper = password_helper or PasswordHelper()

    @staticmethod
    def _to_dto(user: UserORM) -> UserDTO:
        return UserDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            person_id=user.person_id,
            oauth_accounts=[
                dto_from_orm(account, OAuthAccountDTO)
                for account in user.oauth_accounts
            ],
        )

    @staticmethod
    def _secret() -> str:
        return settings.PASS_SECRET.get_secret_value()

    @required_transaction
    async def _get(self, user_id: UUID) -> UserORM:
        user = await self.uow.users.get(user_id)
        if user is None:
            raise AccountNotExistsError()
        return user

    @required_transaction
    async def _get_by_email(self, email: str) -> UserORM:
        user = await self.uow.users.get_by_email(email)
        if user is None:
            raise AccountNotExistsError()
        return user

    @required_transaction
    async def _flushed(self, user_id: UUID) -> UserDTO:
        await self.uow.session.flush()
        return self._to_dto(await self._get(user_id))

    async def get(self, user_id: UUID) -> UserDTO:
        async with self.uow:
            return self._to_dto(await self._get(user_id))

    async def get_by_email(self, email: str) -> UserDTO:
        async with self.uow:
            return self._to_dto(await self._get_by_email(email))

    async def get_by_oauth_account(self, oauth_name: str, account_id: str) -> UserDTO:
        async with self.uow:
            user = await self.uow.users.get_by_oauth_account(oauth_name, account_id)
            if user is None:
                raise AccountNotExistsError()
            return self._to_dto(user)

    async def get_by_person_id(self, person_id: UUID) -> UserDTO | None:
        async with self.uow:
            user = await self.uow.users.get_by_person_id(person_id)
            return self._to_dto(user) if user is not None else None

    async def get_by_telegram_id(self, telegram_id: str) -> UserDTO | None:
        try:
            return await self.get_by_oauth_account("telegram", telegram_id)
        except AccountNotExistsError:
            return None

    async def search(
        self,
        filter: UserFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[UserDTO]:
        async with self.uow as uow:
            users, total = await uow.users.search(
                UserFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(user) for user in users],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def check_username(self, username: str) -> bool:
        async with self.uow as uow:
            return await uow.users.exists_username(username)

    async def authenticate(self, email: str, password: str) -> UserDTO | None:
        async with self.uow as uow:
            user = await uow.users.get_by_email(email)
            if user is None:
                self.password_helper.hash(password)
                return None
            verified, updated_hash = self.password_helper.verify_and_update(
                password, user.hashed_password
            )
            if not verified:
                return None
            result = self._to_dto(user)
            if updated_hash is not None:
                await uow.users.update(user, {"hashed_password": updated_hash.encode()})
                await uow.commit()
            return result

    async def create(self, data: UserCreateDTO, *, safe: bool = False) -> UserDTO:
        async with self.uow as uow:
            if await uow.users.exists_email(data.email):
                raise AccountAlreadyExistsError()
            if await uow.users.exists_username(data.username):
                raise UsernameAlreadyExists()
            person_id = None
            if data.invite_token:
                person_id = await self._validate_invite_token(data.invite_token)
            values = dto_dict(data, only_set=True, exclude={"password", "invite_token"})
            if safe:
                values = {
                    key: value
                    for key, value in values.items()
                    if key not in UNSAFE_USER_FIELDS
                }
            values["hashed_password"] = self.password_helper.hash(data.password)
            if person_id is not None:
                values["person_id"] = person_id
            created = await uow.users.create(values)
            result = await self._flushed(created.id)
            await uow.commit()
        await self._announce_created(result)
        return result

    @required_transaction
    async def _verify_current_password(
        self, user: UserORM, current_password: str | None
    ) -> None:
        if not current_password:
            raise InvalidCurrentPassword()
        verified, _ = self.password_helper.verify_and_update(
            current_password, user.hashed_password
        )
        if not verified:
            logger.debug(
                f"Rejected password change for user {user.id}: "
                "current password mismatch"
            )
            raise InvalidCurrentPassword()

    @required_transaction
    async def _apply_update(self, user: UserORM, update_dict: dict[str, Any]) -> None:
        validated: dict[str, Any] = {}
        for field, value in update_dict.items():
            if field == "email" and value != user.email:
                if await self.uow.users.exists_email(value):
                    raise AccountAlreadyExistsError()
                validated["email"] = value
                validated["is_verified"] = False
            elif field == "password":
                if value is None:
                    continue
                validated["hashed_password"] = self.password_helper.hash(value)
                await self.uow.refresh_tokens.revoke_all_for_user(user.id)
            elif field == "username":
                if value is not None and value != user.username:
                    if await self.uow.users.exists_username(value):
                        raise UsernameAlreadyExists()
                    validated[field] = value
            else:
                validated[field] = value
        if validated:
            await self.uow.users.update(user, validated)

    async def update(
        self, user_id: UUID, data: UserUpdateDTO, *, safe: bool = False
    ) -> UserDTO:
        async with self.uow as uow:
            user = await self._get(user_id)
            values = dto_dict(data, only_set=True)
            if safe:
                values = {
                    key: value
                    for key, value in values.items()
                    if key not in UNSAFE_USER_FIELDS
                }
            current_password = values.pop("current_password", None)
            if safe and values.get("password"):
                await self._verify_current_password(user, current_password)
            await self._apply_update(user, values)
            result = await self._flushed(user_id)
            await uow.commit()
        await self._announce_updated(result, values.keys())
        return result

    async def delete(self, user_id: UUID) -> None:
        async with self.uow as uow:
            await uow.users.delete_one(user_id)
            await uow.commit()
        await publish_account_deleted(user_id)

    async def request_verify(self, user_id: UUID) -> None:
        async with self.uow:
            user = await self._get(user_id)
            if not user.is_active:
                raise AccountInactiveError()
            if user.is_verified:
                raise AccountAlreadyVerifiedError()
            email = user.email
            token = _encode(
                {
                    "sub": str(user.id),
                    "email": email,
                    "aud": VERIFICATION_TOKEN_AUDIENCE,
                },
                self._secret(),
                ACCOUNT_TOKEN_LIFETIME,
            )
        logger.debug(f"Verification requested for user {user_id}")
        await send_verify_message(email=email, token=token)

    async def verify(self, token: str) -> UserDTO:
        try:
            data = _decode(token, self._secret(), VERIFICATION_TOKEN_AUDIENCE)
            user_id = UUID(data["sub"])
            email = data["email"]
        except (jwt.PyJWTError, KeyError, ValueError):
            raise InvalidVerificationTokenError() from None
        async with self.uow as uow:
            try:
                user = await self._get_by_email(email)
            except AccountNotExistsError:
                raise InvalidVerificationTokenError() from None
            if user.id != user_id:
                raise InvalidVerificationTokenError()
            if user.is_verified:
                raise AccountAlreadyVerifiedError()
            await self._apply_update(user, {"is_verified": True})
            result = await self._flushed(user_id)
            await uow.commit()
        await publish_account_email_verified(result.id)
        return result

    async def forgot_password(self, user_id: UUID) -> None:
        async with self.uow:
            user = await self._get(user_id)
            if not user.is_active:
                raise AccountInactiveError()
            fingerprint = self.password_helper.hash(user.hashed_password).decode()
            email = user.email
            token = _encode(
                {
                    "sub": str(user.id),
                    "password_fgpt": fingerprint,
                    "aud": RESET_PASSWORD_TOKEN_AUDIENCE,
                },
                self._secret(),
                ACCOUNT_TOKEN_LIFETIME,
            )
        logger.debug(f"User {user_id} requested a password reset")
        await send_reset_message(email=email, token=token)

    async def reset_password(self, token: str, password: str) -> UserDTO:
        try:
            data = _decode(token, self._secret(), RESET_PASSWORD_TOKEN_AUDIENCE)
            user_id = UUID(data["sub"])
            fingerprint = data["password_fgpt"]
        except (jwt.PyJWTError, KeyError, ValueError):
            raise InvalidResetTokenError() from None
        async with self.uow as uow:
            user = await self._get(user_id)
            valid, _ = self.password_helper.verify_and_update(
                user.hashed_password, fingerprint
            )
            if not valid:
                raise InvalidResetTokenError()
            if not user.is_active:
                raise AccountInactiveError()
            await self._apply_update(user, {"password": password})
            result = await self._flushed(user_id)
            await uow.commit()
        return result

    @required_transaction
    async def _link_oauth(self, user: UserORM, account: dict[str, Any]) -> UserORM:
        return await self.uow.users.add_oauth_account(user, account)

    @required_transaction
    async def _refresh_oauth(self, user: UserORM, account: dict[str, Any]) -> None:
        for existing in user.oauth_accounts:
            if (
                existing.account_id == account["account_id"]
                and existing.oauth_name == account["oauth_name"]
            ):
                await self.uow.users.update_oauth_account(user, existing, account)

    @required_transaction
    async def _create_from_oauth(
        self, login: OAuthLoginDTO, account: dict[str, Any], verified: bool
    ) -> UserORM:
        username = login.account_username
        if username is not None and await self.uow.users.exists_username(username):
            username = None
        user = await self.uow.users.create(
            {
                "email": login.account_email,
                "hashed_password": self.password_helper.hash(
                    self.password_helper.generate()
                ),
                "is_verified": verified,
                "username": username,
            }
        )
        return await self._link_oauth(user, account)

    async def oauth_callback(
        self,
        login: OAuthLoginDTO,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> UserDTO:
        account = dto_dict(login, exclude={"account_username"})
        created = False
        async with self.uow as uow:
            user = await uow.users.get_by_oauth_account(
                login.oauth_name, login.account_id
            )
            if user is not None:
                await self._refresh_oauth(user, account)
            else:
                existing = await uow.users.get_by_email(login.account_email)
                if existing is None:
                    user = await self._create_from_oauth(
                        login, account, is_verified_by_default
                    )
                    created = True
                elif associate_by_email:
                    user = await self._link_oauth(existing, account)
                else:
                    raise AccountAlreadyExistsError()
            result = await self._flushed(user.id)
            await uow.commit()
        if created:
            await self._announce_created(result)
        return result

    async def oauth_associate_callback(
        self, user_id: UUID, login: OAuthLoginDTO
    ) -> UserDTO:
        account = dto_dict(login, exclude={"account_username"})
        async with self.uow as uow:
            user = await self._get(user_id)
            await self._link_oauth(user, account)
            result = await self._flushed(user_id)
            await uow.commit()
        return result

    async def link_telegram_oauth(
        self, person_id: UUID, telegram_id: str, username: str | None
    ) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_person_id(person_id)
            if user is None:
                return
            account = {
                "oauth_name": "telegram",
                "access_token": "",
                "account_id": telegram_id,
                "account_email": f"{username or telegram_id}@telegram.local",
                "expires_at": None,
                "refresh_token": None,
            }
            existing = next(
                (a for a in user.oauth_accounts if a.oauth_name == "telegram"),
                None,
            )
            if existing is not None:
                await uow.users.update_oauth_account(user, existing, account)
            else:
                await uow.users.add_oauth_account(user, account)
            await uow.commit()

    async def unlink_telegram_oauth(self, person_id: UUID) -> None:
        async with self.uow as uow:
            user = await uow.users.get_by_person_id(person_id)
            if user is None:
                return
            existing = next(
                (a for a in user.oauth_accounts if a.oauth_name == "telegram"),
                None,
            )
            if existing is not None:
                await uow.users.remove_oauth_account(user, existing)
                await uow.commit()

    @required_transaction
    async def _validate_invite_token(self, token: str) -> UUID:
        try:
            data = _decode(
                token, settings.USER_SECRET.get_secret_value(), INVITE_AUDIENCE
            )
        except jwt.ExpiredSignatureError:
            raise InviteTokenExpired() from None
        except jwt.PyJWTError:
            raise InviteTokenInvalid() from None
        try:
            person_id = UUID(data["person_id"])
        except (KeyError, TypeError, ValueError):
            raise InviteTokenInvalid() from None
        if await self.uow.persons.get_by_id(person_id) is None:
            raise InvitePersonNotExistsException()
        if await self.uow.users.exists_person(person_id):
            raise PersonAlreadyHasAccount()
        return person_id

    async def create_invite_token(self, invite: InviteTokenCreateDTO) -> InviteTokenDTO:
        async with self.uow:
            if await self.uow.persons.get_by_id(invite.person_id) is None:
                raise InvitePersonNotExistsException()
            if await self.uow.users.exists_person(invite.person_id):
                raise PersonAlreadyHasAccount()
        lifetime = invite.expires_in or settings.INVITE_TOKEN_LIFETIME
        token = _encode(
            {"person_id": str(invite.person_id), "aud": [INVITE_AUDIENCE]},
            settings.USER_SECRET.get_secret_value(),
            lifetime,
        )
        expires_at = int(datetime.now(UTC).timestamp()) + lifetime
        return InviteTokenDTO(token=token, expires_at=expires_at)

    async def create_telegram_link_token(
        self, person_id: UUID | None
    ) -> TelegramLinkTokenDTO:
        if person_id is None:
            raise TelegramLinkPersonRequired()
        if not settings.BOT_TG_USERNAME:
            raise TelegramBotNotConfigured()
        code = secrets.token_urlsafe(16)
        await publish_telegram_link_code_issued(
            code, person_id, TELEGRAM_LINK_TOKEN_LIFETIME
        )
        expires_at = int(datetime.now(UTC).timestamp()) + TELEGRAM_LINK_TOKEN_LIFETIME
        return TelegramLinkTokenDTO(
            token=code,
            deep_link=f"https://t.me/{settings.BOT_TG_USERNAME}?start={code}",
            expires_at=expires_at,
        )

    async def admin_link_person(self, user_id: UUID, person_id: UUID) -> UserDTO:
        async with self.uow as uow:
            if await uow.users.get_by_id(user_id) is None:
                raise UserNotFound()
            if await uow.persons.get_by_id(person_id) is None:
                raise InvitePersonNotExistsException()
            if await uow.users.exists_person(person_id):
                raise PersonAlreadyHasAccount()
            await uow.users.update_one(user_id, {"person_id": person_id})
            result = await self._flushed(user_id)
            await uow.commit()
        await self._announce_updated(result, {"person_id"})
        return result

    async def link_invite(self, user_id: UUID, token: str) -> UserDTO:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFound()
            if user.person_id is not None:
                raise AccountAlreadyLinked()
            person_id = await self._validate_invite_token(token)
            await uow.users.update_one(user_id, {"person_id": person_id})
            result = await self._flushed(user_id)
            await uow.commit()
        await self._announce_updated(result, {"person_id"})
        return result

    async def announce_login(self, user_id: UUID, device_info: str | None) -> None:
        body = f"Выполнен вход с устройства: {device_info}" if device_info else ""
        logger.debug(f"Dispatching login notification for user {user_id}")
        await send_notification(
            NotificationRequest(
                user_ids=[user_id],
                category=NotificationCategory.system,
                title="Вход в систему",
                body=body,
            )
        )

    @staticmethod
    async def _announce_created(user: UserDTO) -> None:
        logger.info(f"User {user.id} has registered.")
        await publish_account_created(
            user.id, user.email, user.is_verified, user.person_id
        )

    @staticmethod
    async def _announce_updated(user: UserDTO, changed: Iterable[str]) -> None:
        if ANNOUNCED_FIELDS & set(changed):
            await publish_account_updated(
                user.id, user.email, user.is_verified, user.person_id
            )

    @required_transaction
    async def _new_session(
        self, user_id: UUID, device_info: str | None, ip_address: str | None
    ) -> SessionTokenDTO:
        raw, hashed = generate_refresh_token()
        session = await self.uow.sessions.add_n_return(
            {
                "user_id": user_id,
                "device_info": device_info,
                "ip_address": ip_address,
            }
        )
        await self.uow.refresh_tokens.add_one(
            {
                "token_hash": hashed,
                "user_id": user_id,
                "session_id": session.id,
                "expires_at": datetime.now(UTC)
                + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS),
            }
        )
        return SessionTokenDTO(
            user_id=user_id, session_id=session.id, refresh_token=raw
        )

    async def open_session(
        self,
        user_id: UUID,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> SessionTokenDTO:
        async with self.uow as uow:
            result = await self._new_session(user_id, device_info, ip_address)
            await uow.commit()
        return result

    @required_transaction
    async def _rotate_session(
        self,
        raw_token: str,
        device_info: str | None,
        ip_address: str | None,
    ) -> SessionTokenDTO | None:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        stored = await self.uow.refresh_tokens.get_by_token_hash(token_hash)
        if stored is None:
            return None
        if stored.expires_at < datetime.now(UTC):
            return None
        if stored.is_revoked:
            return None
        if stored.is_used:
            await self.uow.refresh_tokens.revoke_all_by_session(stored.session_id)
            return None
        stored.is_used = True
        await self.uow.session.flush()
        await self.uow.sessions.update_last_used(
            stored.session_id, ip_address=ip_address, device_info=device_info
        )
        new_raw, new_hashed = generate_refresh_token()
        await self.uow.refresh_tokens.add_one(
            {
                "token_hash": new_hashed,
                "user_id": stored.user_id,
                "session_id": stored.session_id,
                "expires_at": datetime.now(UTC)
                + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRE_SECONDS),
            }
        )
        return SessionTokenDTO(
            user_id=stored.user_id,
            session_id=stored.session_id,
            refresh_token=new_raw,
        )

    async def refresh_session(
        self,
        raw_token: str,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> SessionTokenDTO | None:
        async with self.uow as uow:
            result = await self._rotate_session(raw_token, device_info, ip_address)
            await uow.commit()
        return result

    async def revoke_session_by_token(self, raw_token: str) -> None:
        async with self.uow as uow:
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            stored = await uow.refresh_tokens.get_by_token_hash(token_hash)
            if stored is not None:
                await uow.refresh_tokens.revoke(stored.id)
            await uow.commit()

    async def list_sessions(
        self, user_id: UUID, current_session_id: UUID | None = None
    ) -> list[SessionDTO]:
        async with self.uow as uow:
            sessions = await uow.sessions.list_active_for_user(user_id)
            logger.debug(f"Listing {len(sessions)} active sessions for user {user_id}")
            items = [
                SessionDTO(
                    id=session.id,
                    device_info=session.device_info,
                    ip_address=session.ip_address,
                    created_at=session.created_at,
                    last_used_at=session.last_used_at,
                    is_current=session.id == current_session_id,
                )
                for session in sessions
            ]
        items.sort(key=lambda item: not item.is_current)
        return items

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> bool:
        async with self.uow as uow:
            session = await uow.sessions.get_for_user(user_id, session_id)
            if session is None:
                logger.debug(f"Session {session_id} not found for user {user_id}")
                return False
            await uow.refresh_tokens.revoke_all_by_session(session_id)
            await uow.commit()
        logger.debug(f"Revoked session {session_id} of user {user_id}")
        return True

    async def revoke_other_sessions(
        self, user_id: UUID, current_session_id: UUID | None = None
    ) -> int:
        async with self.uow as uow:
            sessions = await uow.sessions.list_active_for_user(user_id)
            revoked = 0
            for session in sessions:
                if session.id == current_session_id:
                    continue
                await uow.refresh_tokens.revoke_all_by_session(session.id)
                revoked += 1
            await uow.commit()
        logger.debug(f"Revoked {revoked} other sessions for user {user_id}")
        return revoked

    async def cleanup_expired_sessions(self) -> int:
        async with self.uow as uow:
            count = await uow.refresh_tokens.delete_expired()
            await uow.commit()
        return count
