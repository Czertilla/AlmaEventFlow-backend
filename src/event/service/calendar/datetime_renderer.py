import datetime


class CalendarDateTimeRenderer:
    """Normalises datetimes for ICS output.

    The MVP emits timed values in UTC; naive datetimes (the current
    ``event_stage`` columns) are assumed to already be UTC. ``to_tzid`` is a
    placeholder for the future GEO-service-driven timezone support.
    """

    @staticmethod
    def to_utc(value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.UTC)
        return value.astimezone(datetime.UTC)

    @staticmethod
    def to_tzid(value: datetime.datetime, tzid: str) -> datetime.datetime:
        raise NotImplementedError
