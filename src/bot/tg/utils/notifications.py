from logging import getLogger

from bot.tg.dto.actor import ActorDTO
from bot.tg.utils.aef_client import (
    AefClientError,
    get_telegram_notifications_enabled,
)

logger = getLogger(__name__)


async def notifications_state(actor: ActorDTO) -> bool | None:
    """Whether Telegram notifications are on for the actor, ``None`` when the
    actor is not linked or ``notify`` did not answer."""
    if actor.person_id is None:
        return None
    try:
        return await get_telegram_notifications_enabled(actor.person_id)
    except (AefClientError, TimeoutError):
        logger.warning("notification state unavailable", exc_info=True)
        return None
