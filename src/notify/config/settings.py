from logging import getLogger
from pathlib import Path

from pydantic import Secret

from core.config.settings import Settings, getSettings

logger = getLogger(__name__)


class NotifySettings(Settings):
    WEB_PUSH_VAPID_PUBLIC_KEY: str | None = None
    """Inline VAPID public key (base64url). Ignored if ``*_PATH`` is set."""

    WEB_PUSH_VAPID_PRIVATE_KEY: Secret[str] | None = None
    """Inline VAPID private key (PEM or base64url). Ignored if ``*_PATH`` is
    set. Secret — never logged."""

    WEB_PUSH_VAPID_PUBLIC_KEY_PATH: str | None = None
    """File locator for the public key (preferred over inline, like RSA keys)."""

    WEB_PUSH_VAPID_PRIVATE_KEY_PATH: str | None = None
    """File locator for the private key (preferred over inline, like RSA keys)."""

    WEB_PUSH_VAPID_SUBJECT: str = "mailto:admin@aef.czertilla.ru"

    NOTIFY_DEFAULT_LOCALE: str = "ru"
    NOTIFY_DEFAULT_TIMEZONE: str = "UTC"

    EMAIL_DELIVERY_BATCH_SIZE: int = 100
    """Maximum number of email deliveries grouped into one transport batch
    message. Larger recipient sets are split across several batch messages."""

    WEBPUSH_DELIVERY_BATCH_SIZE: int = 100
    """Maximum number of web push deliveries grouped into one transport batch
    message handled together by the in-notify worker."""

    WEBPUSH_LOAD_PAGE_SIZE: int = 200
    """Page size for loading deliveries inside the web push worker, so a large
    batch is processed in bounded chunks rather than all at once."""

    WEBPUSH_SEND_CONCURRENCY: int = 50
    """Maximum simultaneous web push sends per page."""

    OUTBOX_BATCH_SIZE: int = 100
    """Maximum number of outbox rows drained per publisher tick."""

    OUTBOX_POLL_INTERVAL_SECONDS: float = 2.0
    """Idle delay between outbox publisher ticks when nothing is pending."""

    OUTBOX_MAX_ATTEMPTS: int = 5
    """Publish attempts before an outbox row is dead-lettered."""

    DELIVERY_MAX_ATTEMPTS: int = 5
    """Attempts budget snapshotted onto each delivery at creation time."""

    DELIVERY_RETRY_BACKOFF_BASE_SECONDS: float = 60.0
    """First retry delay; doubles each subsequent attempt up to the cap."""

    DELIVERY_RETRY_BACKOFF_CAP_SECONDS: float = 3600.0
    """Upper bound on the exponential retry delay."""

    RETRY_POLL_INTERVAL_SECONDS: float = 10.0
    """Delay between retry re-enqueue worker scans."""

    @staticmethod
    def _resolve_key(path: str | None, inline: str | None) -> str | None:
        if path:
            try:
                return Path(path).read_text().strip()
            except OSError:
                logger.warning("VAPID key file %s unreadable, using inline", path)
        return inline

    @property
    def vapid_public_key(self) -> str | None:
        return self._resolve_key(
            self.WEB_PUSH_VAPID_PUBLIC_KEY_PATH, self.WEB_PUSH_VAPID_PUBLIC_KEY
        )

    @property
    def vapid_private_key(self) -> str | None:
        inline = (
            self.WEB_PUSH_VAPID_PRIVATE_KEY.get_secret_value()
            if self.WEB_PUSH_VAPID_PRIVATE_KEY is not None
            else None
        )
        return self._resolve_key(self.WEB_PUSH_VAPID_PRIVATE_KEY_PATH, inline)

    @property
    def vapid_configured(self) -> bool:
        return bool(self.vapid_private_key and self.vapid_public_key)


settings: NotifySettings = getSettings(NotifySettings)
