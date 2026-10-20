from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.config.settings import settings


def as_aware(value: datetime) -> datetime:
    """A naive value is UTC, as stored and sent between services, not the host's."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def localize(value: datetime, tz_name: str | None = None) -> datetime:
    """``value`` as wall-clock time in ``tz_name``, else in ``DISPLAY_TIMEZONE``
    when set, else in the zone it already carries."""
    value = as_aware(value)
    for name in (tz_name, settings.DISPLAY_TIMEZONE):
        if not name:
            continue
        try:
            return value.astimezone(ZoneInfo(name))
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return value
