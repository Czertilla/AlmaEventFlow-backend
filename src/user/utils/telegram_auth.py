import hashlib
import hmac
import time
from typing import Any

from user.config.settings import settings
from user.exceptions.user import TelegramAuthInvalid, TelegramBotNotConfigured

AUTH_MAX_AGE_SECONDS = 86400
"""Payloads older than this are rejected as stale/replayed, per Telegram's own
recommendation (https://core.telegram.org/widgets/login#checking-authorization)."""


def verify_telegram_widget_payload(data: dict[str, Any]) -> None:
    """Verifies a Telegram Login Widget payload: an HMAC-SHA256 of the sorted,
    newline-joined ``key=value`` fields (excluding ``hash`` itself), keyed by
    ``SHA256(bot_token)``. Raises on a bad signature or a stale ``auth_date``."""
    if not settings.BOT_TG_TOKEN:
        raise TelegramBotNotConfigured()

    received_hash = data.get("hash")
    check_string = "\n".join(
        f"{key}={value}"
        for key, value in sorted(data.items())
        if key != "hash" and value is not None
    )
    secret_key = hashlib.sha256(settings.BOT_TG_TOKEN.encode()).digest()
    expected_hash = hmac.new(
        secret_key, check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not received_hash or not hmac.compare_digest(
        expected_hash, str(received_hash)
    ):
        raise TelegramAuthInvalid()

    try:
        auth_date = int(data["auth_date"])
    except (KeyError, TypeError, ValueError):
        raise TelegramAuthInvalid()
    if time.time() - auth_date > AUTH_MAX_AGE_SECONDS:
        raise TelegramAuthInvalid()
