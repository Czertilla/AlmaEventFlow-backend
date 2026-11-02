from datetime import datetime, timedelta
from profile.repository.account_history import PersonAccountHistoryRepo
from uuid import UUID

from core.config.settings import settings


async def link_cooldown_left(
    history: PersonAccountHistoryRepo, person_id: UUID, now: datetime
) -> timedelta | None:
    """What is left of the pause after the last change of the person's account
    link (`LINK_COOLDOWN_HOURS`); `None` when there is none."""
    pause = timedelta(hours=settings.LINK_COOLDOWN_HOURS)
    if pause <= timedelta(0):
        return None
    changed = await history.last_change_of_person(person_id)
    if changed is None:
        return None
    left = pause - (now - changed)
    return left if left > timedelta(0) else None
