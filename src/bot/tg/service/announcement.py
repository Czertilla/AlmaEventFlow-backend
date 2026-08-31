from datetime import date, datetime
from html import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

_MONTHS_GENITIVE = {
    "ru": (
        "",
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ),
    "en": (
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}


def _format_date(value: date, lang: str) -> str:
    months = _MONTHS_GENITIVE.get(lang, _MONTHS_GENITIVE["ru"])
    return f"{value.day} {months[value.month]} {value.year}"


def _format_time(value: datetime, tz_name: str | None) -> str:
    """Renders the wall-clock time in ``tz_name`` when given and valid --
    Telegram's plain text has no per-viewer rendering, so it commits to the
    zone the stage's creator actually meant."""
    if tz_name:
        try:
            value = value.astimezone(ZoneInfo(tz_name))
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return value.strftime("%H:%M")


def _format_date_time(
    event_date: date | None,
    stage_start: datetime | None,
    stage_tz: str | None,
    lang: str,
) -> str:
    if event_date is None:
        return ""
    text = _format_date(event_date, lang)
    if stage_start is not None:
        text += f", {_format_time(stage_start, stage_tz)}"
    return text


def _format_stage_time(stage: AnnouncementStage) -> str:
    time_part = _format_time(stage.start_at, stage.timezone)
    if stage.end_at is not None:
        time_part += f"–{_format_time(stage.end_at, stage.timezone)}"
    return time_part


async def build_announcement_text(
    request: AnnouncementRequest, lang: str | None = None
) -> str:
    """Renders a group-chat announcement from raw structured data via i18n
    templates -- ``event``-service only gathers facts, this is the only place
    that decides layout/formatting/language. Dynamic values are HTML-escaped
    individually; the surrounding markup lives in the translation strings."""
    lang = lang or i18n_manager.default_lang
    paragraphs: list[str] = []

    if request.action_url:
        paragraphs.append(
            await i18n_manager.get(
                "announcement.title_linked",
                lang=lang,
                event_name=escape(request.event_name),
                action_url=escape(request.action_url),
            )
        )
    else:
        paragraphs.append(
            await i18n_manager.get(
                "announcement.title",
                lang=lang,
                event_name=escape(request.event_name),
            )
        )

    stage_start = request.stages[0].start_at if request.stages else None
    stage_tz = request.stages[0].timezone if request.stages else None
    meta_lines = []
    date_time = _format_date_time(request.event_date, stage_start, stage_tz, lang)
    if date_time:
        meta_lines.append(
            await i18n_manager.get("announcement.date", lang=lang, date=date_time)
        )
    if request.location:
        meta_lines.append(
            await i18n_manager.get(
                "announcement.location",
                lang=lang,
                location=escape(request.location),
            )
        )
    if request.organizer:
        meta_lines.append(
            await i18n_manager.get(
                "announcement.organizer",
                lang=lang,
                organizer=escape(request.organizer),
            )
        )
    if meta_lines:
        paragraphs.append("\n".join(meta_lines))

    if request.event_description:
        paragraphs.append(escape(request.event_description))

    if request.stages:
        stage_lines = [await i18n_manager.get("announcement.stages_header", lang=lang)]
        for stage in request.stages:
            stage_lines.append(
                await i18n_manager.get(
                    "announcement.stage_line",
                    lang=lang,
                    name=escape(stage.name),
                    time=_format_stage_time(stage),
                )
            )
            if stage.description:
                stage_lines.append(
                    await i18n_manager.get(
                        "announcement.stage_description",
                        lang=lang,
                        description=escape(stage.description),
                    )
                )
        paragraphs.append("\n".join(stage_lines))

    paragraphs.append(await i18n_manager.get("announcement.cta", lang=lang))

    return "\n\n".join(paragraphs)
