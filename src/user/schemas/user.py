import uuid
from datetime import datetime
from typing import Annotated, TypedDict

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, Field


class CreateUpdateUserModel(schemas.CreateUpdateDictModel):
    def create_update_dict(self):
        return self.model_dump(
            exclude_unset=True,
            exclude={
                "id",
                "is_superuser",
                "is_active",
                "is_verified",
                "oauth_accounts",
                "person_id",
                "invite_token",
            },
        )


class InviteTokenData(BaseModel):
    person_id: uuid.UUID
    aud: list[str] = ["invite"]
    exp: int


class UserRead(CreateUpdateUserModel, schemas.BaseUser[uuid.UUID]):
    username: str
    person_id: uuid.UUID | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(CreateUpdateUserModel, schemas.BaseUserCreate):
    username: str
    invite_token: str | None = None


class UserUpdate(CreateUpdateUserModel, schemas.BaseUserUpdate):
    username: str
    current_password: str | None = None


class UserOauthAccount(UserRead, schemas.BaseOAuthAccountMixin): ...


class SUser(UserOauthAccount): ...


class PersonLinkRequest(BaseModel):
    person_id: uuid.UUID


class InviteTokenCreate(BaseModel):
    person_id: uuid.UUID
    expires_in: int | None = None


class InviteTokenRead(BaseModel):
    token: str
    expires_at: int


class LinkInviteData(BaseModel):
    token: str


class TelegramLinkTokenRead(BaseModel):
    token: str
    deep_link: str
    expires_at: int


class TelegramWidgetAuth(BaseModel):
    """The signed payload handed back by Telegram's Login Widget JS, verified
    via ``verify_telegram_widget_payload`` before it's trusted."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class OAuthAccountDict(TypedDict):
    oauth_name: str
    access_token: str
    account_id: str
    account_email: str
    expires_at: int | None = None
    refresh_token: str | None = None


class CheckResponse(BaseModel):
    username: Annotated[str, Field(max_length=50)]
    exists: bool

    model_config = ConfigDict(from_attributes=True)


class SessionRead(BaseModel):
    """A single authenticated session of the current user, as surfaced by the
    self-service session manager. ``is_current`` marks the session bound to the
    refresh token presented in the request."""

    id: uuid.UUID
    device_info: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)
