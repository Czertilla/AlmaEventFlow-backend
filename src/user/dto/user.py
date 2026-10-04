from dataclasses import dataclass, field
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class OAuthAccountDTO:
    id: UUID
    oauth_name: str
    access_token: str
    expires_at: int | None
    refresh_token: str | None
    account_id: str
    account_email: str


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    email: str
    username: str | None
    is_active: bool
    is_superuser: bool
    is_verified: bool
    person_id: UUID | None
    oauth_accounts: list[OAuthAccountDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserCreateDTO(FieldsSetDTOMixin):
    email: str
    password: str
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    invite_token: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UserUpdateDTO(FieldsSetDTOMixin):
    password: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
    username: str | None = None
    current_password: str | None = None


@dataclass(frozen=True, slots=True)
class OAuthLoginDTO:
    oauth_name: str
    access_token: str
    account_id: str
    account_email: str
    account_username: str | None = None
    expires_at: int | None = None
    refresh_token: str | None = None


@dataclass(frozen=True, slots=True)
class UserFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
