from uuid import UUID

from pydantic import EmailStr

from core.schema.message.core import MQEvent, MQRequest


class AccountData(MQRequest):
    """User account snapshot for projection in other services. ``person_id``
    links the account to its profile person, letting consumers address
    notifications by person."""

    id: UUID
    email: EmailStr
    is_verified: bool = False
    locale: str | None = None
    person_id: UUID | None = None


class AccountCreatedEvent(MQEvent[AccountData]): ...


class AccountUpdatedEvent(AccountCreatedEvent): ...


class AccountVerified(MQRequest):
    """Marks an account's email as verified in projecting services."""

    id: UUID


class AccountEmailVerifiedEvent(MQEvent[AccountVerified]): ...


class AccountDelete(MQRequest):
    id: UUID


class AccountDeletedEvent(MQEvent[AccountDelete]): ...


class ResolveUserIdRequest(MQRequest):
    person_id: UUID


class UserIdResponse(MQRequest):
    user_id: UUID


class LinkTelegramOAuthRequest(MQRequest):
    person_id: UUID
    telegram_id: str
    username: str | None = None


class UnlinkTelegramOAuthRequest(MQRequest):
    person_id: UUID


class TelegramLinkCodeIssued(MQRequest):
    """A one-time deep-link code minted by ``user`` for the caller's own bot
    ``/start`` flow. ``bot`` is the sole reader (Telegram's ``start`` param is
    too short for a signed token, so the code->person_id mapping travels over
    the broker instead of a Redis instance shared across hosts)."""

    code: str
    person_id: UUID
    ttl: int


class TelegramLinkCodeIssuedEvent(MQEvent[TelegramLinkCodeIssued]): ...
