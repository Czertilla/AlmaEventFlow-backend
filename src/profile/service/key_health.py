import time
from logging import getLogger
from profile.crypto import Health, KeyConfigError, KeyProviderError, keyring

logger = getLogger(__name__)

FRESH_FOR_SECONDS = 10.0

_last: tuple[float, Health] | None = None


async def key_provider_health() -> Health:
    """The state of the key providers, asked at most once per `FRESH_FOR_SECONDS`."""
    global _last
    now = time.monotonic()
    if _last is not None and now - _last[0] < FRESH_FOR_SECONDS:
        return _last[1]
    try:
        health = await keyring().health()
    except (KeyConfigError, KeyProviderError) as exc:
        logger.warning("The key providers are unavailable: %s", type(exc).__name__)
        health = Health.UNAVAILABLE
    _last = (now, health)
    return health
