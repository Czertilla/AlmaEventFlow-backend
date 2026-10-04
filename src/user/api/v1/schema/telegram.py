from pydantic import BaseModel

from core.schema.v1.mixin.dto import FromDTOMixinV1


class TelegramLinkTokenRead(FromDTOMixinV1, BaseModel):
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
